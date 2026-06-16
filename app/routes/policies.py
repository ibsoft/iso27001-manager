import io
import os
import uuid
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, current_app
from flask_login import login_required, current_user
from flask_babel import gettext as _
from app.extensions import db
from app.models.policy import Policy, PolicyVersion
from app.models.user import User
from app.models.audit_log import AuditLog
from app.forms import PolicyForm
from app.utils.decorators import permission_required, admin_required
from app.utils.pagination import paginate

policies_bp = Blueprint("policies", __name__)

ALLOWED_EXT = {"pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
               "odt", "ods", "odp", "txt", "rtf", "csv",
               "png", "jpg", "jpeg", "gif", "svg"}


def _save_upload(file_storage):
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_dir, exist_ok=True)
    ext = os.path.splitext(file_storage.filename)[1].lower()
    unique = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(upload_dir, unique)
    file_storage.save(path)
    return unique, file_storage.filename, os.path.getsize(path)


def _delete_upload(filename):
    if not filename:
        return
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    if os.path.exists(path):
        os.remove(path)


@policies_bp.route("/")
@login_required
def list_policies():
    status = request.args.get("status")
    category = request.args.get("category")
    doc_filter = request.args.get("type")
    search = request.args.get("search", "")

    query = Policy.query
    if status:
        query = query.filter_by(status=status)
    if category:
        query = query.filter_by(category=category)
    if doc_filter == "document":
        query = query.filter_by(is_document=True)
    elif doc_filter == "policy":
        query = query.filter_by(is_document=False)
    if search:
        query = query.filter(
            db.or_(
                Policy.title.ilike(f"%{search}%"),
                Policy.description.ilike(f"%{search}%"),
                Policy.original_filename.ilike(f"%{search}%"),
            )
        )

    policies = paginate(query.order_by(Policy.updated_at.desc()))
    return render_template("policies/list.html", policies=policies)


def _set_common_choices(form):
    form.owner_id.choices = [(0, _("Unassigned"))] + [
        (u.id, f"{u.first_name} {u.last_name}")
        for u in User.query.filter_by(is_active=True).all()
    ]


@policies_bp.route("/new", methods=["GET", "POST"])
@login_required
@permission_required("policy_create")
def new_policy():
    form = PolicyForm()
    _set_common_choices(form)

    if form.validate_on_submit():
        policy = Policy()
        form.populate_obj(policy)
        if form.owner_id.data == 0:
            policy.owner_id = None
        policy.current_version = "1.0"

        file = request.files.get("file")
        if file and file.filename:
            stored, original, size = _save_upload(file)
            policy.filename = stored
            policy.original_filename = original
            policy.file_size = size
            policy.is_document = True

        db.session.add(policy)
        db.session.flush()

        version = PolicyVersion(
            policy_id=policy.id,
            version_number="1.0",
            content=policy.content,
            filename=policy.filename,
            original_filename=policy.original_filename,
            file_size=policy.file_size,
            created_by_id=current_user.id,
        )
        db.session.add(version)
        db.session.commit()
        _log_audit(f"Created {'document' if policy.is_document else 'policy'}: {policy.title}")
        flash(_("Created successfully."), "success")
        return redirect(url_for("policies.view_policy", policy_id=policy.id))

    return render_template("policies/form.html", form=form, title=_("New"), policy=None)


@policies_bp.route("/<int:policy_id>")
@login_required
def view_policy(policy_id):
    policy = Policy.query.get_or_404(policy_id)
    return render_template("policies/view.html", policy=policy)


