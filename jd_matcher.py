"""Compare a resume against a job description and surface keyword / skill gaps."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from analyzer import COMMON_SKILLS, extract_text


STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "if", "then", "else", "for", "of", "to",
    "in", "on", "at", "by", "with", "from", "as", "is", "are", "was", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "should", "could", "may", "might", "can", "must", "shall", "this", "that",
    "these", "those", "it", "its", "they", "them", "their", "we", "our", "you",
    "your", "i", "me", "my", "he", "she", "his", "her", "who", "what", "which",
    "when", "where", "why", "how", "all", "any", "each", "every", "some", "no",
    "not", "only", "own", "same", "so", "than", "too", "very", "just", "also",
    "about", "into", "through", "during", "before", "after", "above", "below",
    "up", "down", "out", "off", "over", "under", "again", "further", "such",
    "more", "most", "other", "another", "good", "great", "well", "best", "team",
    "work", "working", "role", "job", "company", "candidate", "candidates",
    "applicant", "year", "years", "experience", "experienced", "ability",
    "responsibilities", "responsibility", "requirements", "required", "preferred",
    "qualifications", "qualified", "must", "plus", "etc", "including", "include",
    "includes", "knowledge", "skills", "skill", "strong", "excellent", "ideal",
    "looking", "join", "us", "you'll", "you're", "we're",
}

ALL_SKILLS = {skill for skills in COMMON_SKILLS.values() for skill in skills}


@dataclass
class JDMatchResult:
    match_score: int
    matched_keywords: list[str]
    missing_keywords: list[str]
    matched_skills: list[str]
    missing_skills: list[str]
    jd_word_count: int
    resume_word_count: int
    top_jd_terms: list[tuple[str, int]] = field(default_factory=list)
    verdict: str = ""
    suggestions: list[str] = field(default_factory=list)


def _tokenize(text: str) -> list[str]:
    raw = re.findall(r"[A-Za-z][A-Za-z+#.\-]{1,}", text.lower())
    return [t.strip(".-") for t in raw if t.strip(".-")]


def _keyword_frequencies(text: str) -> Counter:
    tokens = _tokenize(text)
    return Counter(t for t in tokens if t not in STOP_WORDS and len(t) > 2)


def _extract_phrases(text: str) -> set[str]:
    """Pull multi-word phrases like 'machine learning', 'ci/cd', 'node.js'."""
    found: set[str] = set()
    lowered = text.lower()
    for skill in ALL_SKILLS:
        if " " in skill or "/" in skill or "." in skill or "+" in skill:
            if skill in lowered:
                found.add(skill)
    return found


def _resume_text(file_or_text) -> str:
    if isinstance(file_or_text, str):
        return file_or_text
    return extract_text(file_or_text)


def match(resume_input, jd_text: str) -> JDMatchResult:
    resume_text = _resume_text(resume_input)
    if not resume_text or len(resume_text.split()) < 30:
        raise ValueError("Could not read enough resume text. Provide a clearer file or paste text.")
    if not jd_text or len(jd_text.split()) < 15:
        raise ValueError("Job description is too short — paste the full posting.")

    resume_lower = resume_text.lower()
    jd_counts = _keyword_frequencies(jd_text)

    jd_phrases = _extract_phrases(jd_text)
    resume_phrases = _extract_phrases(resume_text)

    top_terms = [(w, c) for w, c in jd_counts.most_common(40) if c >= 1]

    matched_keywords: list[str] = []
    missing_keywords: list[str] = []
    for word, _ in top_terms[:25]:
        if re.search(rf"\b{re.escape(word)}\b", resume_lower):
            matched_keywords.append(word)
        else:
            missing_keywords.append(word)

    matched_skills = sorted(jd_phrases & resume_phrases)
    matched_skills += [s for s in ALL_SKILLS
                       if " " not in s and "/" not in s and "." not in s and "+" not in s
                       and s in jd_counts and s in resume_lower
                       and s not in matched_skills]
    missing_skills = sorted(jd_phrases - resume_phrases)
    missing_skills += [s for s in ALL_SKILLS
                       if " " not in s and "/" not in s and "." not in s and "+" not in s
                       and s in jd_counts and s not in resume_lower
                       and s not in missing_skills]

    total_top = max(1, len(matched_keywords) + len(missing_keywords))
    keyword_score = (len(matched_keywords) / total_top) * 70

    total_skills = len(matched_skills) + len(missing_skills)
    skill_score = (len(matched_skills) / total_skills) * 30 if total_skills else 15

    match_score = int(round(keyword_score + skill_score))
    match_score = max(0, min(100, match_score))

    if match_score >= 80:
        verdict = "Strong match — your resume aligns well with this role."
    elif match_score >= 60:
        verdict = "Decent match — add a few missing keywords to push higher."
    elif match_score >= 40:
        verdict = "Partial match — meaningful gaps to close before applying."
    else:
        verdict = "Low match — significant rewriting needed for this role."

    suggestions: list[str] = []
    if missing_skills:
        suggestions.append(
            "Add these JD-aligned skills where they truthfully apply: "
            + ", ".join(missing_skills[:8]) + "."
        )
    if missing_keywords:
        suggestions.append(
            "Weave these recurring JD keywords into your bullets: "
            + ", ".join(missing_keywords[:8]) + "."
        )
    suggestions.append("Mirror the JD's phrasing for tools and responsibilities — ATS scoring rewards exact matches.")
    suggestions.append("Quantify experience related to the top JD requirements (years, scale, impact).")

    return JDMatchResult(
        match_score=match_score,
        matched_keywords=matched_keywords,
        missing_keywords=missing_keywords,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        jd_word_count=len(jd_text.split()),
        resume_word_count=len(resume_text.split()),
        top_jd_terms=top_terms[:15],
        verdict=verdict,
        suggestions=suggestions,
    )
