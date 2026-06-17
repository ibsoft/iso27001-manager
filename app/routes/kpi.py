from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from flask_babel import gettext as _
from app.extensions import db
from app.models.metric import KpiDefinition, KpiMeasurement
from app.utils.decorators import role_required

kpi_bp = Blueprint("kpi", __name__)


@kpi_bp.route("/kpi")
@login_required
def dashboard():
    kpis = KpiDefinition.query.filter_by(is_active=True).order_by(KpiDefinition.category, KpiDefinition.name).all()

    kpi_data = []
    for k in kpis:
        measurements = KpiMeasurement.query.filter_by(kpi_id=k.id).order_by(KpiMeasurement.measured_at.asc()).all()

        labels = [m.measured_at.strftime("%Y-%m-%d") for m in measurements]
        values = [m.value for m in measurements]

        current_value = values[-1] if values else None
        trend = None
        if len(values) >= 2:
            trend = round(values[-1] - values[-2], 2)

        kpi_data.append({
            "kpi": k,
            "labels": labels,
            "values": values,
            "current_value": current_value,
            "target": k.target,
            "trend": trend,
        })

    return render_template("kpi/dashboard.html", kpi_data=kpi_data)


@kpi_bp.route("/kpi/<int:kpi_id>/record", methods=["POST"])
@login_required
@role_required("admin", "manager")
def record_measurement(kpi_id):
    kpi = KpiDefinition.query.get_or_404(kpi_id)
    value = request.form.get("value", type=float)
    notes = request.form.get("notes", "").strip()
    measured_at_str = request.form.get("measured_at", "").strip()

    if value is None:
        flash(_("Value is required."), "danger")
        return redirect(url_for("kpi.dashboard"))

    measured_at = datetime.utcnow()
    if measured_at_str:
        try:
            measured_at = datetime.strptime(measured_at_str, "%Y-%m-%d")
        except ValueError:
            flash(_("Invalid date format."), "danger")
            return redirect(url_for("kpi.dashboard"))

    m = KpiMeasurement(kpi_id=kpi.id, value=value, notes=notes, measured_at=measured_at)
    db.session.add(m)
    db.session.commit()
    flash(_("Measurement recorded."), "success")
    return redirect(url_for("kpi.dashboard"))


@kpi_bp.route("/kpi/<int:measurement_id>/delete", methods=["POST"])
@login_required
@role_required("admin", "manager")
def delete_measurement(measurement_id):
    m = KpiMeasurement.query.get_or_404(measurement_id)
    db.session.delete(m)
    db.session.commit()
    flash(_("Measurement deleted."), "success")
    return redirect(url_for("kpi.dashboard"))