@policies_bp.route("/<int:policy_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("policy_edit")
def edit_policy(policy_id):
    policy = Policy.query.get_or_404(policy_id)
    form = PolicyForm(obj=policy)
    _set_common_choices(form)

    if form.validate_on_submit():
        old_content = policy.content
        old_file = policy.filename
        form.populate_obj(policy)
        if form.owner_id.data == 0:
            policy.owner_id = None
        policy.updated_at = datetime.utcnow()

        file = request.files.get("file")
        if file and file.filename:
            if old_file:
                _delete_upload(old_file)
            stored, original, size = _save_upload(file)
            policy.filename = stored
            policy.original_filename = original
            policy.file_size = size
            policy.is_document = True

        updating_content = form.content.data != old_content
        updating_file = policy.filename != old_file
        db.session.commit()

        if updating_content or updating_file:
            version = PolicyVersion(
                policy_id=policy.id,
                version_number=policy.current_version,
                content=policy.content,
                filename=policy.filename,
                original_filename=policy.original_filename,
                file_size=policy.file_size,
                created_by_id=current_user.id,
            )
            db.session.add(version)
            db.session.commit()

        _log_audit(f"Updated {'document' if policy.is_document else 'policy'}: {policy.title}")
        flash(_("Updated successfully."), "success")
        return redirect(url_for("policies.view_policy", policy_id=policy.id))

    form.owner_id.data = policy.owner_id or 0
    return render_template("policies/form.html", form=form, title=_("Edit"), policy=policy)


@policies_bp.route("/<int:policy_id>/new-version", methods=["GET", "POST"])
@login_required
@permission_required("policy_edit")
def new_version(policy_id):
    policy = Policy.query.get_or_404(policy_id)
    form = PolicyForm(obj=policy)
    _set_common_choices(form)

    if form.validate_on_submit():
        current_version_num = float(policy.current_version)
        new_version_num = f"{current_version_num + 1:.1f}"

        stored = policy.filename
        original = policy.original_filename
        size = policy.file_size
        file = request.files.get("file")
        if file and file.filename:
            if stored:
                _delete_upload(stored)
            stored, original, size = _save_upload(file)

        version = PolicyVersion(
            policy_id=policy.id,
            version_number=new_version_num,
            content=form.content.data if not policy.is_document else policy.content,
            filename=stored,
            original_filename=original,
            file_size=size,
            change_summary=request.form.get("change_summary", ""),
            created_by_id=current_user.id,
        )
        db.session.add(version)

        if not policy.is_document:
            policy.content = form.content.data
        policy.filename = stored
        policy.original_filename = original
        policy.file_size = size
        policy.current_version = new_version_num
        policy.updated_at = datetime.utcnow()
        db.session.commit()
        _log_audit(f"Created new version {new_version_num} for {policy.title}")
        flash(_("New version created."), "success")
        return redirect(url_for("policies.view_policy", policy_id=policy.id))

    form.owner_id.data = policy.owner_id or 0
    return render_template("policies/new_version.html", form=form, policy=policy)


@policies_bp.route("/<int:policy_id>/download")
@login_required
def download_policy(policy_id):
    policy = Policy.query.get_or_404(policy_id)
    if policy.is_document and policy.filename:
        path = os.path.join(current_app.config["UPLOAD_FOLDER"], policy.filename)
        if os.path.exists(path):
            return send_file(path, as_attachment=True, download_name=policy.original_filename)
        flash(_("File not found on disk."), "danger")
        return redirect(url_for("policies.view_policy", policy_id=policy.id))

    from xhtml2pdf import pisa
    html = render_template("policies/pdf.html", policy=policy)
    buf = io.BytesIO()
    pisa_status = pisa.CreatePDF(io.StringIO(html), dest=buf)
    if pisa_status.err:
        flash(_("Failed to generate PDF."), "danger")
        return redirect(url_for("policies.view_policy", policy_id=policy.id))
    buf.seek(0)
    filename = f"{policy.title.replace(' ', '_')}_v{policy.current_version}.pdf"
    return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name=filename)


@policies_bp.route("/<int:policy_id>/download/<int:version_id>")
@login_required
def download_version_file(policy_id, version_id):
    version = PolicyVersion.query.get_or_404(version_id)
    if not version.filename:
        flash(_("No file for this version."), "warning")
        return redirect(url_for("policies.view_policy", policy_id=policy_id))
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], version.filename)
    if not os.path.exists(path):
        flash(_("File not found on disk."), "danger")
        return redirect(url_for("policies.view_policy", policy_id=policy_id))
    return send_file(path, as_attachment=True, download_name=version.original_filename)


@policies_bp.route("/<int:policy_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_policy(policy_id):
    policy = Policy.query.get_or_404(policy_id)
    title = policy.title
    if policy.filename:
        _delete_upload(policy.filename)
    for v in policy.versions:
        if v.filename:
            _delete_upload(v.filename)
    db.session.delete(policy)
    db.session.commit()
    _log_audit_action(f"Deleted {'document' if policy.is_document else 'policy'}: {title}")
    flash(_("Policy deleted."), "success")
    return redirect(url_for("policies.list_policies"))


def _log_audit(details):
    _log_audit_action(details)


def _log_audit_action(details):
    try:
        log = AuditLog(
            user_id=current_user.id,
            action="DELETE" if "Deleted" in details else "CREATE" if "Created" in details or "version" in details else "UPDATE",
            resource_type="Document" if "document" in details else "Policy",
            details=details,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent", "")[:256],
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        pass
