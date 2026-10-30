"""
Candidate-matching service.

Scoring algorithm
-----------------
1. Skill score (60 % weight)
   For each required skill keyword, check whether it appears (as a whole word,
   case-insensitive) in the resume text.
   skill_score = (matched / total_required) * 100
   If the job has no required skills, skill_score = 100.

2. TF-IDF cosine similarity (40 % weight)
   Vectorise the job description and resume text with scikit-learn's
   TfidfVectorizer (English stop-words removed), then compute cosine similarity.
   tfidf_score = cosine_similarity * 100

3. Overall score
   overall_score = 0.6 * skill_score + 0.4 * tfidf_score   (rounded to 1 dp)

Ethical note
------------
Only the *content* of resume text and job descriptions is used.
No names, ages, genders, photographs, or other personal characteristics
enter the scoring calculation.  Scores are decision-support signals only.
"""

import re
from dataclasses import dataclass, field
from typing import List

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# ─── Weights ──────────────────────────────────────────────────────────────────
_SKILL_WEIGHT = 0.60
_TFIDF_WEIGHT = 0.40


@dataclass
class MatchResult:
    """Raw scoring result for one resume against one job."""

    resume_id: int
    original_filename: str
    skill_score: float          # 0–100
    tfidf_score: float          # 0–100
    overall_score: float        # 0–100
    matched_skills: List[str] = field(default_factory=list)
    missing_skills: List[str] = field(default_factory=list)
    resume_status: str = "processed"


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _skill_present(skill: str, text_lower: str) -> bool:
    """
    Return True if *skill* appears as a whole word (or compound) in *text_lower*.

    Uses a word-boundary regex so "sql" does not match "nosql" and
    "machine learning" matches when the two words appear adjacent.
    """
    # Escape special regex chars in skill name, then add word boundaries
    pattern = r"\b" + re.escape(skill) + r"\b"
    return bool(re.search(pattern, text_lower))


def _compute_skill_score(
    required_skills: List[str],
    resume_text: str,
) -> tuple[float, List[str], List[str]]:
    """
    Compute skill coverage.

    Returns:
        (score_0_to_100, matched_skills, missing_skills)
    """
    if not required_skills:
        return 100.0, [], []

    text_lower = resume_text.lower()
    matched, missing = [], []

    for skill in required_skills:
        if _skill_present(skill, text_lower):
            matched.append(skill)
        else:
            missing.append(skill)

    score = (len(matched) / len(required_skills)) * 100.0
    return round(score, 1), matched, missing


def _compute_tfidf_score(job_description: str, resume_text: str) -> float:
    """
    Compute TF-IDF cosine similarity between job description and resume.

    Returns a value in [0, 100].
    Handles empty inputs gracefully (returns 0.0).
    """
    jd = job_description.strip()
    rt = resume_text.strip()

    if not jd or not rt:
        return 0.0

    try:
        vectorizer = TfidfVectorizer(stop_words="english", min_df=1)
        tfidf_matrix = vectorizer.fit_transform([jd, rt])
        sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        return round(float(sim) * 100.0, 1)
    except Exception:
        # Fallback: if vectoriser fails (e.g. all tokens are stop-words), return 0
        return 0.0


# ─── Public API ───────────────────────────────────────────────────────────────

def score_resume(
    resume_id: int,
    original_filename: str,
    extracted_text: str | None,
    resume_status: str,
    job_description: str,
    required_skills: List[str],
) -> MatchResult:
    """
    Score a single resume against a job posting.

    Resumes with status != 'processed' or no extracted text receive score 0.
    """
    # Guard: unprocessable resume
    if resume_status != "processed" or not extracted_text:
        return MatchResult(
            resume_id=resume_id,
            original_filename=original_filename,
            skill_score=0.0,
            tfidf_score=0.0,
            overall_score=0.0,
            matched_skills=[],
            missing_skills=list(required_skills),
            resume_status=resume_status,
        )

    skill_score, matched, missing = _compute_skill_score(required_skills, extracted_text)
    tfidf_score = _compute_tfidf_score(job_description, extracted_text)

    overall = round(
        _SKILL_WEIGHT * skill_score + _TFIDF_WEIGHT * tfidf_score,
        1,
    )

    return MatchResult(
        resume_id=resume_id,
        original_filename=original_filename,
        skill_score=skill_score,
        tfidf_score=tfidf_score,
        overall_score=overall,
        matched_skills=matched,
        missing_skills=missing,
        resume_status=resume_status,
    )


def rank_resumes(
    resumes: list,          # list of Resume ORM instances
    job_description: str,
    required_skills: List[str],
) -> List[MatchResult]:
    """
    Score and rank all resumes for a given job, highest score first.

    Args:
        resumes:          All Resume ORM objects to evaluate.
        job_description:  Full text of the job posting.
        required_skills:  Normalised list of required skill keywords.

    Returns:
        List of MatchResult sorted descending by overall_score.
    """
    results = [
        score_resume(
            resume_id=r.id,
            original_filename=r.original_filename,
            extracted_text=r.extracted_text,
            resume_status=r.status,
            job_description=job_description,
            required_skills=required_skills,
        )
        for r in resumes
    ]
    results.sort(key=lambda x: x.overall_score, reverse=True)
    return results
