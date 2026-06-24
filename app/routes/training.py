from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from flask_babel import gettext as _
from app.extensions import db
from app.models.training import TrainingCourse, TrainingSession, TrainingRecord, CompetenceProfile
from app.models.user import User
from app.models.audit_log import AuditLog
from app.forms import TrainingCourseForm, TrainingSessionForm, TrainingRecordForm, CompetenceProfileForm
from app.utils.decorators import permission_required, admin_required
from app.utils.pagination import paginate
from datetime import datetime, date

training_bp = Blueprint("training", __name__)


# ── Courses ─────────────────────────────────────────────────────

@training_bp.route("/")
@login_required
@permission_required("menu_training")
def list_courses():
    category = request.args.get("category")
    query = TrainingCourse.query
    if category:
        query = query.filter_by(category=category)
    courses = paginate(query.order_by(TrainingCourse.title))
    return render_template("training/courses/list.html", courses=courses)


@training_bp.route("/courses/new", methods=["GET", "POST"])
@login_required
@permission_required("training_edit")
def new_course():
    form = TrainingCourseForm()
    if form.validate_on_submit():
        course = TrainingCourse()
        form.populate_obj(course)
        db.session.add(course)
        db.session.commit()
        _log_audit(f"Created training course: {course.title}")
        flash(_("Training course created."), "success")
        return redirect(url_for("training.view_course", course_id=course.id))
    return render_template("training/courses/form.html", form=form, title=_("New Training Course"))


@training_bp.route("/courses/<int:course_id>")
@login_required
def view_course(course_id):
    course = TrainingCourse.query.get_or_404(course_id)
    upcoming = course.sessions.filter(
        TrainingSession.session_date >= date.today()
    ).order_by(TrainingSession.session_date).all()
    past = course.sessions.filter(
        TrainingSession.session_date < date.today()
    ).order_by(TrainingSession.session_date.desc()).all()
    total_trained = db.session.query(TrainingRecord).join(TrainingSession).filter(
        TrainingSession.course_id == course_id,
        TrainingRecord.status == "completed",
    ).count()
    return render_template("training/courses/view.html", course=course,
                           upcoming=upcoming, past=past, total_trained=total_trained)


