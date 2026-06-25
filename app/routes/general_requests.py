import os
import uuid
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from flask_babel import gettext as _
from app.extensions import db
from app.models.general_request import GeneralRequest
from app.models.approval import ApprovalRequest
from app.models.user import User
from app.utils.pagination import paginate
from app.utils.notify import notify
from app.utils.decorators import permission_required

general_requests_bp = Blueprint("general_requests", __name__)

ALLOWED_EXT = {"pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
               "odt", "ods", "odp", "txt", "rtf", "csv",
               "png", "jpg", "jpeg", "gif", "svg"}


def _save_upload(file_storage):
    upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], "general_requests")
    os.makedirs(upload_dir, exist_ok=True)
    ext = os.path.splitext(file_storage.filename)[1].lower()
    unique = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(upload_dir, unique)
    file_storage.save(path)
    return unique, file_storage.filename, os.path.getsize(path)


def _delete_upload(filename):
    if not filename:
        return
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], "general_requests", filename)
    if os.path.exists(path):
        os.remove(path)


@general_requests_bp.route("/")
@login_required
@permission_required("menu_general_requests")
def list_requests():
    query = GeneralRequest.query.filter_by(created_by_id=current_user.id).order_by(GeneralRequest.created_at.desc())
    requests = paginate(query)
    approval_map = {}
    for req in requests.items:
        apr = ApprovalRequest.query.filter_by(target_type="general_request", target_id=req.id).first()
        if apr:
            approval_map[req.id] = apr
    return render_template("general_requests/list.html", requests=requests, approval_map=approval_map)


@general_requests_bp.route("/new", methods=["GET", "POST"])
@login_required
@permission_required("menu_general_requests")
def new():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        if not title:
            flash(_("Title is required."), "danger")
            return render_template("general_requests/form.html")

        general_req = GeneralRequest(
            title=title,
            content=content,
            created_by_id=current_user.id,
        )

        file = request.files.get("file")
        if file and file.filename:
            stored, original, size = _save_upload(file)
            general_req.filename = stored
            general_req.original_filename = original
            general_req.file_size = size

        db.session.add(general_req)
        db.session.flush()

        approver_id = current_user.manager_id
        if not approver_id:
            db.session.rollback()
            flash(_("You do not have a manager assigned. Please contact an administrator."), "danger")
            return render_template("general_requests/form.html")

        req = ApprovalRequest(
            requester_id=current_user.id,
            approver_id=approver_id,
            target_type="general_request",
            target_id=general_req.id,
        )
        db.session.add(req)
        db.session.commit()

        notify(
            req.approver,
            "approval_requested",
            _("Approval Request: %(title)s", title=general_req.title),
            _("%(name)s requested your approval.", name=current_user.full_name),
            link=url_for("approval.pending"),
            reference_type="approval_request",
            reference_id=req.id,
        )

        flash(_("Request submitted for approval."), "success")
        return redirect(url_for("general_requests.list_requests"))

    return render_template("general_requests/form.html")


@general_requests_bp.route("/<int:req_id>")
@login_required
def view(req_id):
    general_req = GeneralRequest.query.get_or_404(req_id)
    from app.models.approval import ApprovalRequest
    is_approver = ApprovalRequest.query.filter_by(
        target_type="general_request", target_id=general_req.id, approver_id=current_user.id
    ).first() is not None
    if general_req.created_by_id != current_user.id and not current_user.has_role("admin") and not is_approver:
        if current_user.id != general_req.created_by.manager_id:
            flash(_("Access denied."), "danger")
            return redirect(url_for("general_requests.list_requests"))
    approval = ApprovalRequest.query.filter_by(target_type="general_request", target_id=general_req.id).first()
    return render_template("general_requests/view.html", request=general_req, approval=approval)


@general_requests_bp.route("/<int:req_id>/download")
@login_required
def download(req_id):
    general_req = GeneralRequest.query.get_or_404(req_id)
    from app.models.approval import ApprovalRequest
    is_approver = ApprovalRequest.query.filter_by(
        target_type="general_request", target_id=general_req.id, approver_id=current_user.id
    ).first() is not None
    if general_req.created_by_id != current_user.id and not current_user.has_role("admin") and not is_approver:
        flash(_("Access denied."), "danger")
        return redirect(url_for("general_requests.list_requests"))
    if not general_req.filename:
        flash(_("No file attached."), "warning")
        return redirect(url_for("general_requests.view", req_id=req_id))
    from flask import send_file
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], "general_requests", general_req.filename)
    img_exts = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}
    as_attachment = os.path.splitext(general_req.original_filename or "")[1].lower() not in img_exts
    return send_file(path, as_attachment=as_attachment, download_name=general_req.original_filename)
