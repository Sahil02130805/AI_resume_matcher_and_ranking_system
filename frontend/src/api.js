async function call(url, opts) {
  const r = await fetch(url, opts);
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(typeof j.detail === "string" ? j.detail : j.detail?.message || `Request failed (${r.status})`);
  return j;
}

function jdForm(jdText, jdFile) {
  const f = new FormData();
  f.append("jd_text", jdText || "");
  if (jdFile) f.append("jd_file", jdFile);
  return f;
}

export const parseJd = (text, file) => call("/api/jd/parse", { method: "POST", body: jdForm(text, file) });
export const getSampleJd = () => call("/api/sample");
export const analyzeSample = () => call("/api/analyze-sample", { method: "POST" });
export const analyze = (text, jdFile, resumes) => {
  const f = jdForm(text, jdFile);
  resumes.forEach((r) => f.append("resumes", r));
  return call("/api/analyze", { method: "POST", body: f });
};
