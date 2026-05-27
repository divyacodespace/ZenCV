"""Flask entry point for ZenCV — powered by Clyra."""

from __future__ import annotations

import io
import json
import os
from dataclasses import asdict

from flask import (
    Flask, flash, jsonify, redirect, render_template, request, send_file, url_for,
)
from flask_login import LoginManager, current_user, login_required
from werkzeug.utils import secure_filename

from analyzer import analyze
from auth import auth_bp
from jd_matcher import match as jd_match
from models import AnalysisRecord, JDMatchRecord, User, db
from resume_builder import TEMPLATES, render_pdf, resume_from_form


ALLOWED_EXTENSIONS = {"pdf", "docx"}
MAX_UPLOAD_MB = 8


def _allowed(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[-1].lower() in ALLOWED_EXTENSIONS


def create_app() -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024

    # Database
    # 1) honor an explicit DATABASE_URL (Vercel Postgres / Neon / Supabase / etc.)
    # 2) on Vercel without a hosted DB, fall back to SQLite under /tmp (ephemeral)
    # 3) locally, use instance/app.db (persists in the project's instance/ dir)
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        # SQLAlchemy 2.x needs postgresql:// not the legacy postgres:// scheme
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
    elif os.environ.get("VERCEL"):
        db_url = "sqlite:////tmp/app.db"
    else:
        os.makedirs(app.instance_path, exist_ok=True)
        db_url = f"sqlite:///{os.path.join(app.instance_path, 'app.db')}"
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    # Login manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to continue."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Auth blueprint
    app.register_blueprint(auth_bp)

    # Create tables on startup
    with app.app_context():
        db.create_all()

    # ---------- Pages (all require login) ----------

    @app.route("/")
    @login_required
    def index():
        return render_template("home.html")

    @app.route("/analyzer")
    @login_required
    def analyzer_page():
        return render_template("analyzer.html")

    @app.route("/analyze", methods=["POST"])
    @login_required
    def analyze_resume():
        file = request.files.get("resume")
        if not file or not file.filename or not _allowed(file.filename):
            flash("Upload a valid .pdf or .docx file.", "danger")
            return redirect(url_for("analyzer_page"))
        file.filename = secure_filename(file.filename)
        try:
            result = analyze(file)
        except ValueError as exc:
            flash(str(exc), "warning")
            return redirect(url_for("analyzer_page"))
        except Exception:
            flash("Something went wrong reading your resume.", "danger")
            return redirect(url_for("analyzer_page"))

        # Persist for history
        payload = asdict(result)
        payload.pop("text", None)
        rec = AnalysisRecord(
            user_id=current_user.id,
            filename=result.filename,
            ats_score=result.ats_score,
            word_count=result.word_count,
            payload_json=json.dumps(payload),
        )
        db.session.add(rec)
        db.session.commit()

        return render_template("results.html", r=result)

    @app.route("/builder")
    @login_required
    def builder_page():
        return render_template("builder.html", templates=TEMPLATES)

    @app.route("/builder/preview", methods=["POST"])
    @login_required
    def builder_preview():
        data = resume_from_form(request.form)
        template = request.form.get("template", "modern")
        if not data.name:
            flash("Please enter at least your name.", "warning")
            return redirect(url_for("builder_page"))
        return render_template("builder_preview.html", data=data, template=template,
                                templates=TEMPLATES)

    @app.route("/builder/download", methods=["POST"])
    @login_required
    def builder_download():
        data = resume_from_form(request.form)
        template = request.form.get("template", "modern")
        if not data.name:
            flash("Please enter at least your name.", "warning")
            return redirect(url_for("builder_page"))
        pdf_bytes = render_pdf(data, template=template)
        safe_name = secure_filename(data.name) or "resume"
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"{safe_name}_{template}.pdf",
        )

    @app.route("/jd-match")
    @login_required
    def jd_match_page():
        return render_template("jd_match.html")

    @app.route("/jd-match/analyze", methods=["POST"])
    @login_required
    def jd_match_analyze():
        jd_text = (request.form.get("jd_text") or "").strip()
        resume_text = (request.form.get("resume_text") or "").strip()
        file = request.files.get("resume")

        try:
            if file and file.filename and _allowed(file.filename):
                file.filename = secure_filename(file.filename)
                result = jd_match(file, jd_text)
            elif resume_text:
                result = jd_match(resume_text, jd_text)
            else:
                flash("Provide a resume file or paste resume text.", "warning")
                return redirect(url_for("jd_match_page"))
        except ValueError as exc:
            flash(str(exc), "warning")
            return redirect(url_for("jd_match_page"))
        except Exception:
            flash("Something went wrong analyzing the JD match.", "danger")
            return redirect(url_for("jd_match_page"))

        payload = asdict(result)
        rec = JDMatchRecord(
            user_id=current_user.id,
            match_score=result.match_score,
            jd_preview=jd_text[:280],
            payload_json=json.dumps(payload),
        )
        db.session.add(rec)
        db.session.commit()

        return render_template("jd_match_result.html", r=result)

    @app.route("/api/docs")
    @login_required
    def api_docs():
        return render_template("api_docs.html")

    # ---------- JSON API (also require login via session) ----------

    @app.route("/api/analyze", methods=["POST"])
    @login_required
    def api_analyze():
        file = request.files.get("resume")
        if not file or not file.filename or not _allowed(file.filename):
            return jsonify({"error": "missing or invalid 'resume' file (.pdf or .docx)"}), 400
        file.filename = secure_filename(file.filename)
        try:
            result = analyze(file)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        payload = asdict(result)
        payload.pop("text", None)

        rec = AnalysisRecord(
            user_id=current_user.id,
            filename=result.filename,
            ats_score=result.ats_score,
            word_count=result.word_count,
            payload_json=json.dumps(payload),
        )
        db.session.add(rec)
        db.session.commit()

        return jsonify(payload)

    @app.route("/api/jd-match", methods=["POST"])
    @login_required
    def api_jd_match():
        jd_text = (request.form.get("jd_text") or "").strip()
        resume_text = (request.form.get("resume_text") or "").strip()
        file = request.files.get("resume")
        if not jd_text:
            return jsonify({"error": "missing 'jd_text' form field"}), 400
        try:
            if file and file.filename and _allowed(file.filename):
                file.filename = secure_filename(file.filename)
                result = jd_match(file, jd_text)
            elif resume_text:
                result = jd_match(resume_text, jd_text)
            else:
                return jsonify({"error": "provide 'resume' file or 'resume_text'"}), 400
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        payload = asdict(result)
        rec = JDMatchRecord(
            user_id=current_user.id,
            match_score=result.match_score,
            jd_preview=jd_text[:280],
            payload_json=json.dumps(payload),
        )
        db.session.add(rec)
        db.session.commit()

        return jsonify(payload)

    @app.errorhandler(413)
    def too_large(_err):
        flash(f"File is larger than {MAX_UPLOAD_MB} MB.", "danger")
        return redirect(url_for("index"))

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
