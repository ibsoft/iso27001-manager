from datetime import datetime, date
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from flask_babel import gettext as _
from app.extensions import db
from app.forms import (
    BusinessImpactAnalysisForm, BusinessContinuityPlanForm,
    BusinessContinuityTestForm, BusinessContinuityActionForm
)
from app.models.audit_log import AuditLog
from app.models.business_continuity import (
    BusinessImpactAnalysis, BusinessContinuityPlan,
    BusinessContinuityTest, BusinessContinuityAction
)
from app.models.user import User
from app.utils.decorators import permission_required, admin_required
from app.utils.pagination import paginate

business_continuity_bp = Blueprint("business_continuity", __name__)


def _active_users():
    return User.query.filter_by(is_active=True).order_by(User.first_name, User.last_name).all()


def _user_choices(empty_label=None):
    choices = [(0, empty_label or _("Unassigned"))]
    choices.extend((u.id, f"{u.first_name} {u.last_name}") for u in _active_users())
    return choices


def _bia_choices():
    return [(0, _("None"))] + [
        (b.id, b.process_name) for b in BusinessImpactAnalysis.query.order_by(BusinessImpactAnalysis.process_name).all()
    ]


def _plan_choices():
    return [(p.id, p.title) for p in BusinessContinuityPlan.query.order_by(BusinessContinuityPlan.title).all()]


def _test_choices(plan_id):
    choices = [(0, _("None"))]
    tests = BusinessContinuityTest.query.filter_by(plan_id=plan_id).order_by(BusinessContinuityTest.scheduled_date.desc()).all()
    choices.extend((t.id, t.title) for t in tests)
    return choices


