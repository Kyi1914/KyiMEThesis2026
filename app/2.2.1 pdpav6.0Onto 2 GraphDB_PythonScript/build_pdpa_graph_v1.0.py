#!/usr/bin/env python3
"""
build_pdpa_graph.py
===================

Builds a clean, retrieval-optimized Neo4j knowledge graph for a Thai PDPA
Graph-RAG system from TWO sources of truth:

  1. pdpav6.ttl            - the OWL/Turtle ontology (schema classes + individuals)
  2. pdpa_Extract113.pdf   - the PDPA text (Sections 1-29), used to put
                             AUTHORITATIVE section text on :Section nodes so that
                             section-cited retrieval has real text to return.

This bypasses neosemantics deliberately. rdflib reads the ontology, a PDF parser
extracts per-section text, sentence-transformers computes embeddings, and the
official neo4j driver writes the graph + vector indexes. The result is a graph
shaped for retrieval, not for OWL reasoning (no restriction blank nodes, no
TBox/ABox soup, text lives on the nodes you actually cite).

Target model
------------
  (:Chapter)-[:HAS_PART]->(:Part)-[:HAS_SECTION]->(:Section)
  (:Chapter)-[:HAS_SECTION]->(:Section)                 # chapters without parts
  (:LegalAct)-[:HAS_CHAPTER]->(:Chapter)

  (:Concept)-[:DEFINED_IN]->(:Section)                  # primary citation (isDefinedBy)
  (:Concept)-[:CITED_IN]->(:Section)                    # supporting citations (:source)
  (:Concept)-[:SUBCLASS_OF]->(:Concept)
  (:Concept)-[:REQUIRES]->(:Concept)                    # e.g. (HealthData)-[:REQUIRES]->(ExplicitConsent)
  (:Concept)-[:RELATES {predicate, section}]->(:Concept)# controller obligations etc.

  (:LawfulBasis)-[:GROUNDED_IN]->(:Section)             # the 6 bases -> Section 24
  (:Exemption)-[:GROUNDED_IN]->(:Section)               # Section 4 scope exclusions
  (:ConsentException)-[:GROUNDED_IN]->(:Section)        # Section 26 exceptions

Node properties carrying text + embeddings
------------------------------------------
  :Section { number:int, title, chapter, part, text, embedding:[float] }
  :Concept { name, label, definition, text, embedding:[float] }

Usage
-----
  pip install rdflib pdfplumber neo4j sentence-transformers
  python build_pdpa_graph.py \
      --ttl pdpav6.ttl --pdf pdpa_Extract113.pdf \
      --uri bolt://localhost:7687 --user neo4j --password YOUR_PW --wipe

Flags
-----
  --wipe            DETACH DELETE everything in the target DB first (clean rebuild).
  --no-embeddings   Skip the embedding step (fast dry run; vector index still created).
  --database NAME   Target Neo4j database (default: neo4j). Use a SEPARATE db from
                    your n10s import to avoid mixing the two graphs.

Notes
-----
* The PDF supplied is the "unofficial translation" and contains Sections 1-29,
  which matches your modeled scope (Chapters I-II). Sections referenced but out
  of scope (30, 31, ... 73) get :Section stub nodes with no text, exactly so your
  six known out-of-scope questions surface as visible retrieval gaps rather than
  silent failures.
* Re-runs are idempotent: nodes are MERGEd on natural keys (Section.number,
  Concept.name), so you can re-run after editing the .ttl without --wipe.
"""

import argparse
import re
import sys
from collections import defaultdict

from rdflib import Graph, Namespace, URIRef, BNode, Literal
from rdflib.namespace import RDF, RDFS, OWL

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE = "http://www.semanticweb.org/kyith/ontologies/2025/6/untitled-ontology-33/"
NS = Namespace(BASE)
SKOS_DEF = URIRef("http://www.w3.org/2004/02/skos/core#definition")

# Custom annotation/object-property predicates used in the ontology
P_DEFINITION = URIRef(BASE + "definition")
P_SOURCE = URIRef(BASE + "source")

EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
VECTOR_DIM = 768  # dimensionality of the model above

