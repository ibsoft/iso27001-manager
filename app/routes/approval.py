from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from flask_babel import gettext as _
from app.extensions import db
from app.models.user import User
from app.models.approval import ApprovalRequest
from app.models.notification import Notification
from app.utils.pagination import paginate
from app.utils.notify import notify
from app.utils.decorators import permission_required, admin_required

approval_bp = Blueprint("approval", __name__)


@approval_bp.route("/pending")
@login_required
@permission_required("menu_approvals")
def pending():
    search = request.args.get("search", "").strip()
    query = ApprovalRequest.query.filter_by(approver_id=current_user.id, status="pending")
    if search:
        query = query.join(User, ApprovalRequest.requester_id == User.id).filter(
            db.or_(
                User.first_name.ilike(f"%{search}%"),
                User.last_name.ilike(f"%{search}%"),
                ApprovalRequest.target_type.ilike(f"%{search}%"),
            )
        )
    query = query.order_by(ApprovalRequest.created_at.desc())
    requests = paginate(query)
    return render_template("approval/pending.html", requests=requests, search=search, tab="pending")


@approval_bp.route("/history")
@login_required
@permission_required("menu_approvals")
def history():
    search = request.args.get("search", "").strip()
    query = ApprovalRequest.query.filter(
        ApprovalRequest.approver_id == current_user.id,
        ApprovalRequest.status.in_(["approved", "rejected", "cancelled"]),
    )
    if search:
        query = query.join(User, ApprovalRequest.requester_id == User.id).filter(
            db.or_(
                User.first_name.ilike(f"%{search}%"),
                User.last_name.ilike(f"%{search}%"),
                ApprovalRequest.target_type.ilike(f"%{search}%"),
                ApprovalRequest.reason.ilike(f"%{search}%"),
            )
        )
    query = query.order_by(ApprovalRequest.responded_at.desc())
    requests = paginate(query)
    return render_template("approval/pending.html", requests=requests, search=search, tab="history")


@approval_bp.route("/my-requests")
@login_required
def my_requests():
    query = ApprovalRequest.query.filter_by(requester_id=current_user.id).order_by(ApprovalRequest.created_at.desc())
    requests = paginate(query)
    return render_template("approval/my_requests.html", requests=requests)


@approval_bp.route("/request", methods=["POST"])
@login_required
def create_request():
    target_type = request.form.get("target_type")
    target_id = request.form.get("target_id", type=int)
    approver_id = request.form.get("approver_id", type=int)

    if not all([target_type, target_id, approver_id]):
        flash(_("Missing required fields."), "danger")
        return redirect(request.referrer or url_for("dashboard.index"))

    existing = ApprovalRequest.query.filter_by(
        target_type=target_type, target_id=target_id, status="pending"
    ).first()
    if existing:
        flash(_("A pending approval request already exists for this item."), "warning")
        return redirect(request.referrer or url_for("dashboard.index"))

    approver = User.query.get(approver_id)
    if not approver:
        flash(_("Approver not found."), "danger")
        return redirect(request.referrer or url_for("dashboard.index"))

    req = ApprovalRequest(
        requester_id=current_user.id,
        approver_id=approver_id,
        target_type=target_type,
        target_id=target_id,
    )
    db.session.add(req)
    db.session.commit()

    notify(
        approver,
        "approval_requested",
        _("Approval Request: %(type)s", type=target_type.replace("_", " ").title()),
        _("%(name)s requested your approval.", name=current_user.full_name),
        link=url_for("approval.pending"),
        reference_type="approval_request",
        reference_id=req.id,
    )

    flash(_("Approval request submitted."), "success")
    return redirect(request.referrer or url_for("dashboard.index"))


@approval_bp.route("/<int:req_id>/approve", methods=["POST"])
@login_required
def approve(req_id):
    req = ApprovalRequest.query.get_or_404(req_id)
    if req.approver_id != current_user.id:
        flash(_("You are not the approver for this request."), "danger")
        return redirect(url_for("approval.pending"))

    if req.status != "pending":
        flash(_("This request has already been processed."), "warning")
        return redirect(url_for("approval.pending"))

    req.status = "approved"
    req.responded_at = datetime.utcnow()
    req.responded_by_id = current_user.id
    req.reason = request.form.get("reason", "").strip() or None
    req.apply_transition()
    db.session.commit()

    Notification.query.filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,
        db.or_(
            db.and_(Notification.reference_type == "approval_request", Notification.reference_id == req.id),
            db.and_(Notification.reference_type.is_(None), Notification.type == "approval_requested"),
        ),
    ).update({"is_read": True})
    db.session.commit()

    notify(
        req.requester,
        "approved",
        _("Request Approved: %(type)s", type=req.target_type.replace("_", " ").title()),
        _("%(name)s approved your request.", name=current_user.full_name),
        link=url_for("approval.my_requests"),
    )

    flash(_("Request approved."), "success")
    return redirect(url_for("approval.pending"))


@approval_bp.route("/<int:req_id>/reject", methods=["POST"])
@login_required
def reject(req_id):
    req = ApprovalRequest.query.get_or_404(req_id)
    if req.approver_id != current_user.id:
        flash(_("You are not the approver for this request."), "danger")
        return redirect(url_for("approval.pending"))

    if req.status != "pending":
        flash(_("This request has already been processed."), "warning")
        return redirect(url_for("approval.pending"))

    reason = request.form.get("reason", "").strip()
    if not reason:
        flash(_("Please provide a reason for rejection."), "danger")
        return redirect(url_for("approval.pending"))

    req.status = "rejected"
    req.responded_at = datetime.utcnow()
    req.responded_by_id = current_user.id
    req.reason = reason
    req.apply_transition()
    db.session.commit()

    Notification.query.filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,
        db.or_(
            db.and_(Notification.reference_type == "approval_request", Notification.reference_id == req.id),
            db.and_(Notification.reference_type.is_(None), Notification.type == "approval_requested"),
        ),
    ).update({"is_read": True})
    db.session.commit()

    notify(
        req.requester,
        "rejected",
        _("Request Rejected: %(type)s", type=req.target_type.replace("_", " ").title()),
        _("%(name)s rejected your request. Reason: %(reason)s", name=current_user.full_name, reason=reason),
        link=url_for("approval.my_requests"),
    )

    flash(_("Request rejected."), "success")
    return redirect(url_for("approval.pending"))


@approval_bp.route("/<int:req_id>/cancel", methods=["POST"])
@login_required
def cancel(req_id):
    req = ApprovalRequest.query.get_or_404(req_id)
    if req.requester_id != current_user.id:
        flash(_("You are not the requester for this request."), "danger")
        return redirect(url_for("approval.my_requests"))

    if req.status != "pending":
        flash(_("This request has already been processed."), "warning")
        return redirect(url_for("approval.my_requests"))

    req.status = "cancelled"
    db.session.commit()

    flash(_("Request cancelled."), "success")
    return redirect(url_for("approval.my_requests"))


@approval_bp.route("/<int:req_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete(req_id):
    req = ApprovalRequest.query.get_or_404(req_id)
    Notification.query.filter_by(
        reference_type="approval_request", reference_id=req.id
    ).delete()
    db.session.delete(req)
    db.session.commit()
    flash(_("Approval request deleted."), "success")
    return redirect(url_for("approval.history"))
