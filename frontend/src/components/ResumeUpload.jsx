import { useRef, useState } from "react";

export default function ResumeUpload({ files, setFiles, onRun, onRunSample, busy }) {
  const [over, setOver] = useState(false);
  const input = useRef();
  const accept = (list) => setFiles([...list].filter((f) => /\.(pdf|docx)$/i.test(f.name)));

  return (
    <section className="card">
      <h2>2 · Resumes (PDF / DOCX, batch)</h2>
      <div
        className={`drop ${over ? "over" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setOver(true); }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => { e.preventDefault(); setOver(false); accept(e.dataTransfer.files); }}
        onClick={() => input.current.click()}
      >
        Drag &amp; drop resumes here or click to browse
        <input ref={input} type="file" multiple accept=".pdf,.docx" hidden onChange={(e) => accept(e.target.files)} />
      </div>
      <div className="mut small">
        {files.length ? `${files.length} file(s): ${files.map((f) => f.name).join(", ")}` : "No files selected"}
      </div>
      <div className="row">
        <button onClick={onRun} disabled={busy}>Match &amp; rank</button>
        <button className="sec" onClick={onRunSample} disabled={busy}>Run with 14 sample resumes</button>
        {busy && <span className="mut">Analysing…</span>}
      </div>
    </section>
  );
}
