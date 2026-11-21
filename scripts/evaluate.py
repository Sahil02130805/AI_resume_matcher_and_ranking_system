"""Rank the sample resumes and compare with human gold grades (NDCG@5, pairwise order accuracy)."""
import json, math, os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.jd import analyze_jd
from app.parser import parse_resume
from app.matcher import rank


def evaluate(verbose=True):
    gold = {k: v for k, v in json.loads((ROOT / "sample_data/gold_labels.json").read_text()).items() if not k.startswith("_")}
    jd = analyze_jd((ROOT / "sample_data/job_description.txt").read_text())
    res = rank(jd, [parse_resume(p.name, p.read_bytes()) for p in sorted((ROOT / "sample_data/resumes").iterdir())])
    order = [r["name"] for r in res]
    gains = [gold[n] for n in order]
    dcg = lambda g: sum((2 ** x - 1) / math.log2(i + 2) for i, x in enumerate(g[:5]))
    ndcg = dcg(gains) / dcg(sorted(gains, reverse=True))
    pairs = [(a, b) for i, a in enumerate(order) for b in order[i + 1:] if gold[a] != gold[b]]
    acc = sum(gold[a] > gold[b] for a, b in pairs) / len(pairs)
    if verbose:
        for r in res:
            print(f'{r["rank"]:>2} {r["name"]:<16} score={r["score"]:>5}  gold={gold[r["name"]]}  backend={r["similarity_backend"]}')
        print(f"\nNDCG@5 = {ndcg:.3f}   pairwise order accuracy = {acc:.3f} ({len(pairs)} pairs)")
    return ndcg, acc, res


if __name__ == "__main__":
    evaluate()
