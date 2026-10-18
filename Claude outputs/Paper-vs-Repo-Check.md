# Paper-70 vs. KyiMEThesis2026: verification report

Checked on 19 Oct 2026. Every number was recomputed from the repository files
with `app/3. Evaluation/verify_paper_tables.py`.

## Summary

Most of the paper reproduces exactly from `docs/data/`: all six RAGAS metrics
(mean ± SD), Answer Accuracy and its test, citation recall and its test, the
29/6 retrieval-path split, the 82.9 % / 85.3 % / 41 % figures, latency, and
nearly all of Tables 2–3. The KG node and edge totals also reproduce.

These need action:

| # | Severity | Issue |
|---|---|---|
| A | **High: disclose** | The KG-RAG answers come from **two runs merged together** |
| B | **High: paper ≠ code** | The fallback criterion in §4 is not what the code does |
| C | Medium: paper fix | V-RAG citation precision 0.333 is averaged over 35 questions, not 34 → should be **0.343** |
| D | Medium: paper fix | The citation-precision Wilcoxon test used 2-decimal rounded values; exact data give **W = 10.0, p = 0.003** |
| E | Medium: check | Ontology counts do not match `pdpav6.ttl` (77 individuals vs 80; 1,184 triples vs 1,194) |
| F | Medium: check | "103 DEFINED_IN and CITED_IN edges": the build script yields 81 |
| G | Low | Small wording and rounding issues (listed below) |
| H | Repo | Paths, duplicates and uncommitted local changes |

---

## A. KG-RAG result file is a composite of two runs (must disclose)

The evaluated KG-RAG answers (`docs/data/phase 3 - graphRAG_eval_ready.xlsx`)
match `p2 - result - graphRAG_results_prompt4_27062026_manual.xlsx`, which is:

- the **27 Jun** run (`graph_rag_method1_results_prompt4_20260627_181234.xlsx`) for 33 questions, plus
- **PDPA-011 and PDPA-034** copied from the **26 Jun** run (`…20260626_120113.xlsx`).

| | 27 Jun run alone | Reported (composite) |
|---|---|---|
| PDPA-011 path | graph | **vector_fallback** |
| PDPA-034 path | vector_fallback | **graph** |
| Median KG-RAG latency | 4.15 s | 4.35 s |

The paper's Data Availability section says all figures come from "a single
designated result file". The file is single, but the run is not. I disclosed
this in the README with a «CONFIRM» placeholder for the reason. Consider adding
one sentence to the paper as well. PDPA-011 is one of the six fallback
questions that drive the 41 % finding, so a reviewer would want to know.

## B. Fallback criterion: paper vs. code

The paper (§4) says a result is usable only if (1) it ran without error,
(2) it is non-empty **after removing embedding vectors and duplicate rows**,
and (3) **at least one row carries statutory text or a resolvable in-scope section**.

The code (`has_useful_graph_result`, KG-RAG notebook cell 19) checks only
that **at least one row has any non-null value**. It does not remove
embeddings or duplicates, and it does not check for text or sections.

