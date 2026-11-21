import { useRef, useState } from "react";
import { analyze, analyzeSample, getSampleJd, parseJd } from "./api";
import JobDescription from "./components/JobDescription";
import ResumeUpload from "./components/ResumeUpload";
import RankingTable from "./components/RankingTable";
import CandidateDetail from "./components/CandidateDetail";

export default function App() {
  const [jdText, setJdText] = useState("");
  const [jdFile, setJdFile] = useState(null);
  const [jd, setJd] = useState(null);
  const [files, setFiles] = useState([]);
  const [data, setData] = useState(null);
  const [selected, setSelected] = useState(null);
  const [busy, setBusy] = useState(false);
  const detailRef = useRef();

  const run = async (fn) => {
    setBusy(true);
    try {
      const d = await fn();
      setData(d); setJd(d.jd); setSelected(null);
    } catch (e) { alert(e.message); }
    setBusy(false);
  };
  const runUpload = () => run(async () => {
    if (!files.length) throw new Error("Select resumes first");
    return analyze(jdText, jdFile, files);
  });
  const runSample = () => run(async () => {
    const { jd_text } = await getSampleJd();
    setJdText(jd_text); setJdFile(null);
    return analyzeSample();
  });
  const select = (id) => { setSelected(id); setTimeout(() => detailRef.current?.scrollIntoView({ behavior: "smooth" }), 50); };
  const cand = data?.candidates.find((c) => c.id === selected);

  return (
    <>
      <header><h1>AI Resume Matching &amp; Candidate Ranking</h1></header>
      <main>
        <div className="grid2">
          <JobDescription text={jdText} setText={setJdText} file={jdFile} setFile={setJdFile} jd={jd} setJd={setJd} />
          <ResumeUpload files={files} setFiles={setFiles} onRun={runUpload} onRunSample={runSample} busy={busy} />
        </div>
        {data && <RankingTable data={data} selected={selected} onSelect={select} />}
        <div ref={detailRef}>{cand && <CandidateDetail c={cand} />}</div>
      </main>
    </>
  );
}
