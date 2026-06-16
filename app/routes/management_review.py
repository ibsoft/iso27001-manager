from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from flask_babel import gettext as _
from app.extensions import db
from app.models.management_review import ManagementReview, ReviewActionItem
from app.models.user import User
from app.models.audit_log import AuditLog
from app.forms import ManagementReviewForm, ReviewActionItemForm
from app.utils.decorators import permission_required, admin_required
from app.utils.pagination import paginate
from datetime import datetime, date

mgmt_review_bp = Blueprint("management_review", __name__)


@mgmt_review_bp.route("/")
@login_required
def list_reviews():
    status = request.args.get("status")
    query = ManagementReview.query
    if status:
        query = query.filter_by(status=status)
    reviews = paginate(query.order_by(ManagementReview.review_date.desc()))
    overdue = ManagementReview.query.filter(
        ManagementReview.status.in_(["planned", "in_progress"]),
        ManagementReview.review_date < date.today(),
    ).count()
    return render_template("management_review/list.html", reviews=reviews, overdue=overdue)


@mgmt_review_bp.route("/new", methods=["GET", "POST"])
@login_required
@permission_required("management_review_create")
def new_review():
    form = ManagementReviewForm()
    form.conducted_by_id.choices = [(0, _("Unassigned"))] + [
        (u.id, f"{u.first_name} {u.last_name}") for u in User.query.filter_by(is_active=True).all()
    ]
    if form.validate_on_submit():
        review = ManagementReview()
        form.populate_obj(review)
        if form.conducted_by_id.data == 0:
            review.conducted_by_id = None
        db.session.add(review)
        db.session.commit()
        _log_audit(f"Created management review: {review.title}")
        flash(_("Management review created successfully."), "success")
        return redirect(url_for("management_review.view_review", review_id=review.id))
    return render_template("management_review/form.html", form=form, title=_("New Management Review"))


@mgmt_review_bp.route("/<int:review_id>")
@login_required
def view_review(review_id):
    review = ManagementReview.query.get_or_404(review_id)
    action_form = ReviewActionItemForm()
    users_list = User.query.filter_by(is_active=True).order_by(User.first_name).all()
    action_form.owner_id.choices = [(0, _("Unassigned"))] + [
        (u.id, f"{u.first_name} {u.last_name}") for u in users_list
    ]
    return render_template("management_review/view.html", review=review, action_form=action_form, users=users_list)


@mgmt_review_bp.route("/<int:review_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("management_review_edit")
def edit_review(review_id):
    review = ManagementReview.query.get_or_404(review_id)
    form = ManagementReviewForm(obj=review)
    form.conducted_by_id.choices = [(0, _("Unassigned"))] + [
        (u.id, f"{u.first_name} {u.last_name}") for u in User.query.filter_by(is_active=True).all()
    ]
    if form.validate_on_submit():
        form.populate_obj(review)
        if form.conducted_by_id.data == 0:
            review.conducted_by_id = None
        review.updated_at = datetime.utcnow()
        db.session.commit()
        _log_audit(f"Updated management review: {review.title}")
        flash(_("Management review updated successfully."), "success")
        return redirect(url_for("management_review.view_review", review_id=review.id))
    form.conducted_by_id.data = review.conducted_by_id or 0
    return render_template("management_review/form.html", form=form, title=_("Edit Management Review"), review=review)


@mgmt_review_bp.route("/<int:review_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_review(review_id):
    review = ManagementReview.query.get_or_404(review_id)
    title = review.title
    db.session.delete(review)
    db.session.commit()
    _log_audit_action(f"Deleted management review: {title}")
    flash(_("Management review deleted."), "success")
    return redirect(url_for("management_review.list_reviews"))


@mgmt_review_bp.route("/<int:review_id>/actions/new", methods=["POST"])
@login_required
@permission_required("management_review_create")
def new_action(review_id):
    review = ManagementReview.query.get_or_404(review_id)
    form = ReviewActionItemForm()
    form.owner_id.choices = [(0, _("Unassigned"))] + [
        (u.id, f"{u.first_name} {u.last_name}") for u in User.query.filter_by(is_active=True).all()
    ]
    if form.validate_on_submit():
        action = ReviewActionItem(review_id=review.id)
        form.populate_obj(action)
        if form.owner_id.data == 0:
            action.owner_id = None
        db.session.add(action)
        db.session.commit()
        _log_audit(f"Added action item to review: {review.title}")
        flash(_("Action item added."), "success")
    else:
        flash(_("Please correct the errors below."), "danger")
    return redirect(url_for("management_review.view_review", review_id=review.id))


@mgmt_review_bp.route("/<int:review_id>/actions/<int:action_id>/edit", methods=["POST"])
@login_required
@permission_required("management_review_edit")
def edit_action(review_id, action_id):
    review = ManagementReview.query.get_or_404(review_id)
    action = ReviewActionItem.query.get_or_404(action_id)
    form = ReviewActionItemForm(obj=action)
    form.owner_id.choices = [(0, _("Unassigned"))] + [
        (u.id, f"{u.first_name} {u.last_name}") for u in User.query.filter_by(is_active=True).all()
    ]
    if form.validate_on_submit():
        form.populate_obj(action)
        if form.owner_id.data == 0:
            action.owner_id = None
        if action.status == "completed" and not action.completed_at:
            action.completed_at = datetime.utcnow()
        db.session.commit()
        flash(_("Action item updated."), "success")
    else:
        flash(_("Please correct the errors below."), "danger")
    return redirect(url_for("management_review.view_review", review_id=review.id))


@mgmt_review_bp.route("/<int:review_id>/actions/<int:action_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_action(review_id, action_id):
    action = ReviewActionItem.query.get_or_404(action_id)
    db.session.delete(action)
    db.session.commit()
    _log_audit_action(f"Deleted action item from review {review_id}")
    flash(_("Action item deleted."), "success")
    return redirect(url_for("management_review.view_review", review_id=review.id))


def _log_audit(details):
    _log_audit_action(details)


def _log_audit_action(details):
    try:
        log = AuditLog(
            user_id=current_user.id,
            action="DELETE" if "Deleted" in details else "CREATE" if "Created" in details or "Added" in details else "UPDATE",
            resource_type="ManagementReview",
            details=details,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent", "")[:256],
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        pass
