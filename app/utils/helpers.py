from datetime import datetime


def calculate_risk_level(likelihood, impact):
    score = likelihood * impact
    if score >= 20:
        return "critical"
    elif score >= 12:
        return "high"
    elif score >= 6:
        return "medium"
    return "low"


def status_badge_class(status):
    mapping = {
        "not_started": "badge bg-secondary",
        "in_progress": "badge bg-warning text-dark",
        "implemented": "badge bg-success",
        "not_applicable": "badge bg-info",
        "active": "badge bg-success",
        "inactive": "badge bg-secondary",
        "draft": "badge bg-secondary",
        "reviewed": "badge bg-info",
        "approved": "badge bg-primary",
        "published": "badge bg-success",
        "retired": "badge bg-danger",
        "planned": "badge bg-info",
        "completed": "badge bg-success",
        "open": "badge bg-danger",
        "closed": "badge bg-success",
        "identified": "badge bg-warning text-dark",
        "assessed": "badge bg-info",
        "treatment_in_progress": "badge bg-primary",
        "residual_accepted": "badge bg-success",
        "reported": "badge bg-warning text-dark",
        "investigating": "badge bg-primary",
        "contained": "badge bg-info",
        "resolved": "badge bg-success",
        "pending": "badge bg-secondary",
        "assessed": "badge bg-info",
        "approved": "badge bg-success",
        "rejected": "badge bg-danger",
        "review_required": "badge bg-warning text-dark",
        "low": "badge bg-success",
        "medium": "badge bg-warning text-dark",
        "high": "badge bg-danger",
        "critical": "badge bg-dark",
    }
    return mapping.get(status, "badge bg-secondary")