@training_bp.route("/courses/<int:course_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("training_edit")
def edit_course(course_id):
    course = TrainingCourse.query.get_or_404(course_id)
    form = TrainingCourseForm(obj=course)
    if form.validate_on_submit():
        form.populate_obj(course)
        db.session.commit()
        _log_audit(f"Updated training course: {course.title}")
        flash(_("Training course updated."), "success")
        return redirect(url_for("training.view_course", course_id=course.id))
    return render_template("training/courses/form.html", form=form, title=_("Edit Training Course"), course=course)


@training_bp.route("/courses/<int:course_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_course(course_id):
    course = TrainingCourse.query.get_or_404(course_id)
    title = course.title
    db.session.delete(course)
    db.session.commit()
    _log_audit_action(f"Deleted training course: {title}")
    flash(_("Training course deleted."), "success")
    return redirect(url_for("training.list_courses"))


# ── Sessions ────────────────────────────────────────────────────

@training_bp.route("/courses/<int:course_id>/sessions/new", methods=["GET", "POST"])
@login_required
@permission_required("training_edit")
def new_session(course_id):
    course = TrainingCourse.query.get_or_404(course_id)
    form = TrainingSessionForm()
    if form.validate_on_submit():
        session = TrainingSession(course_id=course.id)
        form.populate_obj(session)
        if not session.title:
            session.title = course.title
        db.session.add(session)
        db.session.commit()
        _log_audit(f"Created session for course: {course.title}")
        flash(_("Training session created."), "success")
        return redirect(url_for("training.view_course", course_id=course.id))
    return render_template("training/sessions/form.html", form=form, title=_("New Training Session"), course=course)


@training_bp.route("/sessions/<int:session_id>")
@login_required
def view_session(session_id):
    session = TrainingSession.query.get_or_404(session_id)
    return render_template("training/sessions/view.html", session=session)


@training_bp.route("/sessions/<int:session_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("training_edit")
def edit_session(session_id):
    session = TrainingSession.query.get_or_404(session_id)
    form = TrainingSessionForm(obj=session)
    if form.validate_on_submit():
        form.populate_obj(session)
        db.session.commit()
        flash(_("Training session updated."), "success")
        return redirect(url_for("training.view_session", session_id=session.id))
    return render_template("training/sessions/form.html", form=form, title=_("Edit Training Session"), session=session)


@training_bp.route("/sessions/<int:session_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_session(session_id):
    session = TrainingSession.query.get_or_404(session_id)
    db.session.delete(session)
    db.session.commit()
    _log_audit_action(f"Deleted training session {session_id}")
    flash(_("Training session deleted."), "success")
    return redirect(url_for("training.view_course", course_id=session.course_id))


# ── Records (enrollments) ──────────────────────────────────────

@training_bp.route("/sessions/<int:session_id>/enroll", methods=["POST"])
@login_required
def enroll_user(session_id):
    session = TrainingSession.query.get_or_404(session_id)
    existing = TrainingRecord.query.filter_by(
        user_id=current_user.id, session_id=session.id
    ).first()
    if existing:
        flash(_("You are already enrolled in this session."), "info")
    else:
        record = TrainingRecord(user_id=current_user.id, session_id=session.id)
        db.session.add(record)
        db.session.commit()
        _log_audit_action(f"User {current_user.id} enrolled in session {session.id}")
        flash(_("Enrolled successfully."), "success")
    return redirect(url_for("training.view_session", session_id=session.id))


@training_bp.route("/sessions/<int:session_id>/records/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("training_edit")
def edit_record(session_id, user_id):
    session = TrainingSession.query.get_or_404(session_id)
    record = TrainingRecord.query.filter_by(session_id=session_id, user_id=user_id).first_or_404()
    form = TrainingRecordForm(obj=record)
    if form.validate_on_submit():
        form.populate_obj(record)
        if form.completed_date.data and not record.completed_date:
            from datetime import datetime as dt
            record.completed_date = dt.combine(form.completed_date.data, dt.min.time())
        db.session.commit()
        flash(_("Training record updated."), "success")
        return redirect(url_for("training.view_session", session_id=session.id))
    form.completed_date.data = record.completed_date.date() if record.completed_date else None
    return render_template("training/records/form.html", form=form, title=_("Edit Training Record"), session=session)


@training_bp.route("/sessions/<int:session_id>/records/<int:user_id>/remove", methods=["POST"])
@login_required
@admin_required
def remove_record(session_id, user_id):
    record = TrainingRecord.query.filter_by(session_id=session_id, user_id=user_id).first_or_404()
    db.session.delete(record)
    db.session.commit()
    flash(_("Training record removed."), "success")
    return redirect(url_for("training.view_session", session_id=session.id))


# ── My Training ─────────────────────────────────────────────────

@training_bp.route("/my-training")
@login_required
def my_training():
    records = TrainingRecord.query.filter_by(user_id=current_user.id).order_by(
        TrainingRecord.created_at.desc()
    ).all()
    competence = CompetenceProfile.query.filter_by(user_id=current_user.id).all()
    return render_template("training/my_training.html", records=records, competence=competence)


# ── All Training Records (admin) ───────────────────────────────

@training_bp.route("/records")
@login_required
@permission_required("training_view")
def all_records():
    query = TrainingRecord.query
    status = request.args.get("status")
    if status:
        query = query.filter_by(status=status)
    records = paginate(query.order_by(TrainingRecord.created_at.desc()))
    return render_template("training/records/list.html", records=records)


# ── Competence ──────────────────────────────────────────────────

@training_bp.route("/competence")
@login_required
@permission_required("training_view")
def competence_matrix():
    users = User.query.filter_by(is_active=True).order_by(User.first_name).all()
    competence = CompetenceProfile.query.all()
    return render_template("training/competence/matrix.html", users=users, competence=competence)


@training_bp.route("/competence/<int:profile_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("training_edit")
def edit_competence(profile_id):
    profile = CompetenceProfile.query.get_or_404(profile_id)
    form = CompetenceProfileForm(obj=profile)
    form.user_id.choices = [
        (u.id, f"{u.first_name} {u.last_name}") for u in User.query.filter_by(is_active=True).order_by(User.first_name).all()
    ]
    if form.validate_on_submit():
        form.populate_obj(profile)
        db.session.commit()
        flash(_("Competence profile updated."), "success")
        return redirect(url_for("training.competence_matrix"))
    return render_template("training/competence/form.html", form=form, title=_("Edit Competence"), profile=profile)


@training_bp.route("/competence/new", methods=["GET", "POST"])
@login_required
@permission_required("training_edit")
def new_competence():
    form = CompetenceProfileForm()
    form.user_id.choices = [
        (u.id, f"{u.first_name} {u.last_name}") for u in User.query.filter_by(is_active=True).order_by(User.first_name).all()
    ]
    if form.validate_on_submit():
        profile = CompetenceProfile()
        form.populate_obj(profile)
        db.session.add(profile)
        db.session.commit()
        flash(_("Competence profile created."), "success")
        return redirect(url_for("training.competence_matrix"))
    return render_template("training/competence/form.html", form=form, title=_("New Competence"))


@training_bp.route("/competence/<int:profile_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_competence(profile_id):
    profile = CompetenceProfile.query.get_or_404(profile_id)
    db.session.delete(profile)
    db.session.commit()
    flash(_("Competence profile deleted."), "success")
    return redirect(url_for("training.competence_matrix"))


def _log_audit(details):
    _log_audit_action(details)


def _log_audit_action(details):
    try:
        log = AuditLog(
            user_id=current_user.id,
            action="DELETE" if "Deleted" in details else "CREATE" if "Created" in details else "UPDATE",
            resource_type="Training",
            details=details,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent", "")[:256],
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        pass
