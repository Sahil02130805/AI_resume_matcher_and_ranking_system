"""Job-description analysis.

Produces a list of weighted *requirements* (not just a skill bag):
  * required vs preferred (by section headings and cue words: "nice to have", "a plus" ...)
  * skills named in the job title are core (weight 3.0)
  * "X or Y" alternatives become one requirement satisfied by either skill
  * per-skill minimum years ("3+ years of Python") and general minimum years ("4-6 years of experience")
  * minimum education level
"""
import re
from .nlp import skill_spans
from .parser import education_levels, LEVEL_NAMES

PREF_RE = re.compile(r"preferred|nice[- ]to[- ]have|good to have|bonus|a plus|desirable|optional|advantage|nice to", re.I)
REQ_HEAD_RE = re.compile(r"requirement|qualification|must[- ]have|required|responsibilit|what you|skills|about you|you will", re.I)
YEARS_RE = re.compile(r"(\d+)\s*\+?\s*(?:(?:-|–|to)\s*(\d+)\s*\+?)?\s*(?:years?|yrs?)", re.I)
OR_SEP_RE = re.compile(r"^\s*(?:,\s*)?(?:or|/)\s+(?:an?\s+|other\s+)?$", re.I)
W_TITLE, W_REQ, W_PREF = 3.0, 1.0, 0.5


def _groups(spans, text):
    """Merge neighbouring skills joined by 'or' into alternative groups -> [[skills], ...]."""
    groups = []
    for skill, s, e in spans:
        if groups and OR_SEP_RE.match(text[groups[-1]["end"]:s]) and "/" not in text[groups[-1]["end"]:s]:
            groups[-1]["members"].append(skill)
            groups[-1]["end"] = e
        else:
            groups.append({"members": [skill], "end": e, "start": s})
    return groups


def analyze_jd(text: str) -> dict:
    lines = [l.strip(" \t•-*·▪●◦") for l in text.splitlines() if l.strip()]
    title = next((l for l in lines if len(l) < 90), "Job Description")
    reqs, seen = [], {}

    def add(members, kind, weight, min_years=None):
        key = tuple(sorted(members))
        if key in seen:                       # same requirement twice: keep the strongest
            r = seen[key]
            if weight > r["weight"]:
                r.update(weight=weight, kind=kind)
            r["min_years"] = r["min_years"] or min_years
            return
        r = {"id": f"r{len(reqs)+1}", "label": " / ".join(members), "members": list(members),
             "kind": kind, "weight": weight, "min_years": min_years}
        seen[key] = r
        reqs.append(r)

    for g in _groups(skill_spans(title), title):
        add(g["members"], "required", W_TITLE)

    mode, general_years, req_lines = "required", None, []
    for l in lines:
        spans = skill_spans(l)
        is_heading = (len(l) < 60 and (l.endswith(":") or l.isupper() or (l.istitle() and "." not in l))
                      and (not spans or bool(PREF_RE.search(l) or REQ_HEAD_RE.search(l))))
        if is_heading and PREF_RE.search(l):
            mode = "preferred"
        elif is_heading and REQ_HEAD_RE.search(l):
            mode = "required"
        is_pref = mode == "preferred" or bool(PREF_RE.search(l))
        # years: attach to a skill only if a skill follows the number closely, else it is general experience
        for ym in YEARS_RE.finditer(l):
            if not re.search(r"experience|exp\b|working|hands", l, re.I) and not spans:
                continue
            nxt = [s for s in spans if 0 <= s[1] - ym.end() <= 60]
            if nxt:
                grp = next(g for g in _groups(spans, l) if nxt[0][0] in g["members"])
                add(grp["members"], "preferred" if is_pref else "required", W_PREF if is_pref else W_REQ, int(ym.group(1)))
            elif general_years is None and re.search(r"experience|exp\b", l, re.I):
                general_years = (float(ym.group(1)), float(ym.group(2)) if ym.group(2) else None)
        if not is_heading:
            for g in _groups(spans, l):
                add(g["members"], "preferred" if is_pref else "required", W_PREF if is_pref else W_REQ)
            if len(l) > 25:
                req_lines.append(l)

    levels = education_levels(text)
    lvl = min(levels) if levels else 0
    return {
        "title": title,
        "required_skills": [r["label"] for r in reqs if r["kind"] == "required"],
        "preferred_skills": [r["label"] for r in reqs if r["kind"] == "preferred"],
        "skill_requirements": reqs,
        "min_experience_years": general_years[0] if general_years else None,
        "max_experience_years": general_years[1] if general_years else None,
        "education_level": lvl, "education_label": LEVEL_NAMES[lvl],
        "requirement_lines": req_lines[:40], "text": text,
    }
