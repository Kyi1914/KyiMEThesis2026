# A Citation-Grounded PDPA Ontology and QA Benchmark for Thai Legal Question Answering

Resources, code and evaluation outputs for the KGE-LLM 2026 paper
*A Citation-Grounded PDPA Ontology and QA Benchmark for Thai Legal Question
Answering, with an Exploratory Graph-First RAG Study*, published in the
IJCKG 2026 Posters, Demos and Workshops proceedings (CEUR-WS).

Kyi Thin Nu and Chutiporn Anutariya (Asian Institute of Technology);
Pattama Krataithong (NECTEC).

This repository also holds the Master's thesis the paper derives from.

<!-- ============================================================
     PLACEHOLDERS: every PATH/TO/... and every «CONFIRM» below is
     something only you can fill in. Delete this comment when done.
     ============================================================ -->

## What this repository contains

Three released resources, plus the two systems evaluated on them:

| Resource | Path | Description |
|---|---|---|
| PDPA ontology | `PATH/TO/pdpav6.ttl` | OWL 2 DL, Turtle. 85 classes, 35 object properties, 80 named individuals, 1,194 triples, covering Sections 1–29 |
| Knowledge graph build script | `PATH/TO/build_graph.py` | Materialises the ontology plus statutory text into Neo4j: 150 nodes, 265 relationships |
| QA benchmark | `docs/data/PATH/TO/benchmark_35.json` | 35 questions with reference answers, gold section citations, theme and question type |

| Code | Path |
|---|---|
| KG-RAG (graph-first hybrid) | `app/PATH/TO/kg_rag.ipynb` |
| V-RAG (section-aware vector baseline) | `app/PATH/TO/v_rag.ipynb` |
| Prompts, verbatim | `PATH/TO/prompts/` |
| RAGAS evaluation harness | `PATH/TO/evaluate_ragas.py` |
| Citation scoring, retrieval-path analysis, significance tests | `PATH/TO/path_analysis.py` |

## Which results the paper reports

**Read this before comparing any number against the paper.**

This repository contains more than one evaluation run. The paper reports
exactly one of them:

- **Authoritative, used for every table in the paper:** `PATH/TO/«FILENAME».xlsx`
- Earlier run, retained for transparency, **not** used in the paper:
  `PATH/TO/«OTHER».xlsx`
- Why they differ: «CONFIRM — e.g. the earlier run predates the
  evaluation-harness parsing fix described in the thesis, so its graph context
  was empty at scoring time»

The two runs disagree on the retrieval path taken for «CONFIRM — which
questions» and on median latency («CONFIRM» s vs «CONFIRM» s).

| Paper table | Script | Input |
|---|---|---|
| Table 1, main results | `PATH/TO/evaluate_ragas.py` | authoritative file |
| Table 2, by retrieval path | `PATH/TO/path_analysis.py` | authoritative file |
| Table 3, by question type | `PATH/TO/path_analysis.py` | authoritative file |

## Reproducing the results

### Prerequisites

| Component | Version |
|---|---|
| Python | «CONFIRM» |
| Neo4j | «CONFIRM» — must be running before step 2 |
| Ollama | serves `nomic-embed-text` (768-d) locally |
| OpenAI API key | `gpt-4o-mini-«CONFIRM-DATE»`, used as both generator and judge |
| FAISS | «CONFIRM» |
| RAGAS | «CONFIRM» |
| rdflib | «CONFIRM» |

```bash
pip install -r requirements.txt    # «CONFIRM this file exists»

export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=...
export OPENAI_API_KEY=...
```

### Steps

```bash
# 1. build the knowledge graph from the ontology and the statutory text
python PATH/TO/build_graph.py

# 2. build the V-RAG FAISS index
python PATH/TO/build_vector_index.py

# 3. run both systems over the 35-question benchmark
#    (notebooks: run all cells in order)
#    app/PATH/TO/kg_rag.ipynb
#    app/PATH/TO/v_rag.ipynb

# 4. RAGAS scoring, three judge runs at temperature 0
python PATH/TO/evaluate_ragas.py --runs 3

# 5. citation scoring, retrieval-path breakdown, significance tests
python PATH/TO/path_analysis.py
```

Step 3 takes roughly «CONFIRM» minutes and incurs OpenAI charges.

### Data paths

The released data lives under `docs/data/`. «CONFIRM — the notebooks
previously referenced `../data/`; make sure every path now resolves against
`docs/data/`, or state here what the correct working directory is.»

### Embedding index used by the dense fallback

KG-RAG's fallback searches a vector index built over the `Concept` nodes.
«CONFIRM — name the index and how it is built, since the reported fallback
behaviour depends on it.»

### Fallback criterion

The paper describes a Cypher result as usable when all three hold:

1. the query executed without a syntax or schema error;
2. the result set is non-empty after removing embedding-vector properties and
   de-duplicating rows;
3. at least one row carries non-empty statutory text or a resolvable in-scope
   section — a `Section` node with text, or a `Concept` node with a
   `DEFINED_IN` or `CITED_IN` edge to an in-scope `Section`.

«CONFIRM that this matches the implementation. If the code differs, say so
here and treat the code as authoritative.»

## Known limitations

- The ontology covers Sections 1–29 of the PDPA only.
- The benchmark was authored by a single annotator with no legal-practitioner
  review, so inter-annotator agreement is unmeasured.
- Generated Cypher queries are not evaluated for correctness; only the
  end-to-end rate at which the graph path yields usable context is reported.
- The generator, GPT-4o-mini, was selected using this same 35-question
  benchmark.
- **These are research artefacts, not legal advice**, and are not suitable for
  unsupervised compliance use.

## Licence

Released under CC BY 4.0, matching the CEUR-WS copyright terms of the paper.
See `LICENSE`.

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