# Classes that are STRUCTURAL schema, not retrievable domain concepts.
# Their *individuals* become the structural spine; the classes themselves are skipped.
STRUCTURAL_CLASSES = {
    "Chapter", "Part", "Section", "LegalResourceSubdivision",
}

# Individual rdf:type -> the clean label + the section it is grounded in (if fixed).
INDIVIDUAL_TYPE_MAP = {
    "LawfulBasis": ("LawfulBasis", 24),
    "Exemption": ("Exemption", 4),
    "ExplicitConsentException": ("ConsentException", 26),
}

SCOPE_MAX_SECTION = 29  # Sections 1-29 are in scope (Chapters I-II)


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def local_name(uri) -> str:
    """Return the local fragment of a URIRef, handling both '/' and '#' styles."""
    s = str(uri)
    if "#" in s:
        s = s.rsplit("#", 1)[-1]
    return s.rsplit("/", 1)[-1]


def section_number(uri) -> int | None:
    """Extract an int N from a 'SectionN' local name; None if it isn't one."""
    m = re.fullmatch(r"Section(\d+)", local_name(uri))
    return int(m.group(1)) if m else None


def section_numbers_in_text(text: str) -> list[int]:
    """Find every section number referenced inside a literal like 'Section 6, 20'."""
    return [int(n) for n in re.findall(r"[Ss]ection\s+(\d+)", text or "")]


def first_literal(g: Graph, subj, pred):
    for o in g.objects(subj, pred):
        if isinstance(o, Literal):
            return str(o)
    return None


def all_literals(g: Graph, subj, pred):
    return [str(o) for o in g.objects(subj, pred) if isinstance(o, Literal)]


# ---------------------------------------------------------------------------
# 1. PDF -> per-section text
# ---------------------------------------------------------------------------

# Repeated page boilerplate to drop before splitting on section headers.
_BOILERPLATE = [
    re.compile(r"^\(Unofficial Translation\)\s*$"),
    re.compile(r"^No\.\s*136\s+Chapter\s+69.*Gazette.*$"),
    re.compile(r"^\[Official Emblem.*\]\s*$"),
    re.compile(r"^-{3,}\s*$"),
    re.compile(r"^\d+\s*$"),                      # lone page numbers
    re.compile(r"^(Chapter|Part)\b.*$"),          # chapter / part heading lines
    re.compile(r"^Personal Data Protection\s*$"),
    re.compile(r"^-+\s*$"),
]


def extract_sections_from_pdf(pdf_path: str) -> dict[int, str]:
    """
    Extract text per Section (1..29) from the unofficial-translation PDF.

    Strategy: pull all page text, strip the repeated header/footer boilerplate,
    then split on capitalised 'Section N' headers. Cross-references inside the
    body use lowercase 'section N' and are NOT treated as headers.
    """
    try:
        import pdfplumber
    except ImportError:
        sys.exit("pdfplumber is required for PDF parsing: pip install pdfplumber")

    raw_lines: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            txt = page.extract_text() or ""
            raw_lines.extend(txt.splitlines())

    kept = []
    for line in raw_lines:
        line = line.strip()
        if not line:
            continue
        if any(p.match(line) for p in _BOILERPLATE):
            continue
        kept.append(line)

    full = " ".join(kept)

    # Split on capitalised "Section N" headers.
    parts = re.split(r"\bSection\s+(\d+)\b", full)
    # parts = [pre, num1, body1, num2, body2, ...]
    sections: dict[int, str] = {}
    for i in range(1, len(parts) - 1, 2):
        n = int(parts[i])
        if n < 1 or n > SCOPE_MAX_SECTION:
            continue  # ignore out-of-scope captures from any stray cross-ref
        body = parts[i + 1].strip()
        # Collapse whitespace; keep the longest capture if a number appears twice.
        body = re.sub(r"\s+", " ", body)
        if n not in sections or len(body) > len(sections[n]):
            sections[n] = body
    return sections


# ---------------------------------------------------------------------------
# 2. Ontology -> in-memory model
# ---------------------------------------------------------------------------

