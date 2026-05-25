# AI Resume Platform

A full-stack Flask app combining a resume analyzer, JD match calculator, and
resume builder with downloadable PDF output in two templates.

## Modules

| Module | What it does |
|---|---|
| **Resume Analyzer** | Upload PDF/DOCX, get an ATS score out of 100, plus strengths, weaknesses, keyword gaps, and formatting issues. |
| **Resume Builder** | Fill a form and download a polished PDF (Modern two-column or Classic single-column). |
| **JD Match Calculator** | Paste a job description, get a match percentage and missing-keyword list. |
| **Backend API** | JSON endpoints at `/api/analyze` and `/api/jd-match`. See `/api/docs` for details. |
| **Frontend UI** | Clean Bootstrap 5 interface with score rings, breakdown bars, and template picker. |
| **PDF Export** | Generated with reportlab — no headless browser required. |

## Project structure

```
resume/
  app.py                 Flask routes (pages + JSON API)
  analyzer.py            Text extraction + ATS scoring
  jd_matcher.py          JD vs resume keyword/skill matcher
  resume_builder.py      ResumeData model + PDF generation (modern/classic)
  requirements.txt
  templates/
    base.html
    home.html            dashboard
    analyzer.html        upload + run analyzer
    results.html         analyzer results
    builder.html         multi-section builder form
    builder_preview.html builder preview
    jd_match.html        JD match input
    jd_match_result.html JD match results
    api_docs.html        API documentation
  static/
    css/style.css
```

## Run locally

1. Create and activate a virtual environment

   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

2. Install dependencies

   ```powershell
   pip install -r requirements.txt
   ```

3. Start the server

   ```powershell
   python app.py
   ```

4. Open http://127.0.0.1:5000 in your browser.

## Routes

| Route | Method | Purpose |
|---|---|---|
| `/` | GET | Dashboard |
| `/analyzer` | GET | Upload form |
| `/analyze` | POST | Analyze uploaded resume |
| `/builder` | GET | Resume builder form |
| `/builder/preview` | POST | HTML preview of submitted data |
| `/builder/download` | POST | Download generated PDF |
| `/jd-match` | GET | JD match input |
| `/jd-match/analyze` | POST | Run JD match |
| `/api/docs` | GET | API documentation |
| `/api/analyze` | POST | JSON analysis endpoint |
| `/api/jd-match` | POST | JSON JD match endpoint |

## API examples

```bash
curl -X POST http://127.0.0.1:5000/api/analyze -F "resume=@resume.pdf"

curl -X POST http://127.0.0.1:5000/api/jd-match \
  -F "resume=@resume.pdf" \
  -F "jd_text=Senior Python engineer with AWS and Docker..."
```

## Notes

- Scanned/image-only PDFs are not analyzed (no OCR).
- Scoring is heuristic — use as guidance, not as a final ATS verdict.
- All processing is in-memory; no resume data is persisted on the server.
