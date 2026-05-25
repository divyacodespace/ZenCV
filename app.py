"""Flask entry point for the AI Resume Platform.

Routes:
  /                          dashboard
  /analyzer                  upload form
  /analyze            POST   run analyzer, render results
  /builder                   resume builder form
  /builder/preview    POST   show summary of submitted data
  /builder/download   POST   download generated PDF (template=modern|classic)
  /jd-match                  JD match form
  /jd-match/analyze   POST   run JD match, render results
  /api/docs                  API documentation page
  /api/analyze        POST   JSON: multipart resume -> analysis JSON
  /api/jd-match       POST   JSON: multipart resume + jd_text -> match JSON
"""

from __future__ import annotations

import os
from dataclasses import asdict

from flask import (
    Flask, Response, flash, jsonify, redirect, render_template, request,
    send_file, url_for,
)
from werkzeug.utils import secure_filename

from analyzer import analyze
from jd_matcher import match as jd_match
from resume_builder import TEMPLATES, render_pdf, resume_from_form


ALLOWED_EXTENSIONS = {"pdf", "docx"}
MAX_UPLOAD_MB = 8


def _allowed(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[-1].lower() in ALLOWED_EXTENSIONS


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024

    # ---------- Pages ----------

    @app.route("/")
    def index():
        return render_template("home.html")

    @app.route("/analyzer")
    def analyzer_page():
        return render_template("analyzer.html")

    @app.route("/analyze", methods=["POST"])
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
        return render_template("results.html", r=result)

    @app.route("/builder")
    def builder_page():
        return render_template("builder.html", templates=TEMPLATES)

    @app.route("/builder/preview", methods=["POST"])
    def builder_preview():
        data = resume_from_form(request.form)
        template = request.form.get("template", "modern")
        if not data.name:
            flash("Please enter at least your name.", "warning")
            return redirect(url_for("builder_page"))
        return render_template("builder_preview.html", data=data, template=template,
                                templates=TEMPLATES)

    @app.route("/builder/download", methods=["POST"])
    def builder_download():
        data = resume_from_form(request.form)
        template = request.form.get("template", "modern")
        if not data.name:
            flash("Please enter at least your name.", "warning")
            return redirect(url_for("builder_page"))
        pdf_bytes = render_pdf(data, template=template)
        safe_name = secure_filename(data.name) or "resume"
        return send_file(
            _bytes_io(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"{safe_name}_{template}.pdf",
        )

    @app.route("/jd-match")
    def jd_match_page():
        return render_template("jd_match.html")

    @app.route("/jd-match/analyze", methods=["POST"])
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
        return render_template("jd_match_result.html", r=result)

    @app.route("/api/docs")
    def api_docs():
        return render_template("api_docs.html")

    # ---------- JSON API ----------

    @app.route("/api/analyze", methods=["POST"])
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
        return jsonify(payload)

    @app.route("/api/jd-match", methods=["POST"])
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
        return jsonify(asdict(result))

    @app.errorhandler(413)
    def too_large(_err):
        flash(f"File is larger than {MAX_UPLOAD_MB} MB.", "danger")
        return redirect(url_for("index"))

    return app


def _bytes_io(data: bytes):
    import io
    return io.BytesIO(data)


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
