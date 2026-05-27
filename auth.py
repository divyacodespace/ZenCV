"""Authentication blueprint: signup, login, logout, account dashboard."""

from __future__ import annotations

import json
from datetime import datetime

from email_validator import EmailNotValidError, validate_email
from flask import (
    Blueprint, flash, redirect, render_template, request, url_for,
)
from flask_login import current_user, login_required, login_user, logout_user

from models import AnalysisRecord, JDMatchRecord, User, db


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm") or ""

        if not name or len(name) < 2:
            flash("Please enter your full name.", "warning")
            return render_template("signup.html", name=name, email=email)

        try:
            email = validate_email(email, check_deliverability=False).normalized
        except EmailNotValidError as e:
            flash(f"Invalid email: {e}", "warning")
            return render_template("signup.html", name=name, email=email)

        if len(password) < 8:
            flash("Password must be at least 8 characters.", "warning")
            return render_template("signup.html", name=name, email=email)

        if password != confirm:
            flash("Passwords do not match.", "warning")
            return render_template("signup.html", name=name, email=email)

        if User.query.filter_by(email=email).first():
            flash("An account with that email already exists. Try logging in.", "warning")
            return render_template("signup.html", name=name, email=email)

        user = User(name=name, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        user.last_login_at = datetime.utcnow()
        db.session.commit()

        flash(f"Welcome, {user.name.split()[0]}!", "success")
        return redirect(url_for("index"))

    return render_template("signup.html")


@auth_bp.route("/logout", methods=["POST", "GET"])
@login_required
def logout():
    logout_user()
    flash("You've been logged out.", "success")
    return redirect(url_for("auth.signup"))


@auth_bp.route("/account")
@login_required
def account():
    analyses = current_user.analyses.limit(20).all()
    matches = current_user.jd_matches.limit(20).all()

    # Decode payloads for display
    decoded_analyses = []
    for a in analyses:
        try:
            data = json.loads(a.payload_json)
        except Exception:
            data = {}
        decoded_analyses.append({"record": a, "data": data})

    decoded_matches = []
    for m in matches:
        try:
            data = json.loads(m.payload_json)
        except Exception:
            data = {}
        decoded_matches.append({"record": m, "data": data})

    return render_template(
        "account.html",
        analyses=decoded_analyses,
        matches=decoded_matches,
        total_analyses=current_user.analyses.count(),
        total_matches=current_user.jd_matches.count(),
    )


@auth_bp.route("/account/analysis/<int:record_id>")
@login_required
def view_analysis(record_id: int):
    rec = AnalysisRecord.query.filter_by(id=record_id, user_id=current_user.id).first_or_404()
    data = json.loads(rec.payload_json)
    # Re-hydrate enough fields for results.html to render.
    from types import SimpleNamespace
    r = SimpleNamespace(**data)
    if not hasattr(r, "filename"):
        r.filename = rec.filename
    return render_template("results.html", r=r, from_history=True, created_at=rec.created_at)


@auth_bp.route("/account/match/<int:record_id>")
@login_required
def view_match(record_id: int):
    rec = JDMatchRecord.query.filter_by(id=record_id, user_id=current_user.id).first_or_404()
    data = json.loads(rec.payload_json)
    from types import SimpleNamespace
    r = SimpleNamespace(**data)
    return render_template("jd_match_result.html", r=r, from_history=True, created_at=rec.created_at)
