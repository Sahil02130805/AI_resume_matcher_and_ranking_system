"""Resume parsing: PDF/DOCX -> text -> structured profile (contact, jobs, skills with evidence, education)."""
import io, re
from datetime import date
from .nlp import extract_skills, orgs, person_name

TODAY = date.today()
NOW_IDX = TODAY.year * 12 + TODAY.month
MONTHS = {m: i + 1 for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split())}
_MON = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?"
_DATE = rf"(?:{_MON}\s+\d{{4}}|\d{{1,2}}/\d{{4}}|\d{{4}})"
RANGE_RE = re.compile(rf"({_DATE})\s*(?:-|–|—|to)\s*({_DATE}|present|current|now|till date|ongoing)", re.I)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"\+?\d[\d\s().-]{8,}\d")
BULLET_RE = re.compile(r"^\s*[•\-\*·▪●◦]\s*")
HEADING_RE = re.compile(
    r"^\s*(professional\s+|technical\s+|key\s+|core\s+)?(summary|profile|objective|skills|competencies|experience|"
    r"work experience|employment( history)?|education|academic( background)?|projects|personal projects|certifications?|achievements)\s*:?\s*$", re.I)
LEVEL_NAMES = {0: "Not specified", 1: "Diploma", 2: "Bachelor's", 3: "Master's", 4: "PhD"}


# ---------------- text extraction ----------------
def extract_text(filename: str, data: bytes) -> str:
    name = filename.lower()
    if name.endswith(".pdf"):
        import pdfplumber
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            text = "\n".join((p.extract_text() or "") for p in pdf.pages)
    elif name.endswith(".docx"):
        import docx
        d = docx.Document(io.BytesIO(data))
        parts = [p.text for p in d.paragraphs]
        for t in d.tables:
            for row in t.rows:
                parts.append(" | ".join(c.text for c in row.cells))
        text = "\n".join(parts)
    elif name.endswith(".txt"):
        text = data.decode("utf-8", errors="ignore")
    else:
        raise ValueError(f"Unsupported file type: {filename} (use PDF or DOCX)")
    return text.replace("\u00a0", " ").replace("\r", "")


# ---------------- education ----------------
def education_levels(text: str) -> set:
    t, found = text.lower(), set()
    for lvl, pat in [(4, r"ph\.?d|doctorate"), (3, r"master|m\.?tech|mtech|m\.?sc\b|\bmba\b|\bmca\b"),
                     (2, r"bachelor|b\.?tech|btech|b\.?sc\b|\bbca\b|undergraduate|\bdegree\b"), (1, r"diploma")]:
        if re.search(pat, t):
            found.add(lvl)
    if re.search(r"\bM\.?E\b\.?|\bM\.?S\b\.? in", text):   # case-sensitive: "be"/"me" are ordinary words
        found.add(3)
    if re.search(r"\bB\.E\b\.?|\bBE\b", text):
        found.add(2)
    return found


def parse_education(edu_text: str) -> list:
    out = []
    for line in edu_text.splitlines():
        lv = education_levels(line)
        if not lv:
            continue
        field = re.search(r"\bin\s+([A-Za-z&][A-Za-z &]+?)(?:,|\||\(|\s-\s|$)", line)
        years = re.findall(r"(?:19|20)\d{2}", line)
        inst = next((p.strip() for p in re.split(r",|\|", line)
                     if re.search(r"univers|institute|college|school|iit|nit\b", p, re.I)), None)
        if not inst:
            o = orgs(line)
            inst = o[0] if o else None
        out.append({"text": line.strip(), "level": max(lv), "degree": LEVEL_NAMES[max(lv)],
                    "field": field.group(1).strip() if field else None, "institution": inst,
                    "year": int(years[-1]) if years else None})
    return out


