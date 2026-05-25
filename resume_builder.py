"""Resume PDF generator with two templates (Modern + Classic) via reportlab."""

from __future__ import annotations

import io
from dataclasses import dataclass, field

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle,
)


TEMPLATES = ("modern", "classic")


@dataclass
class Experience:
    title: str = ""
    company: str = ""
    dates: str = ""
    bullets: list[str] = field(default_factory=list)


@dataclass
class Education:
    degree: str = ""
    school: str = ""
    dates: str = ""
    details: str = ""


@dataclass
class Project:
    name: str = ""
    tech: str = ""
    description: str = ""


@dataclass
class ResumeData:
    name: str = ""
    title: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin: str = ""
    summary: str = ""
    skills: list[str] = field(default_factory=list)
    experience: list[Experience] = field(default_factory=list)
    education: list[Education] = field(default_factory=list)
    projects: list[Project] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)


def _split_lines(text: str) -> list[str]:
    if not text:
        return []
    return [line.strip() for line in text.splitlines() if line.strip()]


def _split_csv(text: str) -> list[str]:
    if not text:
        return []
    return [s.strip() for s in text.split(",") if s.strip()]


def resume_from_form(form) -> ResumeData:
    """Build ResumeData from a Flask request.form (multi-value lists)."""
    data = ResumeData(
        name=form.get("name", "").strip(),
        title=form.get("title", "").strip(),
        email=form.get("email", "").strip(),
        phone=form.get("phone", "").strip(),
        location=form.get("location", "").strip(),
        linkedin=form.get("linkedin", "").strip(),
        summary=form.get("summary", "").strip(),
        skills=_split_csv(form.get("skills", "")),
        certifications=_split_lines(form.get("certifications", "")),
    )

    exp_titles = form.getlist("exp_title")
    exp_companies = form.getlist("exp_company")
    exp_dates = form.getlist("exp_dates")
    exp_bullets = form.getlist("exp_bullets")
    for t, c, d, b in zip(exp_titles, exp_companies, exp_dates, exp_bullets):
        if any([t, c, d, b]):
            data.experience.append(Experience(
                title=t.strip(), company=c.strip(), dates=d.strip(),
                bullets=_split_lines(b),
            ))

    edu_degrees = form.getlist("edu_degree")
    edu_schools = form.getlist("edu_school")
    edu_dates = form.getlist("edu_dates")
    edu_details = form.getlist("edu_details")
    for deg, s, d, det in zip(edu_degrees, edu_schools, edu_dates, edu_details):
        if any([deg, s, d, det]):
            data.education.append(Education(
                degree=deg.strip(), school=s.strip(), dates=d.strip(), details=det.strip(),
            ))

    proj_names = form.getlist("proj_name")
    proj_techs = form.getlist("proj_tech")
    proj_descs = form.getlist("proj_desc")
    for n, t, d in zip(proj_names, proj_techs, proj_descs):
        if any([n, t, d]):
            data.projects.append(Project(name=n.strip(), tech=t.strip(), description=d.strip()))

    return data


def _escape(text: str) -> str:
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_pdf(data: ResumeData, template: str = "modern") -> bytes:
    template = template if template in TEMPLATES else "modern"
    buf = io.BytesIO()
    if template == "modern":
        _build_modern(buf, data)
    else:
        _build_classic(buf, data)
    return buf.getvalue()


# ---------- Modern (two-column with sidebar) ----------

MODERN_ACCENT = colors.HexColor("#4f46e5")
MODERN_DARK = colors.HexColor("#1f2937")
MODERN_MUTED = colors.HexColor("#6b7280")
MODERN_SIDEBAR_BG = colors.HexColor("#eef2ff")


def _modern_styles():
    styles = {}
    styles["name"] = ParagraphStyle("name", fontName="Helvetica-Bold", fontSize=22,
                                     textColor=MODERN_DARK, leading=26)
    styles["title"] = ParagraphStyle("title", fontName="Helvetica", fontSize=12,
                                      textColor=MODERN_ACCENT, leading=15, spaceAfter=6)
    styles["section_main"] = ParagraphStyle("section_main", fontName="Helvetica-Bold",
                                             fontSize=12, textColor=MODERN_ACCENT,
                                             leading=14, spaceBefore=10, spaceAfter=4)
    styles["section_side"] = ParagraphStyle("section_side", fontName="Helvetica-Bold",
                                             fontSize=11, textColor=MODERN_ACCENT,
                                             leading=14, spaceBefore=8, spaceAfter=3)
    styles["body"] = ParagraphStyle("body", fontName="Helvetica", fontSize=10,
                                     textColor=MODERN_DARK, leading=13)
    styles["body_side"] = ParagraphStyle("body_side", fontName="Helvetica", fontSize=9.5,
                                          textColor=MODERN_DARK, leading=12.5)
    styles["muted"] = ParagraphStyle("muted", fontName="Helvetica-Oblique", fontSize=9.5,
                                      textColor=MODERN_MUTED, leading=12)
    styles["job_title"] = ParagraphStyle("job_title", fontName="Helvetica-Bold",
                                          fontSize=10.5, textColor=MODERN_DARK,
                                          leading=13, spaceBefore=4)
    styles["bullet"] = ParagraphStyle("bullet", fontName="Helvetica", fontSize=10,
                                       textColor=MODERN_DARK, leading=13,
                                       leftIndent=12, bulletIndent=2)
    return styles