def _log_audit(details):
    try:
        action = "DELETE" if "Deleted" in details else "CREATE" if "Created" in details or "Added" in details else "UPDATE"
        log = AuditLog(
            user_id=current_user.id,
            action=action,
            resource_type="BusinessContinuity",
            details=details,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent", "")[:256],
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        pass


@business_continuity_bp.route("/")
@login_required
@permission_required("menu_business_continuity")
def dashboard():
    total_bia = BusinessImpactAnalysis.query.count()
    total_plans = BusinessContinuityPlan.query.count()
    active_plans = BusinessContinuityPlan.query.filter_by(lifecycle_stage="active").count()
    due_tests = BusinessContinuityPlan.query.filter(
        BusinessContinuityPlan.next_test_date.isnot(None),
        BusinessContinuityPlan.next_test_date <= date.today(),
        BusinessContinuityPlan.lifecycle_stage.notin_(["retired"]),
    ).count()
    open_actions = BusinessContinuityAction.query.filter(
        BusinessContinuityAction.status.in_(["open", "in_progress"])
    ).count()
    recent_tests = BusinessContinuityTest.query.order_by(BusinessContinuityTest.created_at.desc()).limit(5).all()
    return render_template(
        "business_continuity/dashboard.html",
        total_bia=total_bia,
        total_plans=total_plans,
        active_plans=active_plans,
        due_tests=due_tests,
        open_actions=open_actions,
        recent_tests=recent_tests,
    )


@business_continuity_bp.route("/bia")
@login_required
@permission_required("business_continuity_view")
def list_bia():
    status = request.args.get("status")
    criticality = request.args.get("criticality")
    search = request.args.get("search", "")
    query = BusinessImpactAnalysis.query
    if status:
        query = query.filter_by(status=status)
    if criticality:
        query = query.filter_by(criticality=criticality)
    if search:
        query = query.filter(BusinessImpactAnalysis.process_name.ilike(f"%{search}%"))
    records = paginate(query.order_by(BusinessImpactAnalysis.assessment_date.desc()))
    return render_template("business_continuity/bia_list.html", records=records)


@business_continuity_bp.route("/bia/new", methods=["GET", "POST"])
@login_required
@permission_required("business_continuity_create")
def new_bia():
    form = BusinessImpactAnalysisForm()
    form.process_owner_id.choices = _user_choices()
    if form.validate_on_submit():
        record = BusinessImpactAnalysis()
        form.populate_obj(record)
        if form.process_owner_id.data == 0:
            record.process_owner_id = None
        db.session.add(record)
        db.session.commit()
        _log_audit(f"Created BIA: {record.process_name}")
        flash(_("Business impact analysis created."), "success")
        return redirect(url_for("business_continuity.view_bia", bia_id=record.id))
    return render_template("business_continuity/bia_form.html", form=form, title=_("New Business Impact Analysis (BIA)"))


@business_continuity_bp.route("/bia/<int:bia_id>")
@login_required
@permission_required("business_continuity_view")
def view_bia(bia_id):
    record = BusinessImpactAnalysis.query.get_or_404(bia_id)
    return render_template("business_continuity/bia_view.html", record=record)


@business_continuity_bp.route("/bia/<int:bia_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("business_continuity_edit")
def edit_bia(bia_id):
    record = BusinessImpactAnalysis.query.get_or_404(bia_id)
    form = BusinessImpactAnalysisForm(obj=record)
    form.process_owner_id.choices = _user_choices()
    if form.validate_on_submit():
        form.populate_obj(record)
        if form.process_owner_id.data == 0:
            record.process_owner_id = None
        record.updated_at = datetime.utcnow()
        db.session.commit()
        _log_audit(f"Updated BIA: {record.process_name}")
        flash(_("Business impact analysis updated."), "success")
        return redirect(url_for("business_continuity.view_bia", bia_id=record.id))
    form.process_owner_id.data = record.process_owner_id or 0
    return render_template("business_continuity/bia_form.html", form=form, title=_("Edit Business Impact Analysis (BIA)"), record=record)


@business_continuity_bp.route("/bia/<int:bia_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_bia(bia_id):
    record = BusinessImpactAnalysis.query.get_or_404(bia_id)
    name = record.process_name
    BusinessContinuityPlan.query.filter_by(bia_id=record.id).update({"bia_id": None})
    db.session.delete(record)
    db.session.commit()
    _log_audit(f"Deleted BIA: {name}")
    flash(_("Business impact analysis deleted."), "success")
    return redirect(url_for("business_continuity.list_bia"))


@business_continuity_bp.route("/plans")
@login_required
@permission_required("business_continuity_view")
def list_plans():
    stage = request.args.get("lifecycle_stage")
    plan_type = request.args.get("plan_type")
    search = request.args.get("search", "")
    query = BusinessContinuityPlan.query
    if stage:
        query = query.filter_by(lifecycle_stage=stage)
    if plan_type:
        query = query.filter_by(plan_type=plan_type)
    if search:
        query = query.filter(BusinessContinuityPlan.title.ilike(f"%{search}%"))
    plans = paginate(query.order_by(BusinessContinuityPlan.updated_at.desc()))
    return render_template("business_continuity/plan_list.html", plans=plans)


@business_continuity_bp.route("/plans/new", methods=["GET", "POST"])
@login_required
@permission_required("business_continuity_create")
def new_plan():
    form = BusinessContinuityPlanForm()
    form.bia_id.choices = _bia_choices()
    form.owner_id.choices = _user_choices()
    if form.validate_on_submit():
        plan = BusinessContinuityPlan()
        form.populate_obj(plan)
        if form.bia_id.data == 0:
            plan.bia_id = None
        if form.owner_id.data == 0:
            plan.owner_id = None
        if plan.lifecycle_stage in ("approved", "active"):
            plan.approved_by_id = current_user.id
            plan.approved_at = datetime.utcnow()
        db.session.add(plan)
        db.session.commit()
        _log_audit(f"Created continuity plan: {plan.title}")
        flash(_("Business continuity plan created."), "success")
        return redirect(url_for("business_continuity.view_plan", plan_id=plan.id))
    bia_id = request.args.get("bia_id", type=int)
    if bia_id:
        form.bia_id.data = bia_id
    return render_template("business_continuity/plan_form.html", form=form, title=_("New Continuity Plan"))


@business_continuity_bp.route("/plans/<int:plan_id>")
@login_required
@permission_required("business_continuity_view")
def view_plan(plan_id):
    plan = BusinessContinuityPlan.query.get_or_404(plan_id)
    action_form = BusinessContinuityActionForm()
    action_form.owner_id.choices = _user_choices()
    action_form.test_id.choices = _test_choices(plan.id)
    tests = plan.tests.order_by(BusinessContinuityTest.scheduled_date.desc()).all()
    actions = plan.actions.order_by(BusinessContinuityAction.due_date).all()
    return render_template(
        "business_continuity/plan_view.html",
        plan=plan,
        action_form=action_form,
        tests=tests,
        actions=actions,
    )


@business_continuity_bp.route("/plans/<int:plan_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("business_continuity_edit")
def edit_plan(plan_id):
    plan = BusinessContinuityPlan.query.get_or_404(plan_id)
    form = BusinessContinuityPlanForm(obj=plan)
    form.bia_id.choices = _bia_choices()
    form.owner_id.choices = _user_choices()
    if form.validate_on_submit():
        previous_stage = plan.lifecycle_stage
        form.populate_obj(plan)
        if form.bia_id.data == 0:
            plan.bia_id = None
        if form.owner_id.data == 0:
            plan.owner_id = None
        if plan.lifecycle_stage in ("approved", "active") and previous_stage not in ("approved", "active"):
            plan.approved_by_id = current_user.id
            plan.approved_at = datetime.utcnow()
        plan.updated_at = datetime.utcnow()
        db.session.commit()
        _log_audit(f"Updated continuity plan: {plan.title}")
        flash(_("Business continuity plan updated."), "success")
        return redirect(url_for("business_continuity.view_plan", plan_id=plan.id))
    form.bia_id.data = plan.bia_id or 0
    form.owner_id.data = plan.owner_id or 0
    return render_template("business_continuity/plan_form.html", form=form, title=_("Edit Continuity Plan"), plan=plan)


@business_continuity_bp.route("/plans/<int:plan_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_plan(plan_id):
    plan = BusinessContinuityPlan.query.get_or_404(plan_id)
    title = plan.title
    db.session.delete(plan)
    db.session.commit()
    _log_audit(f"Deleted continuity plan: {title}")
    flash(_("Business continuity plan deleted."), "success")
    return redirect(url_for("business_continuity.list_plans"))


@business_continuity_bp.route("/tests")
@login_required
@permission_required("business_continuity_view")
def list_tests():
    outcome = request.args.get("outcome")
    test_type = request.args.get("test_type")
    query = BusinessContinuityTest.query
    if outcome:
        query = query.filter_by(outcome=outcome)
    if test_type:
        query = query.filter_by(test_type=test_type)
    tests = paginate(query.order_by(BusinessContinuityTest.scheduled_date.desc()))
    return render_template("business_continuity/test_list.html", tests=tests)


@business_continuity_bp.route("/tests/new", methods=["GET", "POST"])
@login_required
@permission_required("business_continuity_create")
def new_test():
    form = BusinessContinuityTestForm()
    form.plan_id.choices = _plan_choices()
    form.facilitator_id.choices = _user_choices()
    if not form.plan_id.choices:
        flash(_("Create a continuity plan before scheduling a test."), "warning")
        return redirect(url_for("business_continuity.new_plan"))
    if form.validate_on_submit():
        test = BusinessContinuityTest()
        form.populate_obj(test)
        if form.facilitator_id.data == 0:
            test.facilitator_id = None
        db.session.add(test)
        plan = BusinessContinuityPlan.query.get(test.plan_id)
        if plan and test.next_test_date:
            plan.next_test_date = test.next_test_date
        db.session.commit()
        _log_audit(f"Created continuity test: {test.title}")
        flash(_("Continuity test created."), "success")
        return redirect(url_for("business_continuity.view_test", test_id=test.id))
    plan_id = request.args.get("plan_id", type=int)
    if plan_id:
        form.plan_id.data = plan_id
    return render_template("business_continuity/test_form.html", form=form, title=_("New Disaster Recovery Plan (DRP) Test"))


@business_continuity_bp.route("/tests/<int:test_id>")
@login_required
@permission_required("business_continuity_view")
def view_test(test_id):
    test = BusinessContinuityTest.query.get_or_404(test_id)
    return render_template("business_continuity/test_view.html", test=test)


@business_continuity_bp.route("/tests/<int:test_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("business_continuity_edit")
def edit_test(test_id):
    test = BusinessContinuityTest.query.get_or_404(test_id)
    form = BusinessContinuityTestForm(obj=test)
    form.plan_id.choices = _plan_choices()
    form.facilitator_id.choices = _user_choices()
    if form.validate_on_submit():
        form.populate_obj(test)
        if form.facilitator_id.data == 0:
            test.facilitator_id = None
        test.updated_at = datetime.utcnow()
        plan = BusinessContinuityPlan.query.get(test.plan_id)
        if plan and test.next_test_date:
            plan.next_test_date = test.next_test_date
        db.session.commit()
        _log_audit(f"Updated continuity test: {test.title}")
        flash(_("Continuity test updated."), "success")
        return redirect(url_for("business_continuity.view_test", test_id=test.id))
    form.facilitator_id.data = test.facilitator_id or 0
    return render_template("business_continuity/test_form.html", form=form, title=_("Edit Disaster Recovery Plan (DRP) Test"), test=test)


@business_continuity_bp.route("/tests/<int:test_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_test(test_id):
    test = BusinessContinuityTest.query.get_or_404(test_id)
    title = test.title
    BusinessContinuityAction.query.filter_by(test_id=test.id).update({"test_id": None})
    db.session.delete(test)
    db.session.commit()
    _log_audit(f"Deleted continuity test: {title}")
    flash(_("Continuity test deleted."), "success")
    return redirect(url_for("business_continuity.list_tests"))


@business_continuity_bp.route("/plans/<int:plan_id>/actions/new", methods=["POST"])
@login_required
@permission_required("business_continuity_create")
def new_action(plan_id):
    plan = BusinessContinuityPlan.query.get_or_404(plan_id)
    form = BusinessContinuityActionForm()
    form.owner_id.choices = _user_choices()
    form.test_id.choices = _test_choices(plan.id)
    if form.validate_on_submit():
        action = BusinessContinuityAction(plan_id=plan.id)
        form.populate_obj(action)
        if form.owner_id.data == 0:
            action.owner_id = None
        if form.test_id.data == 0:
            action.test_id = None
        db.session.add(action)
        db.session.commit()
        _log_audit(f"Added continuity action to plan: {plan.title}")
        flash(_("Action item added."), "success")
    else:
        flash(_("Please correct the errors below."), "danger")
    return redirect(url_for("business_continuity.view_plan", plan_id=plan.id))


@business_continuity_bp.route("/plans/<int:plan_id>/actions/<int:action_id>/complete", methods=["POST"])
@login_required
@permission_required("business_continuity_edit")
def complete_action(plan_id, action_id):
    action = BusinessContinuityAction.query.get_or_404(action_id)
    action.status = "completed"
    action.completed_at = datetime.utcnow()
    db.session.commit()
    _log_audit(f"Completed continuity action for plan {plan_id}")
    flash(_("Action item completed."), "success")
    return redirect(url_for("business_continuity.view_plan", plan_id=plan_id))


@business_continuity_bp.route("/plans/<int:plan_id>/actions/<int:action_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_action(plan_id, action_id):
    action = BusinessContinuityAction.query.get_or_404(action_id)
    db.session.delete(action)
    db.session.commit()
    _log_audit(f"Deleted continuity action from plan {plan_id}")
    flash(_("Action item deleted."), "success")
    return redirect(url_for("business_continuity.view_plan", plan_id=plan_id))