# ---------------- sections & dates ----------------
def split_sections(text: str) -> dict:
    sections, current = {"header": []}, "header"
    for line in text.splitlines():
        m = HEADING_RE.match(line)
        if m:
            h = m.group(2).lower()
            current = ("skills" if h in ("skills", "competencies") else
                       "experience" if "experience" in h or "employment" in h else
                       "education" if h == "education" or h.startswith("academic") else
                       "summary" if h in ("summary", "profile", "objective") else
                       "projects" if "project" in h else h)
            sections.setdefault(current, [])
        else:
            sections[current].append(line)
    return {k: "\n".join(v).strip() for k, v in sections.items()}


def _parse_date(s: str, is_end: bool) -> int:
    """-> month index (year*12+month)."""
    s = s.strip().lower()
    if s in ("present", "current", "now", "till date", "ongoing"):
        return NOW_IDX
    m = re.match(rf"({_MON})\s+(\d{{4}})", s)
    if m:
        return int(m.group(2)) * 12 + MONTHS[m.group(1)[:3]]
    m = re.match(r"(\d{1,2})/(\d{4})", s)
    if m:
        return int(m.group(2)) * 12 + int(m.group(1))
    return int(s[:4]) * 12 + (12 if is_end else 1)


def merged_months(intervals) -> int:
    """Union length (in months) of (start_idx, end_idx) intervals: concurrent jobs are not double counted."""
    iv = sorted((s, e) for s, e in intervals if e >= s)
    total, cs, ce = 0, None, None
    for s, e in iv:
        if ce is None or s > ce + 1:
            if ce is not None:
                total += ce - cs + 1
            cs, ce = s, e
        else:
            ce = max(ce, e)
    return total + (ce - cs + 1 if ce is not None else 0)


def _split_header(h: str):
    parts = [p.strip() for p in re.split(r"\s*[|·@]\s*|\s+at\s+|\s+-\s+", h) if p.strip()]
    if not parts:
        return None, None
    if "," in parts[0]:
        t, c = [x.strip() for x in parts[0].split(",", 1)]
        return t, c
    return parts[0], parts[1] if len(parts) > 1 else None


def parse_jobs(exp_text: str) -> list:
    """A job starts on a line holding a date range. If that line has no title text, the title/company is
    taken from the non-bullet lines directly above it."""
    jobs, cur, recent = [], None, []
    for line in exp_text.splitlines():
        s = line.strip()
        m = RANGE_RE.search(s)
        if m:
            rest = (s[:m.start()] + " " + s[m.end():]).strip(" |,-–—()@·")
            if not rest and recent:
                rest = " | ".join(recent[-2:][::-1]) if len(recent) > 1 else recent[-1]
                if cur:
                    cur["lines"] = cur["lines"][:max(0, len(cur["lines"]) - len(recent[-2:]))]
            if cur:
                jobs.append(cur)
            cur = {"hdr": rest, "start": _parse_date(m.group(1), False), "end": _parse_date(m.group(2), True), "lines": []}
            recent = []
        elif cur is not None:
            cur["lines"].append(line)
            recent = recent + [s] if s and not BULLET_RE.match(s) and len(s) < 80 else []
        elif s and not BULLET_RE.match(s):
            recent.append(s)
    if cur:
        jobs.append(cur)
    out = []
    for j in jobs:
        if j["end"] < j["start"]:
            continue
        title, company = _split_header(j["hdr"])
        body = "\n".join(j["lines"]).strip()
        s, e = j["start"], j["end"]
        out.append({"title": title, "company": company, "header": j["hdr"], "text": body,
                    "start": f"{(s - 1) // 12}-{(s - 1) % 12 + 1:02d}", "end": f"{(e - 1) // 12}-{(e - 1) % 12 + 1:02d}",
                    "start_idx": s, "end_idx": e, "months": e - s + 1,
                    "is_intern": bool(re.search(r"intern|trainee|apprentice", (title or "") + " " + j["hdr"], re.I)),
                    "skills": sorted(extract_skills((title or "") + "\n" + body))})
    return out


