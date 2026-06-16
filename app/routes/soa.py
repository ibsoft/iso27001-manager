from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import login_required, current_user
from flask_babel import gettext as _
from flask_babel import lazy_gettext as _l
from app.extensions import db
from app.models.soa import SoAEntry
from app.models.control import Control
from app.models.domain import Domain
from app.models.user import User
from app.models.audit_log import AuditLog
from app.forms import SoAForm
from app.utils.decorators import permission_required
from wtforms import SelectField
from wtforms.validators import DataRequired
from datetime import datetime

soa_bp = Blueprint("soa", __name__)


@soa_bp.route("/")
@login_required
def list_soa():
    lang = session.get("lang", "en")
    domains = Domain.query.order_by(Domain.code).all()
    soa_entries = {}
    for domain in domains:
        entries = SoAEntry.query.join(Control).filter(
            Control.domain_id == domain.id
        ).order_by(Control.code).all()

        if not entries:
            controls = Control.query.filter_by(domain_id=domain.id).order_by(Control.code).all()
            for c in controls:
                entry = SoAEntry(control_id=c.id, applicable=True)
                db.session.add(entry)
                entries.append(entry)
            db.session.commit()

        soa_entries[domain.id] = {
            "domain": domain,
            "entries": SoAEntry.query.join(Control).filter(
                Control.domain_id == domain.id
            ).order_by(Control.code).all()
        }

    return render_template("soa/list.html", soa_entries=soa_entries, lang=lang)


@soa_bp.route("/new", methods=["GET", "POST"])
@login_required
@permission_required("soa_edit")
def new_soa():
    lang = session.get("lang", "en")
    form = SoAForm()
    form.responsible_person_id.choices = [(0, _("Unassigned"))] + [
        (u.id, f"{u.first_name} {u.last_name}") for u in User.query.filter_by(is_active=True).all()
    ]
    control_choices = [(c.id, f"{c.code} - {c.localized_title(lang)}") for c in Control.query.order_by(Control.code).all()]
    form.control_id = SelectField(_l("Control"), coerce=int, choices=control_choices, validators=[DataRequired()])

    if form.validate_on_submit():
        existing = SoAEntry.query.filter_by(control_id=form.control_id.data).first()
        if existing:
            flash(_("SoA entry already exists for this control."), "warning")
            return redirect(url_for("soa.edit_entry", entry_id=existing.id))
        entry = SoAEntry()
        form.populate_obj(entry)
        if form.responsible_person_id.data == 0:
            entry.responsible_person_id = None
        entry.version = "1.0"
        db.session.add(entry)
        db.session.commit()
        _log_audit(f"Created SoA entry for control {entry.control.code}")
        flash(_("SoA entry created."), "success")
        return redirect(url_for("soa.list_soa"))

    return render_template("soa/form.html", form=form, lang=lang)


@soa_bp.route("/<int:entry_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("soa_edit")
def edit_entry(entry_id):
    lang = session.get("lang", "en")
    entry = SoAEntry.query.get_or_404(entry_id)
    form = SoAForm(obj=entry)
    form.responsible_person_id.choices = [(0, _("Unassigned"))] + [
        (u.id, f"{u.first_name} {u.last_name}") for u in User.query.filter_by(is_active=True).all()
    ]

    if form.validate_on_submit():
        form.populate_obj(entry)
        if form.responsible_person_id.data == 0:
            entry.responsible_person_id = None
        entry.updated_at = datetime.utcnow()
        db.session.commit()
        _log_audit(f"Updated SoA entry for control {entry.control.code}")
        flash(_("SoA entry updated."), "success")
        return redirect(url_for("soa.list_soa"))

    form.responsible_person_id.data = entry.responsible_person_id or 0
    return render_template("soa/edit.html", form=form, entry=entry, lang=lang)


@soa_bp.route("/summary")
@login_required
def soa_summary():
    total = SoAEntry.query.count()
    applicable = SoAEntry.query.filter_by(applicable=True).count()
    not_applicable = SoAEntry.query.filter_by(applicable=False).count()
    implemented = SoAEntry.query.filter_by(implementation_status="implemented").count()
    in_progress = SoAEntry.query.filter_by(implementation_status="in_progress").count()
    not_started = SoAEntry.query.filter_by(implementation_status="not_started").count()

    return render_template("soa/summary.html", **locals())


@soa_bp.route("/export")
@login_required
@permission_required("report_export")
def export_soa():
    entries = SoAEntry.query.join(Control).order_by(Control.code).all()
    return render_template("soa/export.html", entries=entries)


def _log_audit(details):
    try:
        log = AuditLog(
            user_id=current_user.id,
            action="UPDATE",
            resource_type="SoA",
            details=details,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent", "")[:256],
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        pass