class Model:
    def __init__(self):
        self.chapters: dict[str, dict] = {}     # uri -> {name, title}
        self.parts: dict[str, dict] = {}        # uri -> {name, title, chapter}
        self.sections: dict[int, dict] = {}     # number -> {chapter, part}
        self.concepts: dict[str, dict] = {}     # name -> {label, definition, text, ...}
        self.individuals: dict[str, dict] = {}  # name -> {label, grounded_in, comment}
        self.subclass: list[tuple] = []         # (child_name, parent_name)
        self.requires: list[tuple] = []         # (concept_name, target_name, predicate)
        self.relates: list[tuple] = []          # (domain_name, range_name, predicate, section)
        self.cited_in: list[tuple] = []         # (concept_name, section_number)
        self.defined_in: list[tuple] = []       # (concept_name, section_number)
        self.act_chapters: list[str] = []       # chapter uris under the PDPA act
        self.act_name: str | None = None


def parse_ontology(ttl_path: str) -> Model:
    g = Graph()
    g.parse(ttl_path, format="turtle")
    m = Model()

    # --- Structural individuals: chapters, parts, sections -------------------
    chapter_cls = NS.Chapter
    part_cls = NS.Part
    section_cls = NS.Section

    for ch in g.subjects(RDF.type, chapter_cls):
        m.chapters[str(ch)] = {
            "name": local_name(ch),
            "title": first_literal(g, ch, NS["eli:title"]) or local_name(ch),
        }
    for pt in g.subjects(RDF.type, part_cls):
        m.parts[str(pt)] = {
            "name": local_name(pt),
            "title": first_literal(g, pt, NS["eli:title"]) or local_name(pt),
            "chapter": None,
        }

    # Chapter -> Part (has_Part) and resolve part.chapter
    for ch_uri, ch in m.chapters.items():
        for pt in g.objects(URIRef(ch_uri), NS.has_Part):
            if str(pt) in m.parts:
                m.parts[str(pt)]["chapter"] = ch_uri

    # Section -> (chapter | part). Build from has_Section on chapters and parts.
    section_to_chapter: dict[int, str] = {}
    section_to_part: dict[int, str] = {}
    for ch_uri in m.chapters:
        for sec in g.objects(URIRef(ch_uri), NS.has_Section):
            n = section_number(sec)
            if n:
                section_to_chapter[n] = ch_uri
    for pt_uri in m.parts:
        for sec in g.objects(URIRef(pt_uri), NS.has_Section):
            n = section_number(sec)
            if n:
                section_to_part[n] = pt_uri
                section_to_chapter[n] = m.parts[pt_uri]["chapter"]

    for sec in g.subjects(RDF.type, section_cls):
        n = section_number(sec)
        if not n:
            continue
        m.sections[n] = {
            "chapter": section_to_chapter.get(n),
            "part": section_to_part.get(n),
        }

    # PDPA act individual -> chapters
    for act in g.subjects(RDF.type, NS.PersonalDataProtectionAct):
        if isinstance(act, URIRef):
            m.act_name = local_name(act)
            for ch in g.objects(act, NS.has_Chapter):
                m.act_chapters.append(str(ch))
            break

    # --- Domain concepts: owl:Class with content ----------------------------
    concept_uris: set[str] = set()
    for cls in g.subjects(RDF.type, OWL.Class):
        if not isinstance(cls, URIRef):
            continue
        name = local_name(cls)
        if name in STRUCTURAL_CLASSES:
            continue
        concept_uris.add(str(cls))

        comments = all_literals(g, cls, RDFS.comment)
        definition = (first_literal(g, cls, P_DEFINITION)
                      or first_literal(g, cls, SKOS_DEF))
        see_also = all_literals(g, cls, RDFS.seeAlso)
        text = "\n\n".join([t for t in (comments + see_also) if t])

        m.concepts[name] = {
            "label": first_literal(g, cls, RDFS.label) or name,
            "definition": definition or (comments[0] if comments else ""),
            "text": text,
        }

        # Citations: :source -> CITED_IN ; isDefinedBy section refs -> DEFINED_IN
        for src in g.objects(cls, P_SOURCE):
            n = section_number(src)
            if n and n <= SCOPE_MAX_SECTION:
                m.cited_in.append((name, n))
        for idb in g.objects(cls, RDFS.isDefinedBy):
            for n in section_numbers_in_text(str(idb)):
                if n <= SCOPE_MAX_SECTION:
                    m.defined_in.append((name, n))

        # subClassOf: named parent -> SUBCLASS_OF ; restriction bnode -> REQUIRES
        for parent in g.objects(cls, RDFS.subClassOf):
            if isinstance(parent, URIRef):
                pname = local_name(parent)
                if pname not in STRUCTURAL_CLASSES:
                    m.subclass.append((name, pname))
            elif isinstance(parent, BNode):
                on_prop = next(g.objects(parent, OWL.onProperty), None)
                some_val = next(g.objects(parent, OWL.someValuesFrom), None)
                if on_prop is not None and some_val is not None:
                    m.requires.append(
                        (name, local_name(some_val), local_name(on_prop))
                    )

    # --- Object properties -> concept-to-concept RELATES edges ---------------
    # Materialise schema-level domain/range as navigable edges (controller
    # obligations etc.), tagged with the source section for citation.
    for prop in g.subjects(RDF.type, OWL.ObjectProperty):
        dom = next(g.objects(prop, RDFS.domain), None)
        rng = next(g.objects(prop, RDFS.range), None)
        if not (isinstance(dom, URIRef) and isinstance(rng, URIRef)):
            continue
        dname, rname = local_name(dom), local_name(rng)
        if str(dom) not in concept_uris or str(rng) not in concept_uris:
            continue
        sec = None
        for src in g.objects(prop, P_SOURCE):
            n = section_number(src)
            if n and n <= SCOPE_MAX_SECTION:
                sec = n
                break
        m.relates.append((dname, rname, local_name(prop), sec))

    # --- Meaningful individuals (lawful bases, exemptions, exceptions) -------
    for ind in g.subjects(RDF.type, OWL.NamedIndividual):
        if not isinstance(ind, URIRef):
            continue
        name = local_name(ind)
        types = {local_name(t) for t in g.objects(ind, RDF.type)}
        for type_name, (label, default_sec) in INDIVIDUAL_TYPE_MAP.items():
            if type_name in types:
                # Prefer an explicit :source section, else the type default.
                sec = default_sec
                for src in g.objects(ind, P_SOURCE):
                    n = section_number(src)
                    if n:
                        sec = n
                comment = first_literal(g, ind, RDFS.comment) or ""
                # isDefinedBy often holds the precise sub-section, e.g. "Section 24(3)"
                refined = first_literal(g, ind, RDFS.isDefinedBy)
                m.individuals[name] = {
                    "label": label,
                    "display": first_literal(g, ind, RDFS.label) or name,
                    "grounded_in": sec,
                    "comment": comment,
                    "ref": refined or "",
                }
                break

    return m


