# AI Resume Matching & Candidate Ranking System

Paste/upload a Job Description and a batch of resumes (PDF/DOCX) → every candidate gets a 0–100 match score, a ranking, matched/missing skills, an experience comparison and a plain-English explanation with resume evidence.
All bundled resumes are **synthetic** (`scripts/generate_samples.py`); no real personal data.

**Stack:** React (Vite) · FastAPI · spaCy + Sentence-Transformers · PostgreSQL (SQLAlchemy; SQLite fallback)

## Run it
**Docker (one command, PostgreSQL included):**
```bash
docker compose up --build      # http://localhost:8000
```
**Local:**
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && python -m spacy download en_core_web_sm
python scripts/generate_samples.py
export DATABASE_URL=postgresql://user:pass@localhost:5432/resume_matcher   # omit to use SQLite
cd backend && uvicorn app.main:app --reload                                # API + built UI on :8000
# UI development:  cd frontend && npm install && npm run dev               # :5173, proxies /api
```
Click **Run with 14 sample resumes** for an instant demo. `pytest -q tests` runs 11 tests; `python scripts/evaluate.py` prints ranking quality vs human gold labels.
Env: `DATABASE_URL`, `EMBEDDING_MODEL` (default `all-MiniLM-L6-v2`), `USE_TFIDF=1` (force offline fallback).

## Architecture
```
frontend/ (React)  ──/api──►  backend/app/main.py  (FastAPI)
                                ├─ parser.py     PDF/DOCX → sections, contact, jobs(title/company/dates), education, skill evidence
                                ├─ nlp.py        spaCy: PhraseMatcher skill extraction (longest-match), NER (name/orgs), sentences
                                ├─ jd.py         JD → weighted requirements (required/preferred/core, OR-groups, per-skill years)
                                ├─ skills.py     taxonomy (~90 skills + aliases) and related-skill graph
                                ├─ embeddings.py Sentence-Transformers (MiniLM) or TF-IDF fallback
                                ├─ matcher.py    scoring, ceilings, explanations, ranking
                                └─ db.py         SQLAlchemy: analyses + candidate_results (JSON explanation docs)
```

## Parsing
* **Skills** – spaCy `PhraseMatcher` over the taxonomy, overlaps resolved by longest match (so "Spring Boot" ≠ "Spring", "Java" never fires in "JavaScript"). Ambiguous words (REST, ML, Spring, Express) count only when capitalised.
* **Experience** – jobs start at a date-range line (`Mar 2020 – Present`, `2018-2021`, `03/2019 – 05/2021`); title/company are parsed from the line or the lines above it. Years come from a **month-level union**, so overlapping jobs are never double counted; internships count ×0.5.
* **Skill evidence** – each skill records whether it appears in a job (with months used and last-used date), only in projects, or only in the skills list.
* **Education** – degree level, field, institution (NER), year. **Name** – spaCy PERSON entity with heuristics fallback.
* Each resume gets `parse_quality`/`warnings` (missing e-mail, no dates, …); unreadable files (e.g. scanned PDFs) are reported, never silently scored; duplicate e-mails are skipped.

## JD analysis
Not a keyword bag: each requirement has a **weight** (skill in the job title = core 3.0, required 1.0, preferred / "nice to have" / "a plus" 0.5), alternatives (**"Kafka or RabbitMQ"** = one requirement, best member counts), optional **minimum years for a skill** ("3+ years of Python"), general **years range** ("5–8 years of experience") and minimum education.

## Scoring — how the % is calculated
`Match % = min( ceilings , 100 × Σ weightᵢ × componentᵢ )` (weights re-normalised if the JD has no experience/education requirement)

| Component | Weight | Computation |
|---|---|---|
| **Skills** | 45% | Weighted average over JD requirements of `credit`. Credit = *match quality* × *evidence* × *years* × *recency*. Match quality: exact 1.0; **related skill** partial (Spring→Spring Boot 0.8, PostgreSQL→SQL 0.9, Jenkins→CI/CD 1.0); with embeddings, semantically similar skill = 0.8×cosine (≥0.55). Evidence: used in a job 1.0 / project only 0.9 / listed only 0.75 (Agile, Git exempt). Years: `0.5+0.5·min(1, years/required)`. Recency: last used ≤3 y 1.0, ≤6 y 0.9, older 0.8. |
| **Semantic fit** | 25% | Each JD requirement sentence ↔ its best-matching resume sentence (cosine), averaged and calibrated to 0–1. Catches the same experience described in different words, and supplies the evidence sentences shown to recruiters. |
| **Experience** | 20% | `min(1, (0.7·relevant_yrs + 0.3·total_yrs) / required_yrs)`. A job's *relevance* = share of required skills it demonstrates ÷ 0.4 (capped at 1); relevant years are the month-level union weighted by that relevance, so 7 years in an unrelated role don't count as 7 years of fit. Over-qualification isn't penalised. |
| **Education** | 10% | Meets level 1.0 · one below 0.6 · lower 0.3. |

**Ceilings (guard rails):** `35 + 65·min(1, required_coverage/0.7)` stops soft semantic similarity rescuing a candidate who lacks the required skills; `35 + 65·min(1, evidenced_coverage/0.5)` stops **keyword stuffing** (a resume that lists every skill but shows none in any job is capped at 35). When a cap applies, the explanation says so.

Every candidate response contains the score breakdown (`score × weight = points`), per-skill evidence/years/last-used, written reasons, best and weakest resume↔JD evidence, and parse warnings.

## Evaluation
`sample_data/gold_labels.json` holds human relevance grades for the 14 sample resumes (including adversarial cases: a keyword-stuffer, overlapping freelance jobs, synonym-heavy wording). `scripts/evaluate.py` reports **NDCG@5 = 1.00** and **pairwise order accuracy ≈ 0.95** (TF-IDF fallback); a test enforces thresholds.

## Honest limitations
* No scoring system is "perfect": the taxonomy is hand-curated (~90 skills), so skills outside it are only seen through the semantic component. Extend `skills.py` or add ESCO/O*NET.
* The TF-IDF fallback is lexical; the sample run showed it under-scoring a Java/Spring candidate semantically. Install `sentence-transformers` for true semantic matching (calibration constants in `embeddings.py` should be tuned on your own labelled data).
* Scanned PDFs need OCR (not included). Multi-column PDFs may be read out of order.
* Weights/thresholds are documented constants chosen by reasoning, not learned; with real labelled outcomes they could be fitted (e.g. logistic regression over the four components).
* Scoring ignores name, gender, age, photo and location by design, but a human should review any automated ranking.
