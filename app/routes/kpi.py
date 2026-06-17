import io
import csv
from datetime import datetime, timedelta, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, jsonify
from flask_login import login_required
from flask_babel import gettext as _
from app.extensions import db
from app.models.metric import KpiDefinition, KpiMeasurement
from app.models.audit_log import AuditLog
from app.utils.decorators import permission_required
from app.utils.pagination import paginate

kpi_bp = Blueprint("kpi", __name__)


@kpi_bp.route("/")
@login_required
def list_kpis():
    active = request.args.get("active", "1")
    query = KpiDefinition.query
    if active == "1":
        query = query.filter_by(is_active=True)
    elif active == "0":
        query = query.filter_by(is_active=False)
    kpis = paginate(query.order_by(KpiDefinition.category, KpiDefinition.name))
    return render_template("kpi/list.html", kpis=kpis)


@kpi_bp.route("/dashboard")
@login_required
def dashboard():
    kpis = KpiDefinition.query.filter_by(is_active=True).all()
    kpi_data = []
    for kpi in kpis:
        measurements = KpiMeasurement.query.filter_by(kpi_id=kpi.id)\
            .order_by(KpiMeasurement.measured_at.asc()).all()
        labels = [(m.measured_at.strftime("%Y-%m-%d") if m.measured_at else "") for m in measurements]
        values = [m.value for m in measurements]
        latest_value = values[-1] if values else None
        trend = "up" if len(values) >= 2 and values[-1] > values[-2] else \
                "down" if len(values) >= 2 and values[-1] < values[-2] else "flat"
        target = kpi.target or 1
        pct = round((latest_value / target * 100) if latest_value is not None else 0, 1)
        kpi_data.append({
            "kpi_id": kpi.id,
            "kpi_name": kpi.name,
            "kpi_desc": kpi.description or "",
            "kpi_category": kpi.category or "",
            "kpi_unit": kpi.unit or "",
            "kpi_target": target,
            "chart_labels": labels,
            "chart_values": values,
            "latest_value": latest_value,
            "trend": trend,
            "pct": min(pct, 100),
        })
    return render_template("kpi/dashboard.html", kpi_data=kpi_data)


@kpi_bp.route("/record/<int:kpi_id>", methods=["GET", "POST"])
@login_required
@permission_required("kpi_record")
def record_measurement(kpi_id):
    kpi = KpiDefinition.query.get_or_404(kpi_id)
    if request.method == "POST":
        value = request.form.get("value", type=float)
        measured_at = request.form.get("measured_at")
        notes = request.form.get("notes", "")
        if value is None:
            flash(_("Value is required."), "danger")
            return render_template("kpi/record.html", kpi=kpi)
        measurement = KpiMeasurement(
            kpi_id=kpi.id,
            value=value,
            measured_at=datetime.strptime(measured_at, "%Y-%m-%d").replace(tzinfo=timezone.utc) if measured_at else datetime.now(timezone.utc),
            notes=notes,
        )
        db.session.add(measurement)
        db.session.commit()
        flash(_("Measurement recorded."), "success")
        return redirect(url_for("kpi.dashboard"))
    return render_template("kpi/record.html", kpi=kpi)


@kpi_bp.route("/data/<int:kpi_id>")
@login_required
def kpi_data_json(kpi_id):
    kpi = KpiDefinition.query.get_or_404(kpi_id)
    months = request.args.get("months", 12, type=int)
    since = datetime.now(timezone.utc) - timedelta(days=months * 30)
    measurements = KpiMeasurement.query.filter_by(kpi_id=kpi.id)\
        .filter(KpiMeasurement.measured_at >= since)\
        .order_by(KpiMeasurement.measured_at.asc()).all()
    return jsonify({
        "name": kpi.name,
        "unit": kpi.unit,
        "target": kpi.target,
        "labels": [m.measured_at.strftime("%Y-%m-%d") for m in measurements],
        "values": [m.value for m in measurements],
    })


@kpi_bp.route("/export-csv")
@login_required
def export_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["KPI", "Category", "Unit", "Target", "Date", "Value", "Notes"])
    for kpi in KpiDefinition.query.order_by(KpiDefinition.category, KpiDefinition.name).all():
        for m in KpiMeasurement.query.filter_by(kpi_id=kpi.id)\
                .order_by(KpiMeasurement.measured_at.desc()).all():
            writer.writerow([kpi.name, kpi.category, kpi.unit, kpi.target,
                             m.measured_at.strftime("%Y-%m-%d"), m.value, m.notes])
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"kpi_export_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv",
    )