# ---------------------------------------------------------------------------
# 3. Embeddings
# ---------------------------------------------------------------------------

def embed_texts(texts: list[str]):
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(EMBED_MODEL)
    vecs = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)
    return [v.tolist() for v in vecs]


# ---------------------------------------------------------------------------
# 4. Write to Neo4j
# ---------------------------------------------------------------------------

def write_graph(m: Model, pdf_sections: dict[int, str], args):
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(args.uri, auth=(args.user, args.password))

    def run(tx, cypher, **params):
        tx.run(cypher, **params)

    with driver.session(database=args.database) as session:
        if args.wipe:
            session.execute_write(run, "MATCH (n) DETACH DELETE n")

        # --- Constraints + vector indexes ---
        session.execute_write(run,
            "CREATE CONSTRAINT section_number IF NOT EXISTS "
            "FOR (s:Section) REQUIRE s.number IS UNIQUE")
        session.execute_write(run,
            "CREATE CONSTRAINT concept_name IF NOT EXISTS "
            "FOR (c:Concept) REQUIRE c.name IS UNIQUE")
        session.execute_write(run, f"""
            CREATE VECTOR INDEX section_embedding IF NOT EXISTS
            FOR (s:Section) ON (s.embedding)
            OPTIONS {{indexConfig: {{`vector.dimensions`: {VECTOR_DIM},
                                     `vector.similarity_function`: 'cosine'}}}}""")
        session.execute_write(run, f"""
            CREATE VECTOR INDEX concept_embedding IF NOT EXISTS
            FOR (c:Concept) ON (c.embedding)
            OPTIONS {{indexConfig: {{`vector.dimensions`: {VECTOR_DIM},
                                     `vector.similarity_function`: 'cosine'}}}}""")

        # --- Structural spine: act, chapters, parts, sections ---
        if m.act_name:
            session.execute_write(run,
                "MERGE (a:LegalAct {name:$n})", n=m.act_name)
        for uri, ch in m.chapters.items():
            session.execute_write(run,
                "MERGE (c:Chapter {name:$n}) SET c.title=$t",
                n=ch["name"], t=ch["title"])
            if uri in m.act_chapters and m.act_name:
                session.execute_write(run,
                    "MATCH (a:LegalAct {name:$a}),(c:Chapter {name:$c}) "
                    "MERGE (a)-[:HAS_CHAPTER]->(c)",
                    a=m.act_name, c=ch["name"])
        for uri, pt in m.parts.items():
            session.execute_write(run,
                "MERGE (p:Part {name:$n}) SET p.title=$t",
                n=pt["name"], t=pt["title"])
            if pt["chapter"] and pt["chapter"] in m.chapters:
                session.execute_write(run,
                    "MATCH (c:Chapter {name:$c}),(p:Part {name:$p}) "
                    "MERGE (c)-[:HAS_PART]->(p)",
                    c=m.chapters[pt["chapter"]]["name"], p=pt["name"])

        # Sections in scope come from the ontology; ensure stubs for any
        # cited-but-out-of-scope sections too (so gaps are visible).
        cited_sections = {n for _, n in m.cited_in} | {n for _, n in m.defined_in}
        cited_sections |= {v["grounded_in"] for v in m.individuals.values()
                           if v["grounded_in"]}
        all_section_numbers = set(m.sections) | set(pdf_sections) | cited_sections

        for n in sorted(all_section_numbers):
            meta = m.sections.get(n, {})
            ch_name = (m.chapters.get(meta.get("chapter"), {}) or {}).get("name")
            pt_name = (m.parts.get(meta.get("part"), {}) or {}).get("name")
            text = pdf_sections.get(n)
            in_scope = n <= SCOPE_MAX_SECTION
            session.execute_write(run,
                "MERGE (s:Section {number:$n}) "
                "SET s.title=$title, s.chapter=$ch, s.part=$pt, "
                "    s.text=$text, s.in_scope=$scope, s.has_text=$has_text",
                n=n, title=f"Section {n}", ch=ch_name, pt=pt_name,
                text=text or "", scope=in_scope, has_text=bool(text))
            if ch_name and not pt_name:
                session.execute_write(run,
                    "MATCH (c:Chapter {name:$c}),(s:Section {number:$n}) "
                    "MERGE (c)-[:HAS_SECTION]->(s)", c=ch_name, n=n)
            if pt_name:
                session.execute_write(run,
                    "MATCH (p:Part {name:$p}),(s:Section {number:$n}) "
                    "MERGE (p)-[:HAS_SECTION]->(s)", p=pt_name, n=n)

        # --- Concepts ---
        for name, c in m.concepts.items():
            session.execute_write(run,
                "MERGE (x:Concept {name:$n}) "
                "SET x.label=$l, x.definition=$d, x.text=$t",
                n=name, l=c["label"], d=c["definition"], t=c["text"])

        # --- Meaningful individuals as their own labelled nodes ---
        for name, ind in m.individuals.items():
            label = ind["label"]  # LawfulBasis | Exemption | ConsentException
            session.execute_write(run,
                f"MERGE (x:{label} {{name:$n}}) "
                f"SET x.display=$disp, x.comment=$c, x.ref=$ref",
                n=name, disp=ind["display"], c=ind["comment"], ref=ind["ref"])
            if ind["grounded_in"]:
                session.execute_write(run,
                    f"MATCH (x:{label} {{name:$n}}),(s:Section {{number:$sec}}) "
                    f"MERGE (x)-[:GROUNDED_IN]->(s)",
                    n=name, sec=ind["grounded_in"])

        # --- Edges between concepts ---
        for child, parent in m.subclass:
            session.execute_write(run,
                "MATCH (a:Concept {name:$a}),(b:Concept {name:$b}) "
                "MERGE (a)-[:SUBCLASS_OF]->(b)", a=child, b=parent)
        for src, tgt, pred in m.requires:
            session.execute_write(run,
                "MATCH (a:Concept {name:$a}),(b:Concept {name:$b}) "
                "MERGE (a)-[r:REQUIRES]->(b) SET r.predicate=$p",
                a=src, b=tgt, p=pred)
        for dom, rng, pred, sec in m.relates:
            session.execute_write(run,
                "MATCH (a:Concept {name:$a}),(b:Concept {name:$b}) "
                "MERGE (a)-[r:RELATES {predicate:$p}]->(b) SET r.section=$s",
                a=dom, b=rng, p=pred, s=sec)

        # --- Citations ---
        for name, n in set(m.cited_in):
            session.execute_write(run,
                "MATCH (c:Concept {name:$c}),(s:Section {number:$n}) "
                "MERGE (c)-[:CITED_IN]->(s)", c=name, n=n)
        for name, n in set(m.defined_in):
            session.execute_write(run,
                "MATCH (c:Concept {name:$c}),(s:Section {number:$n}) "
                "MERGE (c)-[:DEFINED_IN]->(s)", c=name, n=n)

        # --- Embeddings ---
        if not args.no_embeddings:
            sec_rows = [(n, pdf_sections[n]) for n in sorted(pdf_sections)]
            if sec_rows:
                vecs = embed_texts([t for _, t in sec_rows])
                for (n, _), v in zip(sec_rows, vecs):
                    session.execute_write(run,
                        "MATCH (s:Section {number:$n}) SET s.embedding=$v",
                        n=n, v=v)
            con_rows = [(name, (c["definition"] or c["text"] or name))
                        for name, c in m.concepts.items()]
            if con_rows:
                vecs = embed_texts([t for _, t in con_rows])
                for (name, _), v in zip(con_rows, vecs):
                    session.execute_write(run,
                        "MATCH (c:Concept {name:$n}) SET c.embedding=$v",
                        n=name, v=v)

    driver.close()


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Build the PDPA Graph-RAG knowledge graph.")
    ap.add_argument("--ttl", required=True, help="Path to pdpav6.ttl")
    ap.add_argument("--pdf", required=True, help="Path to pdpa_Extract113.pdf")
    ap.add_argument("--uri", default="bolt://localhost:7687")
    ap.add_argument("--user", default="neo4j")
    ap.add_argument("--password", required=True)
    ap.add_argument("--database", default="neo4j")
    ap.add_argument("--wipe", action="store_true",
                    help="DETACH DELETE all nodes before building")
    ap.add_argument("--no-embeddings", action="store_true",
                    help="Skip embedding computation")
    args = ap.parse_args()

    print("Parsing ontology...")
    model = parse_ontology(args.ttl)
    print(f"  chapters={len(model.chapters)} parts={len(model.parts)} "
          f"sections={len(model.sections)} concepts={len(model.concepts)} "
          f"individuals={len(model.individuals)}")

    print("Extracting section text from PDF...")
    pdf_sections = extract_sections_from_pdf(args.pdf)
    got = sorted(pdf_sections)
    print(f"  extracted text for sections: {got}")
    missing = [n for n in range(1, SCOPE_MAX_SECTION + 1) if n not in pdf_sections]
    if missing:
        print(f"  WARNING: no text captured for sections {missing} "
              f"(check the PDF split assumptions)")

    print("Writing to Neo4j...")
    write_graph(model, pdf_sections, args)
    print("Done.")


if __name__ == "__main__":
    main()