Fix: either rewrite the paper sentence to match the code ("…a non-empty
result with at least one non-null value…"), or change the code and re-run.
The re-run would change results. The README currently describes the code's behaviour.

The "fixed refusal" claim is fine: it is implemented through the prompt
(`I don't know based on the retrieved context.`).

## C. V-RAG citation precision: 0.333 should be 0.343

The paper says citation scoring covers 34 questions (PDPA-032 has no gold
sections). V-RAG's 0.333 includes PDPA-032 scored as 0 (35 questions). Over
the 34 scored questions it is **0.343**. KG-RAG's 0.661 and both recall
values (0.510) are already over 34.

The same inconsistency appears in **Table 3, Explanatory, V-RAG precision**:
0.250 (includes PDPA-032) → **0.313** over the 4 scored questions. The recall
in that row (0.375) already excludes PDPA-032.

Also update the hard-coded 0.333 in `fig_cross_system.py` and
`citation comparison.py`, and in the chapter-4 chart values.

## D. Citation-precision Wilcoxon

| Input | n | W | p |
|---|---|---|---|
| Thesis Appendix F values (rounded to 2 dp) — what the paper reports | 28 | 14.0 | 0.005 |
| Exact per-question values in `phase_4_…v2.0.xlsx` | 28 | **10.0** | **0.003** |

The conclusion does not change, but the reported statistic should come from
the designated file. Suggest Table 1: `W = 10.0, p = 0.003`. The Answer
Accuracy test (W = 26.0, p = 0.028, 19 ties) and the citation-recall test
(W = 38.5, p = 0.97) reproduce exactly.

## E. Ontology counts (rdflib on the repo's `pdpav6.ttl`)

| | Paper | Repo file |
|---|---|---|
| Classes | 85 | 85 ✓ |
| Object properties | 35 | 35 ✓ |
| Named individuals | 80 | **77** |
| Triples | 1,194 | **1,184** |

Either the paper's figures come from a later ontology version than the one
committed, or they come from Protégé's metrics view (axiom counts), which
differs from an RDF triple count. Open the committed `pdpav6.ttl` in Protégé
and check *Ontology metrics*. Then either commit the correct file or change
the paper to the repo's numbers. If the figures are Protégé axioms, call them
"axioms", not "triples".

## F. Knowledge-graph counts

Simulating `build_pdpa_graph.py` on `pdpav6.ttl` gives:

- **150 nodes** ✓, 8 labels ✓, 9 relationship types ✓, **265 relationships** ✓
- 1 LegalAct, 3 Chapters, 3 Parts, 37 Sections, 81 Concepts ✓, 25 individuals (6 + 6 + 13) ✓
- CITED_IN 51 + DEFINED_IN 30 = **81**, not 103 (GROUNDED_IN adds 25 more)

To confirm against your live Neo4j database, run:

```cypher
MATCH ()-[r]->() RETURN type(r) AS rel, count(*) ORDER BY rel;
```

If it shows 81, change "103 DEFINED_IN and CITED_IN edges" in §3.2.
(If the paper meant to include GROUNDED_IN, the total would be 106.)

## G. Minor wording and rounding

- §4: "each of the 49 chunks corresponds to one section" is not exact. The
  notebook output shows 49 chunks across 30 section tags (1–29 plus a stray
  "34"), because long sections are split into sub-chunks. Suggest "49
  section-tagged chunks, long sections split into sub-chunks".
- Table 2: graph-routed V-RAG precision is 0.38505, which rounds to **0.385**, not 0.384.
- §5.1 uses "34 in-scope questions" to mean in-PDPA, but §3.3 uses
  "in scope" for the 29 Section 1–29 questions. Use "in-PDPA" in §5.1.
- Table 2 caption: KG-RAG cited nothing on **all six** fallback questions
  (five non-answers with no citation, plus the refusal on PDPA-032). "Five of
  those six" is defensible only if PDPA-032 is excluded as unscored. Make the
  caption say so.
- §4 says both systems share nomic-embed-text. That is true for retrieval,
  but the build script also writes an mpnet `embedding` property that KG-RAG
  does not use. The README now explains this, and no paper change is needed.

## H. Repository issues

1. **Uncommitted local changes.** The GitHub index still has
   `vectorRag_29q_…ipynb` and `app/3. Evaluation/archived/`, but on disk they
   are `vectorRag_35q_…ipynb` and `archived - not used/`. New figures in
   `app/4. additional - figures/figures/` are not committed. Commit and push,
   since the paper links to the GitHub version.
2. **Notebook paths do not resolve** inside the repo (`../data/…`). The README
   has a table of fixes.
3. **`3.1 modelsEvaluation-vrag` saves its output as `graphRAG_evaluationResult.xlsx`**
   (copy-paste from the KG-RAG notebook). Rename this in the notebook.
4. **The Wilcoxon scripts** `extra-statisticalt.py` and
   `extra-statisticalTest-WilcoxonTest.py` are identical, and they point to
   files that don't exist. Delete one and fix the paths.
5. **The committed FAISS index** `app/2.1 VectorRAG/faiss_ollama_pdpa/` dates
   from June 2025, but the notebook writes to `../data/faiss_pdpa_vrag`. The
   committed index is not the one used for the paper.
6. **`.pyc` files are tracked.** The new `.gitignore` excludes them; also run
   `git rm -r --cached "app/2.2 KGRAG/promptTemplate/__pycache__"` once.
7. **Duplicates** (identical content): three copies of each eval-ready file,
   two copies of the benchmark, and two copies of the Sections 1–29 PDF.
   `README-for-github.md` is an outdated template and can be deleted.
8. **The build-script readme** (`2.2.1 …/readme.md`) contains your local Neo4j
   password (`11111111`). Replace it with `YOUR_PASSWORD`.
9. **Missing:** `LICENSE` file, pinned `requirements.txt`, the exact
   gpt-4o-mini snapshot, and the Neo4j and RAGAS versions.

### Suggested cleanup (do in File Explorer, then commit)

| Action | Path |
|---|---|
| Delete | `README-for-github.md` |
| Delete | `app/3. Evaluation/extra-statisticalt.py` (duplicate) |
| Delete | `docs/Phase 2 - SystemImplementation - Vector RAG/vectorRAG_eval_ready.xlsx`, `graphRAG_eval_ready.xlsx` |
| Delete | `docs/Phase 3 - Evaluation/data/` (both files are copies of `docs/data/`) |
| Delete | `docs/data/phase 4 - pdpa_qa_dataset_for_analysis.xlsx` (copy of the benchmark) |
| Delete | `docs/diagram/fig_category_breakdown_1.png` (same size as `fig_category_breakdown.png`) |
| Move | `docs/Phase 2 - …/p2 - result - graphRAG_results_prompt4_27062026_manual.xlsx` → `docs/data/` (it is a paper input, but it sits in a folder named "Vector RAG") |
| Rename | `app/4. additional - figures/import matplotlib.pyplot as plt.pyplot as plt.py` → `fig_ragas_comparison.py` |
| Rename | `app/4. additional - figures/citation comparison.py` → `fig_citation_comparison.py` |

Tell me when these are done and I'll update the README paths to match.