def _build_modern(buf, data: ResumeData) -> None:
    page_w, page_h = LETTER
    margin = 0.5 * inch
    side_w = 2.1 * inch
    gutter = 0.25 * inch
    main_w = page_w - 2 * margin - side_w - gutter

    side_frame = Frame(margin, margin, side_w, page_h - 2 * margin,
                        leftPadding=12, rightPadding=12, topPadding=14, bottomPadding=14,
                        showBoundary=0)
    main_frame = Frame(margin + side_w + gutter, margin, main_w, page_h - 2 * margin,
                        leftPadding=4, rightPadding=4, topPadding=14, bottomPadding=14,
                        showBoundary=0)

    def draw_sidebar_bg(canvas, _doc):
        canvas.setFillColor(MODERN_SIDEBAR_BG)
        canvas.rect(margin, margin, side_w, page_h - 2 * margin, stroke=0, fill=1)

    s = _modern_styles()
    doc = BaseDocTemplate(buf, pagesize=LETTER, leftMargin=margin, rightMargin=margin,
                           topMargin=margin, bottomMargin=margin)

    # Sidebar content
    side_story = []
    side_story.append(Paragraph(_escape(data.name) or "Your Name", s["name"]))
    if data.title:
        side_story.append(Paragraph(_escape(data.title), s["title"]))
    side_story.append(Spacer(1, 6))

    side_story.append(Paragraph("CONTACT", s["section_side"]))
    contact_bits = [
        ("Email", data.email),
        ("Phone", data.phone),
        ("Location", data.location),
        ("LinkedIn", data.linkedin),
    ]
    for label, val in contact_bits:
        if val:
            side_story.append(Paragraph(f"<b>{label}:</b> {_escape(val)}", s["body_side"]))

    if data.skills:
        side_story.append(Paragraph("SKILLS", s["section_side"]))
        for skill in data.skills:
            side_story.append(Paragraph(f"&#9679; {_escape(skill)}", s["body_side"]))

    if data.certifications:
        side_story.append(Paragraph("CERTIFICATIONS", s["section_side"]))
        for cert in data.certifications:
            side_story.append(Paragraph(f"&#9679; {_escape(cert)}", s["body_side"]))

    if data.education:
        side_story.append(Paragraph("EDUCATION", s["section_side"]))
        for edu in data.education:
            if edu.degree:
                side_story.append(Paragraph(f"<b>{_escape(edu.degree)}</b>", s["body_side"]))
            if edu.school:
                side_story.append(Paragraph(_escape(edu.school), s["body_side"]))
            if edu.dates:
                side_story.append(Paragraph(_escape(edu.dates), s["muted"]))
            if edu.details:
                side_story.append(Paragraph(_escape(edu.details), s["body_side"]))
            side_story.append(Spacer(1, 4))

    # Main content
    main_story = []
    if data.summary:
        main_story.append(Paragraph("PROFESSIONAL SUMMARY", s["section_main"]))
        main_story.append(Paragraph(_escape(data.summary), s["body"]))

    if data.experience:
        main_story.append(Paragraph("EXPERIENCE", s["section_main"]))
        for exp in data.experience:
            header = f"<b>{_escape(exp.title)}</b>"
            if exp.company:
                header += f" &nbsp;&middot;&nbsp; {_escape(exp.company)}"
            main_story.append(Paragraph(header, s["job_title"]))
            if exp.dates:
                main_story.append(Paragraph(_escape(exp.dates), s["muted"]))
            for b in exp.bullets:
                main_story.append(Paragraph(f"&#8226; {_escape(b)}", s["bullet"]))
            main_story.append(Spacer(1, 6))

    if data.projects:
        main_story.append(Paragraph("PROJECTS", s["section_main"]))
        for proj in data.projects:
            header = f"<b>{_escape(proj.name)}</b>"
            if proj.tech:
                header += f" &nbsp;&middot;&nbsp; <i>{_escape(proj.tech)}</i>"
            main_story.append(Paragraph(header, s["job_title"]))
            if proj.description:
                main_story.append(Paragraph(_escape(proj.description), s["body"]))
            main_story.append(Spacer(1, 4))

    # Combine: render sidebar then main using a single PageTemplate with two frames.
    # reportlab needs the story to flow sidebar-first, then we'll force a FrameBreak.
    from reportlab.platypus.doctemplate import FrameBreak

    combined = side_story + [FrameBreak()] + main_story
    doc.addPageTemplates([
        PageTemplate(id="modern", frames=[side_frame, main_frame], onPage=draw_sidebar_bg)
    ])
    doc.build(combined)


# ---------- Classic (single column, traditional) ----------

