# A Citation-Grounded PDPA Ontology and QA Benchmark for Thai Legal Question Answering

Resources, code and evaluation outputs for the KGE-LLM 2026 paper
*A Citation-Grounded PDPA Ontology and QA Benchmark for Thai Legal Question
Answering, with an Exploratory Graph-First RAG Study*, IJCKG 2026 Posters,
Demos and Workshops (CEUR-WS).

Kyi Thin Nu and Chutiporn Anutariya (Asian Institute of Technology);
Pattama Krataithong (NECTEC).

This repository also holds the Master's thesis work the paper derives from.

> **Not legal advice.** These are research artefacts. Answer accuracy is
> 0.33–0.42; do not use either system for compliance decisions without expert review.

---

## 1. Repository map

```
KyiMEThesis2026/
├── app/
│   ├── 2.1 VectorRAG/                         V-RAG baseline (FAISS + nomic + GPT-4o-mini)
│   ├── 2.2 KGRAG/                             KG-RAG (Cypher-first, dense fallback)
│   │   └── promptTemplate/                    prompt1–4 (paper uses prompt4)
│   ├── 2.2.1 pdpav6.0Onto 2 GraphDB_PythonScript/   ontology + Neo4j build script
│   ├── 3. Evaluation/                         RAGAS harness + statistics
│   └── 4. additional - figures/               figure scripts
├── docs/
│   ├── data/                                  ★ benchmark + every result file the paper uses
│   ├── diagram/                               figures and architecture diagrams
│   ├── Others/                                ontology design deck
│   └── Phase 2 / Phase 3 folders              working copies (see §6)
└── image/ontology.graph
```

## 2. Released resources

| Resource | Path | Paper |
|---|---|---|
| PDPA ontology (OWL 2 DL, Turtle) | `app/2.2.1 pdpav6.0Onto 2 GraphDB_PythonScript/pdpav6.ttl` | §3.1 |
| Knowledge-graph build script | `app/2.2.1 pdpav6.0Onto 2 GraphDB_PythonScript/build_pdpa_graph.py` | §3.2 |
| Build instructions | `app/2.2.1 pdpav6.0Onto 2 GraphDB_PythonScript/readme.md` | §3.2 |
| Statutory text (Sections 1–29, English) | `app/2.2.1 pdpav6.0Onto 2 GraphDB_PythonScript/pdpa_Extract113.pdf` (same file as `docs/data/pdpa_ch1&2.pdf`) | §3.2, §4 |
| Full PDPA (English translation) | `docs/data/pdpa.pdf` | — |
| 35-question benchmark | `docs/data/pdpa_qa_dataset.xlsx`, sheet `Dataset` | §3.3 |

Benchmark columns: `id`, `question`, `groundTruth` (reference answer),
`pdpa_sections` (gold citations), `category`, `question_type`, `primary_scope`
(`Sec 1–29` = 29, `Beyond Ch I–II` = 5, `Out of PDPA scope` = 1).
PDPA-032 has no gold sections, so citation scoring covers 34 questions.

## 3. Code

| Component | Path |
|---|---|
| V-RAG pipeline | `app/2.1 VectorRAG/vectorRag_35q_gpt4omini_prompt_v1.ipynb` |
| V-RAG prompt (verbatim) | `app/2.1 VectorRAG/vector_prompt_v1.py` |
| KG-RAG pipeline | `app/2.2 KGRAG/3. graphRag_35q_hybrid_gpt4omini_prompt4 v2.1.ipynb` |
| KG-RAG prompts (verbatim; paper = `prompt4`) | `app/2.2 KGRAG/promptTemplate/prompt4.py` |
| RAGAS evaluation, V-RAG | `app/3. Evaluation/3.1 modelsEvaluation-vrag_16072026.ipynb` |
| RAGAS evaluation, KG-RAG | `app/3. Evaluation/3.2 modelsEvaluation-grag_16072026.ipynb` |
| **Reproduce Tables 1–3 and §5.1 (no API calls)** | `app/3. Evaluation/verify_paper_tables.py` |
| Answer-accuracy Wilcoxon test (standalone) | `app/3. Evaluation/extra-statisticalTest-WilcoxonTest.py` |
| Figure scripts | `app/4. additional - figures/` |

`app/2.2 KGRAG/2. addEmbedding2KG.ipynb` is an early experiment (OpenAI
`text-embedding-3-small`); it is **not** part of the paper's pipeline.

## 4. Which result files the paper reports

**Read this before comparing any number with the paper.** Every number in
Tables 1–3 and §5.1 is computed from the four files below.
`python "app/3. Evaluation/verify_paper_tables.py"` recomputes all of them.

| File (all in `docs/data/`) | Produced by | Feeds |
|---|---|---|
| `pdpa_qa_dataset.xlsx` | hand-authored | question type, scope, gold sections |
| `phase3 - result - 3.1 vRAG_evaluationResult.xlsx` | `3.1 modelsEvaluation-vrag_16072026.ipynb` | Table 1 RAGAS rows (V-RAG), Answer Accuracy test |
| `phase3 - result - 3.2 graphRAG_evaluationResult_20260715_130836.xlsx` | `3.2 modelsEvaluation-grag_16072026.ipynb` | Table 1 RAGAS rows (KG-RAG), Answer Accuracy test |
| `phase_4_Comparative_Analysis_grag_vrag_v2.0.xlsx` | assembled from the runs below; citation scores recomputed from raw text (sheet `recalc summary`) | retrieval path, latency, citation precision/recall (Tables 1–3, §5.1) |

