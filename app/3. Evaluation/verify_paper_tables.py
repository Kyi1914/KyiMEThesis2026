"""
Reproduce every number in Tables 1-3 and Section 5.1 of the IJCKG 2026 paper
from the result files in this repository (no API calls, no Neo4j needed).

Run from anywhere:
    python "app/3. Evaluation/verify_paper_tables.py"

Inputs (all under docs/data/):
    pdpa_qa_dataset.xlsx                                   benchmark (question_type, scope, gold sections)
    phase3 - result - 3.1 vRAG_evaluationResult.xlsx       RAGAS, V-RAG, 3 judge runs
    phase3 - result - 3.2 graphRAG_evaluationResult_20260715_130836.xlsx   RAGAS, KG-RAG, 3 judge runs
    phase_4_Comparative_Analysis_grag_vrag_v2.0.xlsx       retrieval path, latency, per-question citation scores

Citation convention used by the paper: PDPA-032 has no gold sections and is
excluded from citation scoring (34 questions). KG-RAG precision is undefined
(not zero) when KG-RAG cites nothing.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "docs" / "data"
DATASET = DATA / "pdpa_qa_dataset.xlsx"
VRAG_RAGAS = DATA / "phase3 - result - 3.1 vRAG_evaluationResult.xlsx"
KGRAG_RAGAS = DATA / "phase3 - result - 3.2 graphRAG_evaluationResult_20260715_130836.xlsx"
PHASE4 = DATA / "phase_4_Comparative_Analysis_grag_vrag_v2.0.xlsx"

METRICS = ["Context Precision", "Context Recall", "Faithfulness",
           "Noise Sensitivity", "Answer Accuracy", "Response Relevancy"]


def ragas_runs(path):
    x = pd.ExcelFile(path)
    return [x.parse(f"4omini_run{i}") for i in (1, 2, 3)]


def table1_ragas(runs):
    run_means = pd.DataFrame([r[METRICS].mean() for r in runs])
    return run_means.mean(), run_means.std()  # sample SD across the 3 runs


def load():
    ds = pd.read_excel(DATASET, "Dataset")
    vr, kr = ragas_runs(VRAG_RAGAS), ragas_runs(KGRAG_RAGAS)
    path = pd.read_excel(PHASE4, "data")
    lat = pd.read_excel(PHASE4, "latency comparison")
    cv = pd.read_excel(PHASE4, "citation recall - vrag")
    cg = pd.read_excel(PHASE4, "citation recall - grag")
    for t in (path, lat, cv, cg):
        assert (t["id"].values == ds["id"].values).all(), "row order mismatch"
    df = pd.DataFrame({
        "id": ds["id"], "qtype": ds["question_type"], "scope": ds["primary_scope"],
        "has_gold": ds["pdpa_sections"].notna(),
        "path": path["kgrag_mode"],
        "v_acc": pd.concat([r["Answer Accuracy"] for r in vr], axis=1).mean(axis=1),
        "k_acc": pd.concat([r["Answer Accuracy"] for r in kr], axis=1).mean(axis=1),
        "v_rec": cv["section_recall"], "v_prec": cv["section_precision"],
        "k_rec": cg["citation_recall"], "k_prec": cg["citation_precision"],
        "v_lat": lat["vrag_latency_sec"], "k_lat": lat["grag_latency_sec"],
    })
    return df, vr, kr


def main():
    df, vr, kr = load()
    sc = df[df.has_gold]  # 34 citation-scored questions

    print("=" * 70, "\nTABLE 1  main results")
    vm, vs = table1_ragas(vr)
    km, ks = table1_ragas(kr)
    for m in METRICS:
        print(f"  {m:20s} V-RAG {vm[m]:.3f} ± {vs[m]:.3f}   KG-RAG {km[m]:.3f} ± {ks[m]:.3f}")
    w = wilcoxon(df.v_acc, df.k_acc)
    ties = int((np.isclose(df.v_acc, df.k_acc)).sum())
    print(f"  Answer Accuracy Wilcoxon (n=35): W={w.statistic:.1f}, p={w.pvalue:.3f}, ties={ties}")
    print(f"  Citation recall    (n={len(sc)}): V-RAG {sc.v_rec.mean():.3f}  KG-RAG {sc.k_rec.mean():.3f}")
    w = wilcoxon(sc.v_rec, sc.k_rec)
    print(f"     Wilcoxon: W={w.statistic:.1f}, p={w.pvalue:.3f}")
    print(f"  Citation precision V-RAG over 34 = {sc.v_prec.mean():.3f}"
          f"   (over all 35 incl. PDPA-032 = {df.v_prec.mean():.3f})")
    print(f"  Citation precision KG-RAG (defined on {sc.k_prec.notna().sum()}) = {sc.k_prec.mean():.3f}")
    both = sc.dropna(subset=["v_prec", "k_prec"])
    w = wilcoxon(both.v_prec, both.k_prec)
    w2 = wilcoxon(both.v_prec.round(2), both.k_prec.round(2))
    print(f"     Wilcoxon (n={len(both)}, exact values):        W={w.statistic:.1f}, p={w.pvalue:.4f}")
    print(f"     Wilcoxon (n={len(both)}, values rounded to 2dp): W={w2.statistic:.1f}, p={w2.pvalue:.4f}")
    print(f"  KG-RAG cited nothing on {sc.k_prec.isna().sum()} of {len(sc)} scored questions")
    print(f"  Median latency (s): V-RAG {df.v_lat.median():.2f}  KG-RAG {df.k_lat.median():.2f}")

    print("=" * 70, "\nTABLE 2  by KG-RAG retrieval path")
    for p, g in df.groupby("path", sort=False):
        gs = g[g.has_gold]
        print(f"  {p:16s} n={len(g):2d}  acc V {g.v_acc.mean():.3f} K {g.k_acc.mean():.3f} | "
              f"prec V {gs.v_prec.mean():.3f} K {gs.k_prec.mean():.3f} | "
              f"rec V {gs.v_rec.mean():.3f} K {gs.k_rec.mean():.3f}")
    gain = df.k_acc - df.v_acc
    fb = df.path == "vector_fallback"
    print(f"  graph path usable on {(~fb).sum()}/35 = {(~fb).mean():.1%}; "
          f"of 34 in-PDPA = {(~fb & (df.scope != 'Out of PDPA scope')).sum() / 34:.1%}")
    print(f"  share of total accuracy gain from fallback questions: {gain[fb].sum() / gain.sum():.1%}")

    print("=" * 70, "\nTABLE 3  by question type (citation over questions with gold sections)")
    for qt, g in df.groupby("qtype"):
        gs = g[g.has_gold]
        print(f"  {qt:12s} n={len(g):2d}  prec V {gs.v_prec.mean():.3f} K {gs.k_prec.mean():.3f} | "
              f"rec V {gs.v_rec.mean():.3f} K {gs.k_rec.mean():.3f} | "
              f"lat ratio {g.k_lat.median() / g.v_lat.median():.1f}x")


if __name__ == "__main__":
    main()
