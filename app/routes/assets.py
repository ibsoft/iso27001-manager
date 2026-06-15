from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from flask_babel import gettext as _
from app.extensions import db
from app.models.asset import Asset
from app.models.user import User
from app.models.audit_log import AuditLog
from app.forms import AssetForm
from app.utils.decorators import permission_required, admin_required
from datetime import datetime

assets_bp = Blueprint("assets", __name__)


@assets_bp.route("/")
@login_required
def list_assets():
    classification = request.args.get("classification")
    asset_type = request.args.get("asset_type")
    status = request.args.get("status")
    search = request.args.get("search", "")

    query = Asset.query
    if classification:
        query = query.filter_by(classification=classification)
    if asset_type:
        query = query.filter_by(asset_type=asset_type)
    if status:
        query = query.filter_by(status=status)
    if search:
        query = query.filter(Asset.name.ilike(f"%{search}%"))

    assets = query.order_by(Asset.name).all()
    return render_template("assets/list.html", assets=assets)


@assets_bp.route("/new", methods=["GET", "POST"])
@login_required
@permission_required("asset_create")
def new_asset():
    form = AssetForm()
    form.owner_id.choices = [(0, _("Unassigned"))] + [(u.id, f"{u.first_name} {u.last_name}") for u in User.query.filter_by(is_active=True).all()]

    if form.validate_on_submit():
        asset = Asset()
        form.populate_obj(asset)
        if form.owner_id.data == 0:
            asset.owner_id = None
        db.session.add(asset)
        db.session.commit()
        _log_audit(f"Created asset: {asset.name}")
        flash(_("Asset created successfully."), "success")
        return redirect(url_for("assets.view_asset", asset_id=asset.id))

    return render_template("assets/form.html", form=form, title=_("New Asset"))


@assets_bp.route("/<int:asset_id>")
@login_required
def view_asset(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    return render_template("assets/view.html", asset=asset)


@assets_bp.route("/<int:asset_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("asset_edit")
def edit_asset(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    form = AssetForm(obj=asset)
    form.owner_id.choices = [(0, _("Unassigned"))] + [(u.id, f"{u.first_name} {u.last_name}") for u in User.query.filter_by(is_active=True).all()]

    if form.validate_on_submit():
        form.populate_obj(asset)
        if form.owner_id.data == 0:
            asset.owner_id = None
        asset.updated_at = datetime.utcnow()
        db.session.commit()
        _log_audit(f"Updated asset: {asset.name}")
        flash(_("Asset updated successfully."), "success")
        return redirect(url_for("assets.view_asset", asset_id=asset.id))

    form.owner_id.data = asset.owner_id or 0
    return render_template("assets/form.html", form=form, title=_("Edit Asset"), asset=asset)


@assets_bp.route("/<int:asset_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_asset(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    name = asset.name
    db.session.delete(asset)
    db.session.commit()
    _log_audit_action(f"Deleted asset: {name}")
    flash(_("Asset deleted."), "success")
    return redirect(url_for("assets.list_assets"))


def _log_audit(details):
    _log_audit_action(details)


def _log_audit_action(details):
    try:
        log = AuditLog(
            user_id=current_user.id,
            action="DELETE" if "Deleted" in details else "CREATE" if "Created" in details else "UPDATE",
            resource_type="Asset",
            details=details,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent", "")[:256],
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        pass