### Paper element → source

| Paper element | Sheet / column | Script |
|---|---|---|
| Table 1: Context Precision, Context Recall, Faithfulness, Noise Sensitivity, Answer Accuracy, Response Relevancy (mean ± SD of 3 runs) | `4omini_run1..3` and `4omini_summary` in both phase-3 result files | `verify_paper_tables.py` |
| Table 1: Answer Accuracy W = 26.0, p = 0.028 | per-question mean of `Answer Accuracy` over the 3 runs | `verify_paper_tables.py`, `extra-statisticalTest-WilcoxonTest.py` |
| Table 1: citation recall / precision and tests | phase-4 `citation recall - vrag` (`section_recall`, `section_precision`), `citation recall - grag` (`citation_recall`, `citation_precision`) | `verify_paper_tables.py` |
| Table 1: median latency 2.12 s / 4.35 s | phase-4 `latency comparison` | `verify_paper_tables.py` |
| Table 2, §5.1 (29 graph / 6 fallback, 82.9 %, 41 %) | phase-4 `data` → `kgrag_mode` | `verify_paper_tables.py` |
| Table 3 | benchmark `question_type` joined with the phase-4 citation and latency sheets | `verify_paper_tables.py`; figures from `chapter4_type_category_charts.ipynb` |
| Figure: RAGAS bar chart | `docs/diagram/fig_ragas_comparison.png` | `app/4. additional - figures/import matplotlib.pyplot as plt.pyplot as plt.py` |
| Figure: cross-system comparators | `docs/diagram/fig_cross_system.png` | `app/4. additional - figures/fig_cross_system.py` |
| Figures: by type / by category | `docs/diagram/fig_type_breakdown.png`, `fig_category_breakdown.png` | `app/4. additional - figures/chapter4_type_category_charts.ipynb` |
| Figure 1 (ontology top level) | `image/ontology.graph`, `docs/Others/PDPA_Ontology_Design.pptx.pdf` | Protégé |
| Figure 2 (KG-RAG pipeline) | `docs/diagram/diagram-export-*.png`, `offline_kg_construction.png` | draw.io |

### System answers behind the evaluation

| System | Raw run | Evaluation input (RAGAS) |
|---|---|---|
| V-RAG | `app/2.1 VectorRAG/vector_rag_results_vector_prompt_v1_20260630_151417.xlsx` (run of 30 Jun 2026) | `docs/data/phase 3 - vectorRAG_eval_ready.xlsx` (identical answers and contexts) |
| KG-RAG | `docs/Phase 2 - SystemImplementation - Vector RAG/p2 - result - graphRAG_results_prompt4_27062026_manual.xlsx` | `docs/data/phase 3 - graphRAG_eval_ready.xlsx` (identical answers and modes) |

**The KG-RAG file is a composite of two runs of the same pipeline and prompt
(`prompt4`):**

- 33 questions come from the run of 27 Jun 2026
  (`app/2.2 KGRAG/graph_rag_method1_results_prompt4_20260627_181234.xlsx`);
- **PDPA-011 and PDPA-034** come from the run of 26 Jun 2026
  (`app/2.2 KGRAG/graph_rag_method1_results_prompt4_20260626_120113.xlsx`).
  «CONFIRM — state why these two rows were replaced.»

The runs differ in retrieval path for those two questions (27 Jun: PDPA-011
graph, PDPA-034 fallback; reported: PDPA-011 fallback, PDPA-034 graph) and in
median latency (27 Jun alone: 4.15 s; reported composite: 4.35 s). The 26 Jun
run alone has a 28/7 graph/fallback split. Both raw runs are kept for transparency.

## 5. Reproducing the results

### Environment

| Component | Version |
|---|---|
| Python | 3.11.9 (pipelines and evaluation); build script needs ≥ 3.10 |
| Neo4j | 5.11 or later (vector indexes) — «CONFIRM exact version» |
| Ollama | serves `nomic-embed-text` (768-d) |
| OpenAI | `gpt-4o-mini`, temperature 0, generator **and** RAGAS judge — «CONFIRM model snapshot date» |
| RAGAS, LangChain, faiss-cpu, rdflib | see `requirements.txt` — «pin with `pip freeze`» |

Create `.env` files next to the notebooks (never commit them):

```
OPENAI_API_KEY=...
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=...
```

### Steps

1. **Build the knowledge graph** (from `app/2.2.1 pdpav6.0Onto 2 GraphDB_PythonScript/`):

   ```
   python build_pdpa_graph.py --ttl pdpav6.ttl --pdf pdpa_Extract113.pdf --uri bolt://localhost:7687 --user neo4j --password <PASSWORD> --wipe
   ```

   This creates the graph and a `Section`/`Concept` `embedding` property with
   `paraphrase-multilingual-mpnet-base-v2`. **KG-RAG does not use that
   embedding**; see step 3.