def weighted_years(jobs, key=None) -> float:
    """Years of experience from month-level union. Internships count 0.5; overlapping jobs count once.
    `key(job)` may return a 0..1 relevance multiplier."""
    best = {}
    for j in jobs:
        w = (0.5 if j["is_intern"] else 1.0) * (key(j) if key else 1.0)
        if w <= 0:
            continue
        for mth in range(j["start_idx"], j["end_idx"] + 1):
            if best.get(mth, 0) < w:
                best[mth] = w
    return round(sum(best.values()) / 12, 1)


# ---------------- main ----------------
def parse_resume(filename: str, data: bytes) -> dict:
    text = extract_text(filename, data)
    if len(text.strip()) < 30:
        raise ValueError("No readable text found (scanned/image-only PDF? OCR is not enabled)")
    sec = split_sections(text)
    warnings = []

    m = EMAIL_RE.search(text)
    email = m.group(0) if m else None
    phone = None
    for line in (sec["header"] or text[:300]).splitlines()[:8]:
        for pm in PHONE_RE.finditer(EMAIL_RE.sub("", line)):
            if len(re.sub(r"\D", "", pm.group(0))) >= 10:
                phone = pm.group(0).strip()
                break
        if phone:
            break

    name = person_name(sec["header"] or text)
    if not name:
        for line in text.splitlines()[:6]:
            w = line.split()
            if 2 <= len(w) <= 4 and all(re.fullmatch(r"[A-Za-z.'-]+", x) for x in w) and not HEADING_RE.match(line):
                name = line.strip()
                break
    name = name or (re.sub(r"[._\d]+", " ", email.split("@")[0]).title().strip() if email else
                    re.sub(r"[_\-.]+", " ", filename.rsplit(".", 1)[0]).title())

    exp_text = sec.get("experience") or "\n".join(l for l in text.splitlines()
                                                 if RANGE_RE.search(l) and not education_levels(l))
    jobs = parse_jobs(exp_text)
    stated = re.search(r"(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)\b[^.\n]{0,40}experience", text, re.I)
    if jobs:
        total_years = weighted_years(jobs)
    elif stated:
        total_years = float(stated.group(1))
        warnings.append("No dated jobs found; experience taken from the stated 'N years' claim.")
    else:
        total_years = 0.0
        warnings.append("No dated work history or stated experience found.")
    if not email:
        warnings.append("No email address found.")
    if "skills" not in sec and "experience" not in sec:
        warnings.append("No Skills/Experience headings detected; layout may be non-standard.")

    edu = parse_education(sec.get("education", "") or "")
    if not edu:
        edu = parse_education(text)
    level = max((e["level"] for e in edu), default=0)

    listed = extract_skills(sec.get("skills", ""))
    in_projects = extract_skills(sec.get("projects", ""))
    in_summary = extract_skills(sec.get("summary", ""))
    all_skills = extract_skills(text)
    skill_index = {}
    for s in all_skills:
        js = [j for j in jobs if s in j["skills"]]
        skill_index[s] = {"listed": s in listed or s in in_summary, "projects": s in in_projects,
                          "jobs": [jobs.index(j) for j in js],
                          "months": merged_months([(j["start_idx"], j["end_idx"]) for j in js]),
                          "last_end": max((j["end_idx"] for j in js), default=None)}

    return {
        "filename": filename, "name": name, "email": email, "phone": phone,
        "current_title": jobs[0]["title"] if jobs else None,
        "total_experience_years": total_years, "education_level": level, "education": edu,
        "summary": sec.get("summary", "")[:400], "skills": sorted(all_skills), "skill_index": skill_index,
        "jobs": jobs, "text": text, "sections": {k: v for k, v in sec.items() if k != "header"},
        "warnings": warnings,
        "parse_quality": "high" if not warnings else "medium" if len(warnings) == 1 else "low",
    }
