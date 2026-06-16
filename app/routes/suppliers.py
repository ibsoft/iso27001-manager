from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from flask_babel import gettext as _
from app.extensions import db
from app.models.supplier import Supplier
from app.models.audit_log import AuditLog
from app.forms import SupplierForm
from app.utils.decorators import permission_required, admin_required
from app.utils.pagination import paginate
from datetime import datetime

suppliers_bp = Blueprint("suppliers", __name__)


@suppliers_bp.route("/")
@login_required
def list_suppliers():
    status = request.args.get("status")
    assessment = request.args.get("assessment_status")
    search = request.args.get("search", "")

    query = Supplier.query
    if status:
        query = query.filter_by(status=status)
    if assessment:
        query = query.filter_by(assessment_status=assessment)
    if search:
        query = query.filter(Supplier.name.ilike(f"%{search}%"))

    suppliers = paginate(query.order_by(Supplier.name))
    return render_template("suppliers/list.html", suppliers=suppliers)


@suppliers_bp.route("/new", methods=["GET", "POST"])
@login_required
@permission_required("supplier_create")
def new_supplier():
    form = SupplierForm()
    if form.validate_on_submit():
        supplier = Supplier()
        form.populate_obj(supplier)
        db.session.add(supplier)
        db.session.commit()
        _log_audit(f"Created supplier: {supplier.name}")
        flash(_("Supplier created successfully."), "success")
        return redirect(url_for("suppliers.view_supplier", supplier_id=supplier.id))

    return render_template("suppliers/form.html", form=form, title=_("New Supplier"))


@suppliers_bp.route("/<int:supplier_id>")
@login_required
def view_supplier(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    return render_template("suppliers/view.html", supplier=supplier)


@suppliers_bp.route("/<int:supplier_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("supplier_edit")
def edit_supplier(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    form = SupplierForm(obj=supplier)
    if form.validate_on_submit():
        form.populate_obj(supplier)
        supplier.updated_at = datetime.utcnow()
        db.session.commit()
        _log_audit(f"Updated supplier: {supplier.name}")
        flash(_("Supplier updated successfully."), "success")
        return redirect(url_for("suppliers.view_supplier", supplier_id=supplier.id))

    return render_template("suppliers/form.html", form=form, title=_("Edit Supplier"), supplier=supplier)


@suppliers_bp.route("/<int:supplier_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_supplier(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    name = supplier.name
    db.session.delete(supplier)
    db.session.commit()
    _log_audit_action(f"Deleted supplier: {name}")
    flash(_("Supplier deleted."), "success")
    return redirect(url_for("suppliers.list_suppliers"))


def _log_audit(details):
    _log_audit_action(details)


def _log_audit_action(details):
    try:
        log = AuditLog(
            user_id=current_user.id,
            action="DELETE" if "Deleted" in details else "CREATE" if "Created" in details else "UPDATE",
            resource_type="Supplier",
            details=details,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent", "")[:256],
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        pass