CLASSIC_DARK = colors.HexColor("#111111")
CLASSIC_MUTED = colors.HexColor("#555555")
CLASSIC_RULE = colors.HexColor("#888888")


def _classic_styles():
    return {
        "name": ParagraphStyle("name", fontName="Times-Bold", fontSize=20,
                                textColor=CLASSIC_DARK, leading=24, alignment=TA_CENTER),
        "title": ParagraphStyle("title", fontName="Times-Italic", fontSize=12,
                                 textColor=CLASSIC_MUTED, leading=15, alignment=TA_CENTER),
        "contact": ParagraphStyle("contact", fontName="Times-Roman", fontSize=10,
                                   textColor=CLASSIC_DARK, leading=13, alignment=TA_CENTER),
        "section": ParagraphStyle("section", fontName="Times-Bold", fontSize=12,
                                   textColor=CLASSIC_DARK, leading=15, spaceBefore=10,
                                   spaceAfter=2, alignment=TA_LEFT),
        "body": ParagraphStyle("body", fontName="Times-Roman", fontSize=10.5,
                                textColor=CLASSIC_DARK, leading=14, alignment=TA_LEFT),
        "muted": ParagraphStyle("muted", fontName="Times-Italic", fontSize=10,
                                 textColor=CLASSIC_MUTED, leading=13),
        "job_title": ParagraphStyle("job_title", fontName="Times-Bold", fontSize=11,
                                     textColor=CLASSIC_DARK, leading=14, spaceBefore=4),
        "bullet": ParagraphStyle("bullet", fontName="Times-Roman", fontSize=10.5,
                                  textColor=CLASSIC_DARK, leading=14,
                                  leftIndent=14, bulletIndent=2),
    }


def _hr():
    from reportlab.platypus import HRFlowable
    return HRFlowable(width="100%", thickness=0.5, color=CLASSIC_RULE,
                      spaceBefore=2, spaceAfter=6)


def _build_classic(buf, data: ResumeData) -> None:
    s = _classic_styles()
    doc = BaseDocTemplate(buf, pagesize=LETTER,
                           leftMargin=0.75 * inch, rightMargin=0.75 * inch,
                           topMargin=0.6 * inch, bottomMargin=0.6 * inch)
    frame = Frame(doc.leftMargin, doc.bottomMargin,
                   doc.width, doc.height, showBoundary=0)
    doc.addPageTemplates([PageTemplate(id="classic", frames=[frame])])

    story = []
    story.append(Paragraph(_escape(data.name) or "Your Name", s["name"]))
    if data.title:
        story.append(Paragraph(_escape(data.title), s["title"]))

    contact_line = " &nbsp;&middot;&nbsp; ".join(
        _escape(x) for x in [data.email, data.phone, data.location, data.linkedin] if x
    )
    if contact_line:
        story.append(Paragraph(contact_line, s["contact"]))
    story.append(Spacer(1, 4))
    story.append(_hr())

    if data.summary:
        story.append(Paragraph("SUMMARY", s["section"]))
        story.append(Paragraph(_escape(data.summary), s["body"]))

    if data.skills:
        story.append(Paragraph("SKILLS", s["section"]))
        story.append(Paragraph(" &nbsp;&middot;&nbsp; ".join(_escape(s_) for s_ in data.skills), s["body"]))

    if data.experience:
        story.append(Paragraph("EXPERIENCE", s["section"]))
        for exp in data.experience:
            header = f"<b>{_escape(exp.title)}</b>"
            if exp.company:
                header += f", {_escape(exp.company)}"
            if exp.dates:
                header += f" &nbsp;&mdash;&nbsp; <i>{_escape(exp.dates)}</i>"
            story.append(Paragraph(header, s["job_title"]))
            for b in exp.bullets:
                story.append(Paragraph(f"&#8226; {_escape(b)}", s["bullet"]))
            story.append(Spacer(1, 4))

    if data.projects:
        story.append(Paragraph("PROJECTS", s["section"]))
        for proj in data.projects:
            header = f"<b>{_escape(proj.name)}</b>"
            if proj.tech:
                header += f" &nbsp;&mdash;&nbsp; <i>{_escape(proj.tech)}</i>"
            story.append(Paragraph(header, s["job_title"]))
            if proj.description:
                story.append(Paragraph(_escape(proj.description), s["body"]))
            story.append(Spacer(1, 4))

    if data.education:
        story.append(Paragraph("EDUCATION", s["section"]))
        for edu in data.education:
            header = f"<b>{_escape(edu.degree)}</b>"
            if edu.school:
                header += f", {_escape(edu.school)}"
            if edu.dates:
                header += f" &nbsp;&mdash;&nbsp; <i>{_escape(edu.dates)}</i>"
            story.append(Paragraph(header, s["job_title"]))
            if edu.details:
                story.append(Paragraph(_escape(edu.details), s["body"]))
            story.append(Spacer(1, 4))

    if data.certifications:
        story.append(Paragraph("CERTIFICATIONS", s["section"]))
        for cert in data.certifications:
            story.append(Paragraph(f"&#8226; {_escape(cert)}", s["bullet"]))

    doc.build(story)
