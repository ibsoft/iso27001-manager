from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from flask_babel import gettext as _
from app.extensions import db
from app.models.notification import Notification
from app.utils.pagination import paginate

notifications_bp = Blueprint("notifications", __name__)


@notifications_bp.route("/")
@login_required
def list_all():
    query = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc())
    notifications = paginate(query)
    return render_template("notifications/list.html", notifications=notifications)


@notifications_bp.route("/<int:notif_id>/read", methods=["POST"])
@login_required
def mark_read(notif_id):
    notif = Notification.query.get_or_404(notif_id)
    if notif.user_id != current_user.id:
        flash(_("Notification not found."), "danger")
        return redirect(url_for("notifications.list_all"))
    notif.is_read = True
    db.session.commit()
    return redirect(request.referrer or url_for("notifications.list_all"))


@notifications_bp.route("/read-all", methods=["POST"])
@login_required
def mark_all_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({"is_read": True})
    db.session.commit()
    flash(_("All notifications marked as read."), "success")
    return redirect(request.referrer or url_for("notifications.list_all"))