2. **V-RAG.** Run `app/2.1 VectorRAG/vectorRag_35q_gpt4omini_prompt_v1.ipynb`.
   Section-aware chunking of `pdpa_ch1&2.pdf` gives 49 chunks covering
   Sections 1–29 (long sections are split into ≤ 1,200-character sub-chunks
   that keep their section tag; the splitter also tags one chunk "Section 34"),
   `k = 4`, cosine FAISS.

3. **KG-RAG.** Run `app/2.2 KGRAG/3. graphRag_35q_hybrid_gpt4omini_prompt4 v2.1.ipynb`.
   Cell 10 builds the dense-fallback index **`concept_nomic_index`** on
   `Concept.nomic_embedding` (nomic-embed-text over each concept's text +
   definition, `k = 4`).

4. **RAGAS.** Run `app/3. Evaluation/3.1 …vrag…ipynb` and `3.2 …grag…ipynb`
   (gpt-4o-mini judge, 3 runs, temperature 0).

5. **Tables and tests.** `python "app/3. Evaluation/verify_paper_tables.py"`.

Steps 2–4 call the OpenAI API and incur charges.

### Path fixes needed before re-running

The notebooks were run from a working folder, so their relative paths do not
resolve inside this repository. Set them as follows:

| Notebook | Variable / line | Currently | Point to |
|---|---|---|---|
| V-RAG | `PDF_PATH` | `../data/pdpa_ch1&2.pdf` | `../../docs/data/pdpa_ch1&2.pdf` |
| V-RAG | `QUESTION_SOURCE` | `../data/pdpa_qa_dataset.xlsx` | `../../docs/data/pdpa_qa_dataset.xlsx` |
| V-RAG | `FAISS_DIR` | `../data/faiss_pdpa_vrag` | a fresh folder (the committed `faiss_ollama_pdpa/` index predates the paper runs) |
| KG-RAG | `QUESTION_SOURCE` | `../data/pdpa_qa_dataset.xlsx` | `../../docs/data/pdpa_qa_dataset.xlsx` |
| 3.1 / 3.2 RAGAS | `pd.read_excel(...)` | `vectorRAG_eval_ready.xlsx` / `graphRAG_eval_ready.xlsx` | `../../docs/data/phase 3 - …_eval_ready.xlsx` |
| Wilcoxon script | `VRAG_FILE`, `KGRAG_FILE` | `3_1_vRAG_…`, `graphRAG_…` | the two phase-3 result files in `docs/data/` |

### Fallback criterion (as implemented)

The code (`has_useful_graph_result`, KG-RAG notebook cell 19) treats a Cypher
result as usable when the query ran without error and **at least one returned
row has a non-empty value**. If not, it uses the dense fallback; if the
retrieved context is empty, the answer prompt returns the fixed refusal
`I don't know based on the retrieved context.` The code is authoritative.

## 6. Other files (not used for the paper's numbers)

| Path | What it is |
|---|---|
| `docs/Phase 2 - …/vectorRAG_eval_ready.xlsx`, `graphRAG_eval_ready.xlsx`; `docs/Phase 3 - Evaluation/data/*` | identical copies of the eval-ready files in `docs/data/` |
| `docs/data/phase 4 - pdpa_qa_dataset_for_analysis.xlsx` | identical copy of `pdpa_qa_dataset.xlsx` |
| `docs/Phase 3 - Evaluation/results/Manual Eval -*.xlsx` | early manual context precision/recall (pre-RAGAS) |
| `app/3. Evaluation/archived - not used/` | superseded evaluation notebooks |
| `app/2.2 KGRAG/promptTemplate/prompt1–3.py` | earlier prompt iterations |
| `app/2.2.1 …/rename_ontology.py`, `aboutProject.md`, `skillAssessment.md` | development notes |

## 7. Known limitations

- The ontology covers PDPA Sections 1–29 only.
- The benchmark was authored by one annotator, with no legal-practitioner
  review; inter-annotator agreement is unmeasured.
- Generated Cypher is not evaluated for correctness.
- GPT-4o-mini is both generator and judge, and was selected on this benchmark.
- Evaluation is on the English translation, not the Thai text.

## Licence

CC BY 4.0, matching the paper's CEUR-WS terms. «Add a `LICENSE` file.»

## Citation

```bibtex
@inproceedings{nu2026pdpa,
  title     = {A Citation-Grounded {PDPA} Ontology and {QA} Benchmark for Thai
               Legal Question Answering, with an Exploratory Graph-First {RAG} Study},
  author    = {Nu, Kyi Thin and Anutariya, Chutiporn and Krataithong, Pattama},
  booktitle = {Proceedings of the IJCKG 2026 Posters, Demos and Workshops},
  series    = {CEUR Workshop Proceedings},
  year      = {2026},
  note      = {International Workshop on Knowledge Graph Engineering in the Era
               of Large Language Models (KGE-LLM 2026)}
}
```
