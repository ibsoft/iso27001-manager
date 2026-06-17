import os
import uuid
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, current_app
from flask_login import login_required, current_user
from flask_babel import gettext as _
from app.extensions import db
from app.models.filled_form import FilledForm
from app.models.user import User
from app.models.audit_log import AuditLog
from app.models.asset_assignment import AssetAssignment
from app.utils.decorators import admin_required, role_required
from app.utils.pagination import paginate

filled_forms_bp = Blueprint("filled_forms", __name__)

ALLOWED_EXT = {"pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
               "odt", "ods", "odp", "txt", "rtf", "csv",
               "png", "jpg", "jpeg", "gif", "svg"}


def _save_upload(file_storage):
    upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], "filled_forms")
    os.makedirs(upload_dir, exist_ok=True)
    ext = os.path.splitext(file_storage.filename)[1].lower()
    unique = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(upload_dir, unique)
    file_storage.save(path)
    return unique, file_storage.filename, os.path.getsize(path)


def _delete_upload(filename):
    if not filename:
        return
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], "filled_forms", filename)
    if os.path.exists(path):
        os.remove(path)


@filled_forms_bp.route("/")
@login_required
def list_filled_forms():
    year = request.args.get("year", type=int)
    user_id = request.args.get("user_id", type=int)
    search = request.args.get("search", "")

    query = FilledForm.query

    if current_user.has_role("admin"):
        if user_id:
            query = query.filter_by(user_id=user_id)
    else:
        query = query.filter_by(user_id=current_user.id)
        user_id = current_user.id

    if year:
        query = query.filter_by(year=year)

    if search:
        query = query.filter(
            db.or_(
                FilledForm.title.ilike(f"%{search}%"),
                FilledForm.description.ilike(f"%{search}%"),
                FilledForm.original_filename.ilike(f"%{search}%"),
            )
        )

    years = (
        db.session.query(FilledForm.year)
        .distinct()
        .order_by(FilledForm.year.desc())
        .all()
    )
    years = [r[0] for r in years]
    if not years:
        years = [datetime.utcnow().year]

    users = User.query.filter_by(is_active=True).order_by(User.first_name, User.last_name).all()

    checked_out_assets = []
    if user_id:
        checked_out_assets = (
            AssetAssignment.query
            .filter_by(user_id=user_id, status="checked_out")
            .order_by(AssetAssignment.checkout_date.desc())
            .all()
        )

    forms = paginate(query.order_by(FilledForm.uploaded_at.desc()))
    return render_template(
        "filled_forms/list.html",
        forms=forms,
        years=years,
        users=users,
        checked_out_assets=checked_out_assets,
    )


@filled_forms_bp.route("/upload", methods=["GET", "POST"])
@login_required
@role_required("admin", "manager")
def upload_filled_form():
    users = User.query.filter_by(is_active=True).order_by(User.first_name, User.last_name).all()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        year = request.form.get("year", type=int)
        description = request.form.get("description", "").strip()
        file = request.files.get("file")

        if current_user.has_role("admin"):
            selected_user_id = request.form.get("user_id", type=int)
            if not selected_user_id or not User.query.get(selected_user_id):
                flash(_("Please select a user."), "danger")
                return render_template("filled_forms/upload.html", users=users)
        else:
            selected_user_id = current_user.id

        if not title:
            flash(_("Title is required."), "danger")
            return render_template("filled_forms/upload.html", users=users)
        if not year or year < 2000 or year > 2100:
            flash(_("Valid year is required."), "danger")
            return render_template("filled_forms/upload.html", users=users)
        if not file or not file.filename:
            flash(_("File is required."), "danger")
            return render_template("filled_forms/upload.html", users=users)

        ext = os.path.splitext(file.filename)[1].lower().lstrip(".")
        if ext not in ALLOWED_EXT:
            flash(_("File type not allowed."), "danger")
            return render_template("filled_forms/upload.html", users=users)

        stored, original, size = _save_upload(file)
        form = FilledForm(
            user_id=selected_user_id,
            year=year,
            title=title,
            description=description,
            filename=stored,
            original_filename=original,
            file_size=size,
        )
        db.session.add(form)
        db.session.commit()

        try:
            log = AuditLog(
                user_id=current_user.id,
                action="CREATE",
                resource_type="FilledForm",
                details=f"Uploaded filled form: {title} ({year}) for user {selected_user_id}",
                ip_address=request.remote_addr,
                user_agent=request.headers.get("User-Agent", "")[:256],
            )
            db.session.add(log)
            db.session.commit()
        except Exception:
            pass

        flash(_("Form uploaded successfully."), "success")
        return redirect(url_for("filled_forms.list_filled_forms"))

    return render_template("filled_forms/upload.html", users=users)


@filled_forms_bp.route("/<int:form_id>/download")
@login_required
def download_filled_form(form_id):
    form = FilledForm.query.get_or_404(form_id)
    if form.user_id != current_user.id and not current_user.has_role("admin"):
        abort(403)
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], "filled_forms", form.filename)
    if not os.path.exists(path):
        flash(_("File not found on disk."), "danger")
        return redirect(url_for("filled_forms.list_filled_forms"))
    return send_file(path, as_attachment=True, download_name=form.original_filename)


@filled_forms_bp.route("/<int:form_id>/delete", methods=["POST"])
@login_required
def delete_filled_form(form_id):
    form = FilledForm.query.get_or_404(form_id)
    if form.user_id != current_user.id and not current_user.has_role("admin"):
        abort(403)
    title = form.title
    _delete_upload(form.filename)
    db.session.delete(form)
    db.session.commit()

    try:
        log = AuditLog(
            user_id=current_user.id,
            action="DELETE",
            resource_type="FilledForm",
            details=f"Deleted filled form: {title}",
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent", "")[:256],
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        pass

    flash(_("Form deleted."), "success")
    return redirect(url_for("filled_forms.list_filled_forms"))
