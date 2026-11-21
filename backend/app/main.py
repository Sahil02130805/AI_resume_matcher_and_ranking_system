import os
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from . import db
from .jd import analyze_jd
from .matcher import rank
from .parser import extract_text, parse_resume

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "sample_data"
MAX_FILES = 200
MAX_BYTES = 10 * 1024 * 1024
app = FastAPI(title="AI Resume Matching & Ranking")


async def _jd_text(jd_text: Optional[str], jd_file: Optional[UploadFile]) -> str:
    if jd_file is not None and jd_file.filename:
        try:
            return extract_text(jd_file.filename, await jd_file.read())
        except ValueError as e:
            raise HTTPException(400, str(e))
    if jd_text and jd_text.strip():
        return jd_text
    raise HTTPException(400, "Provide a job description (paste text or upload PDF/DOCX).")


def _public(jd):
    return {k: v for k, v in jd.items() if k not in ("text", "requirement_lines")}


def _run(jd_text: str, files: list):
    """files: [(filename, bytes)]"""
    jd = analyze_jd(jd_text)
    if not (jd["required_skills"] or jd["preferred_skills"]):
        raise HTTPException(400, "Could not detect any known skills in the job description.")
    parsed, errors = [], []
    for name, data in files:
        try:
            if len(data) > MAX_BYTES:
                raise ValueError("file larger than 10 MB")
            parsed.append(parse_resume(name, data))
        except Exception as e:
            errors.append({"filename": name, "error": str(e)})
    if not parsed:
        raise HTTPException(400, {"message": "No resume could be parsed", "errors": errors})
    seen, unique = {}, []
    for r in parsed:                       # drop duplicate submissions of the same person (same e-mail)
        key = (r["email"] or "").lower()
        if key and key in seen:
            errors.append({"filename": r["filename"], "error": f"Duplicate of {seen[key]} (same e-mail) - skipped"})
            continue
        seen[key] = r["filename"]
        unique.append(r)
    candidates = rank(jd, unique)
    public = _public(jd)
    return {"id": db.save(public, candidates, errors), "jd": public, "candidates": candidates, "errors": errors}


@app.post("/api/jd/parse")
async def parse_jd(jd_text: Optional[str] = Form(None), jd_file: Optional[UploadFile] = File(None)):
    return _public(analyze_jd(await _jd_text(jd_text, jd_file)))


@app.post("/api/analyze")
async def analyze(jd_text: Optional[str] = Form(None), jd_file: Optional[UploadFile] = File(None),
                  resumes: List[UploadFile] = File(...)):
    text = await _jd_text(jd_text, jd_file)
    if len(resumes) > MAX_FILES:
        raise HTTPException(400, f"At most {MAX_FILES} resumes per batch")
    files = [(r.filename, await r.read()) for r in resumes]
    return _run(text, files)


@app.get("/api/sample")
def sample_jd():
    return {"jd_text": (SAMPLES / "job_description.txt").read_text(encoding="utf-8")}


@app.post("/api/analyze-sample")
def analyze_sample():
    files = [(p.name, p.read_bytes()) for p in sorted((SAMPLES / "resumes").iterdir()) if p.suffix in (".pdf", ".docx")]
    if not files:
        raise HTTPException(404, "Run scripts/generate_samples.py first.")
    return _run((SAMPLES / "job_description.txt").read_text(encoding="utf-8"), files)


@app.get("/api/analyses")
def analyses():
    return db.recent()


@app.get("/api/analyses/{aid}")
def get_analysis(aid: str):
    p = db.load(aid)
    if not p:
        raise HTTPException(404, "Analysis not found")
    return p


@app.get("/api/analyses/{aid}/candidates/{cid}")
def get_candidate(aid: str, cid: str):
    r = db.candidate(aid, cid)
    if not r:
        raise HTTPException(404, "Candidate not found")
    return r


DIST = ROOT / "frontend" / "dist"
if DIST.exists():       # production: serve the built React app
    app.mount("/", StaticFiles(directory=DIST, html=True), name="frontend")
else:
    @app.get("/")
    def _root():
        return {"message": "API running. Build the UI with `cd frontend && npm install && npm run build`, or run `npm run dev`."}
