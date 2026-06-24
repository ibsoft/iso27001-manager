from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from flask_babel import gettext as _
from app.extensions import db
from app.models.asset import Asset
from app.models.user import User
from app.models.asset_assignment import AssetAssignment
from app.models.audit_log import AuditLog
from app.forms import AssetCheckoutForm, AssetCheckinForm
from app.utils.decorators import permission_required, admin_required
from app.utils.pagination import paginate
from datetime import datetime, date

assignments_bp = Blueprint("assignments", __name__)


def _log(user_id, action, details):
    try:
        log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type="AssetAssignment",
            details=details,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent", "")[:256],
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        pass


@assignments_bp.route("/")
@login_required
@permission_required("menu_assignments")
def list_assignments():
    status_filter = request.args.get("status")
    search = request.args.get("search", "")
    user_id = request.args.get("user_id", type=int)
    asset_id = request.args.get("asset_id", type=int)

    query = AssetAssignment.query

    if status_filter:
        query = query.filter(AssetAssignment.status == status_filter)
    if user_id:
        query = query.filter(AssetAssignment.user_id == user_id)
    if asset_id:
        query = query.filter(AssetAssignment.asset_id == asset_id)
    if search:
        query = query.join(Asset).filter(
            db.or_(
                Asset.name.ilike(f"%{search}%"),
                AssetAssignment.assignee_name.ilike(f"%{search}%"),
                AssetAssignment.department.ilike(f"%{search}%"),
            )
        )

    assignments = paginate(query.order_by(AssetAssignment.checkout_date.desc()))
    users = User.query.filter_by(is_active=True).order_by(User.first_name).all()
    return render_template("assignments/list.html", assignments=assignments, users=users)


@assignments_bp.route("/<int:assignment_id>")
@login_required
def view_assignment(assignment_id):
    assignment = AssetAssignment.query.get_or_404(assignment_id)
    return render_template("assignments/view.html", assignment=assignment)


@assignments_bp.route("/<int:assignment_id>/receipt")
@login_required
def receipt(assignment_id):
    assignment = AssetAssignment.query.get_or_404(assignment_id)
    return render_template("assignments/receipt.html", assignment=assignment, datetime=datetime)


@assignments_bp.route("/<int:assignment_id>/checkin", methods=["GET", "POST"])
@login_required
@permission_required("asset_edit")
def checkin_assignment(assignment_id):
    assignment = AssetAssignment.query.get_or_404(assignment_id)
    if assignment.status == "returned":
        flash(_("This asset has already been returned."), "warning")
        return redirect(url_for("assignments.view_assignment", assignment_id=assignment.id))

    form = AssetCheckinForm()
    if form.validate_on_submit():
        if not form.checkin_signature_data.data:
            flash(_("Return signature is required."), "danger")
            return render_template("assignments/checkin.html", form=form, assignment=assignment)
        assignment.actual_return_date = form.actual_return_date.data or datetime.utcnow()
        assignment.condition_notes = form.condition_notes.data
        assignment.checkin_signature_data = form.checkin_signature_data.data
        assignment.checkin_signed_at = datetime.utcnow() if form.checkin_signature_data.data else None
        assignment.released_by_id = current_user.id
        assignment.released_at = datetime.utcnow()
        assignment.status = "returned"
        assignment.updated_at = datetime.utcnow()
        db.session.commit()
        _log(current_user.id, "CHECKIN",
             f"Asset '{assignment.asset.name}' returned by {assignment.assignee_name or assignment.user}")
        flash(_("Asset checked in successfully."), "success")
        return redirect(url_for("assignments.view_assignment", assignment_id=assignment.id))

    if request.method == "POST":
        if form.errors:
            flash(_("Please correct the errors below."), "danger")
        elif not form.checkin_signature_data.data:
            flash(_("Return signature is required."), "danger")
    form.actual_return_date.data = date.today()
    return render_template("assignments/checkin.html", form=form, assignment=assignment)


@assignments_bp.route("/user/<int:user_id>")
@login_required
def user_history(user_id):
    user = User.query.get_or_404(user_id)
    query = AssetAssignment.query.filter(
        db.or_(AssetAssignment.user_id == user_id, AssetAssignment.assignee_name.ilike(f"%{user.first_name}%"))
    )
    assignments = paginate(query.order_by(AssetAssignment.checkout_date.desc()))
    active_count = AssetAssignment.query.filter(
        AssetAssignment.user_id == user_id, AssetAssignment.status == "checked_out"
    ).count()
    return render_template("assignments/user_history.html",
                           assignments=assignments, user=user, active_count=active_count)


