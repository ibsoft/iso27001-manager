from flask import Blueprint, render_template
from flask_login import login_required
from flask_babel import gettext as _
from app.models.clause import Clause

clauses_bp = Blueprint("clauses", __name__)


@clauses_bp.route("/")
@login_required
def list_clauses():
    clauses = Clause.query.order_by(Clause.number).all()
    return render_template("clauses/list.html", clauses=clauses)


@clauses_bp.route("/<int:clause_id>")
@login_required
def view_clause(clause_id):
    clause = Clause.query.get_or_404(clause_id)
    return render_template("clauses/view.html", clause=clause)