@assignments_bp.route("/report")
@login_required
@permission_required("report_view")
def report():
    total = AssetAssignment.query.count()
    active = AssetAssignment.query.filter_by(status="checked_out").count()
    returned = AssetAssignment.query.filter_by(status="returned").count()
    overdue = AssetAssignment.query.filter(
        AssetAssignment.status == "checked_out",
        AssetAssignment.expected_return_date < datetime.utcnow(),
    ).count()

    by_user = (
        db.session.query(
            User.id, User.first_name, User.last_name,
            db.func.count(AssetAssignment.id).label("total"),
            db.func.sum(db.case((AssetAssignment.status == "returned", 1), else_=0)).label("returned_count"),
            db.func.sum(db.case((AssetAssignment.status == "checked_out", 1), else_=0)).label("active_count"),
        )
        .join(User, AssetAssignment.user_id == User.id, isouter=True)
        .group_by(User.id, User.first_name, User.last_name)
        .order_by(db.func.count(AssetAssignment.id).desc())
        .all()
    )

    recent = AssetAssignment.query.order_by(AssetAssignment.checkout_date.desc()).limit(20).all()
    return render_template("assignments/report.html", total=total, active=active,
                           returned=returned, overdue=overdue,
                           by_user=by_user, recent=recent)


@assignments_bp.route("/<int:assignment_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_assignment(assignment_id):
    assignment = AssetAssignment.query.get_or_404(assignment_id)
    if assignment.status != "returned":
        flash(_("Only returned assignments can be deleted."), "danger")
        return redirect(request.referrer or url_for("assignments.list_assignments"))
    detail = f"Assignment #{assignment.id}: {assignment.asset.name} → {assignment.assignee_name or assignment.user}"
    db.session.delete(assignment)
    db.session.commit()
    _log(current_user.id, "DELETE", f"Deleted {detail}")
    flash(_("Assignment deleted."), "success")
    return redirect(request.referrer or url_for("assignments.list_assignments"))


@assignments_bp.route("/offboard/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def offboard_user(user_id):
    user = User.query.get_or_404(user_id)
    active = AssetAssignment.query.filter_by(user_id=user_id, status="checked_out").all()
    if not active:
        flash(_("No active assignments for this user."), "info")
        return redirect(url_for("assignments.user_history", user_id=user_id))

    now = datetime.utcnow()
    count = 0
    for a in active:
        a.actual_return_date = now
        a.released_by_id = current_user.id
        a.released_at = now
        a.status = "returned"
        a.notes = (a.notes or "") + f"\n[Offboarded {now.strftime('%Y-%m-%d')} by {current_user.username}]"
        count += 1
    db.session.commit()
    _log(current_user.id, "OFFBOARD",
         f"Offboarded user '{user.username}' — {count} asset(s) returned")
    flash(_("%(count)s asset(s) returned for %(name)s.", count=count, name=user.full_name), "success")
    return redirect(url_for("assignments.user_history", user_id=user_id))

# ── Asset-specific checkout (from assets blueprint) ──────────────────────


@assignments_bp.route("/asset/<int:asset_id>/checkout", methods=["GET", "POST"])
@login_required
@permission_required("asset_edit")
def checkout_asset(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    if asset.status != "active":
        flash(_("Only active assets can be checked out."), "warning")
        return redirect(url_for("assets.view_asset", asset_id=asset.id))

    active = AssetAssignment.query.filter_by(asset_id=asset_id, status="checked_out").first()
    if active:
        flash(_("This asset is already checked out. Return it first."), "warning")
        return redirect(url_for("assignments.view_assignment", assignment_id=active.id))

    form = AssetCheckoutForm()
    form.user_id.choices = [(0, _("— External / Not listed —"))] + [
        (u.id, f"{u.first_name} {u.last_name} ({u.username})")
        for u in User.query.filter_by(is_active=True).order_by(User.first_name).all()
    ]

    if form.validate_on_submit():
        if not form.signature_data.data:
            flash(_("Signature is required."), "danger")
            return render_template("assignments/checkout.html", form=form, asset=asset)
        assignment = AssetAssignment()
        assignment.asset_id = asset.id
        assignment.assignee_type = form.assignee_type.data
        if form.assignee_type.data == "internal" and form.user_id.data and form.user_id.data > 0:
            user = User.query.get(form.user_id.data)
            assignment.user_id = user.id
            assignment.assignee_name = f"{user.first_name} {user.last_name}"
            assignment.contact_email = user.email
            assignment.contact_phone = user.mobile_phone or user.phone_number
            assignment.department = form.department.data
        else:
            assignment.assignee_name = form.assignee_name.data
            assignment.department = form.department.data
            assignment.contact_email = form.contact_email.data
            assignment.contact_phone = form.contact_phone.data
        assignment.expected_return_date = form.expected_return_date.data
        assignment.purpose = form.purpose.data
        assignment.notes = form.notes.data
        assignment.signature_data = form.signature_data.data
        assignment.signed_at = datetime.utcnow() if form.signature_data.data else None
        assignment.status = "checked_out"
        db.session.add(assignment)
        db.session.commit()
        _log(current_user.id, "CHECKOUT",
             f"Asset '{asset.name}' assigned to {assignment.assignee_name}")
        flash(_("Asset checked out successfully."), "success")
        return redirect(url_for("assignments.view_assignment", assignment_id=assignment.id))

    if request.method == "POST":
        if form.errors:
            flash(_("Please correct the errors below."), "danger")
        elif not form.signature_data.data:
            flash(_("Signature is required."), "danger")
    return render_template("assignments/checkout.html", form=form, asset=asset)
