"""
prompt2.py — Prompt version 2.

Change vs prompt1: the two answer prompts (graph_qa, vector_qa) now require the
model to cite the PDPA Section number whenever the context contains one. This
targets section-grounded answers, which your scoring notebook measures via
section_recall. The cypher_generation prompt is unchanged from prompt1 except
that examples now also return section/definition fields where available.

Keep the SAME interface as prompt1: VERSION (str) and PROMPTS (dict with the
three keys). Only the text inside changes.
"""

VERSION = "prompt2"

CYPHER_GENERATION = """ 
You are a Cypher query generator for a Neo4j knowledge graph of Thailand's PDPA (Sections 1-29).
Generate ONE Cypher query that answers the question using ONLY the graph below.

GRAPH STRUCTURE:
- (:Concept {name, label, definition, text}) - domain concepts (e.g. PersonalData, DataSubject,
  Consent). `label` is the human-readable name; `definition` is the explanation text.
- (:Section {number, title, text, in_scope}) - statutory sections. `text` is the verbatim law;
  `number` is the citation (integer); `in_scope` = true for Sections 1-29.
- (:LawfulBasis {display, comment}), (:Exemption {display, comment}),
  (:ConsentException {display, comment}) - enumerated legal items. `display` is the label,
  `comment` is the explanation.
- Structure: (:LegalAct)-[:HAS_CHAPTER]->(:Chapter)-[:HAS_PART]->(:Part)-[:HAS_SECTION]->(:Section);
  also (:Chapter)-[:HAS_SECTION]->(:Section).
- Grounding / citation edges (use these to return a Section.number so the answer can cite it):
    (:Concept)-[:DEFINED_IN]->(:Section)      // where a concept is defined
    (:Concept)-[:CITED_IN]->(:Section)        // other sections mentioning it
    (:LawfulBasis|:Exemption|:ConsentException)-[:GROUNDED_IN]->(:Section)
    (:Concept)-[:RELATES|:SUBCLASS_OF|:REQUIRES]->(:Concept)

RULES:
- Use ONLY the labels, relationships, and properties above.
- Match text case-insensitively, e.g. WHERE toLower(c.label) CONTAINS 'consent'.
- Whenever possible, also return the related Section.number so the answer can cite the section.
- Section numbers are integers: match as (:Section {number: 24}).
- Use single quotes for strings. Add LIMIT 10 unless more rows are clearly needed.
- Return ONLY the Cypher. No explanation, no markdown fences.

EXAMPLES:

1. Question: What is personal data?
Cypher:
MATCH (c:Concept)
WHERE toLower(c.label) CONTAINS 'personal data' OR toLower(c.name) CONTAINS 'personaldata'
OPTIONAL MATCH (c)-[:DEFINED_IN]->(s:Section)
RETURN c.label, c.definition, s.number AS section
LIMIT 5;

2. Question: Who are the individuals involved in personal data?
Cypher:
MATCH (c:Concept)
WHERE toLower(c.label) CONTAINS 'datasubject'
   OR toLower(c.label) CONTAINS 'datacontroller'
   OR toLower(c.label) CONTAINS 'dataprocessor'
OPTIONAL MATCH (c)-[:DEFINED_IN]->(s:Section)
RETURN c.label, c.definition, s.number AS section
LIMIT 10;

3. Question: In what cases can personal data be collected, used or disclosed?
Cypher:
MATCH (lb:LawfulBasis)
OPTIONAL MATCH (lb)-[:GROUNDED_IN]->(s:Section)
RETURN lb.display, lb.comment, s.number AS section
ORDER BY section
LIMIT 25;

4. Question: When does the PDPA not apply?
Cypher:
MATCH (e:Exemption)
OPTIONAL MATCH (e)-[:GROUNDED_IN]->(s:Section)
RETURN e.display, e.comment, s.number AS section
LIMIT 25;

5. Question: What does Section 24 say?
Cypher:
MATCH (s:Section {number: 24})
RETURN s.number, s.title, s.text
LIMIT 1;

6. Question: What are the conditions for transferring personal data abroad?
Cypher:
MATCH (c:Concept)
WHERE toLower(c.label) CONTAINS 'transfer' OR toLower(c.label) CONTAINS 'cross border'
OPTIONAL MATCH (c)-[:DEFINED_IN|CITED_IN]->(s:Section)
RETURN c.label, c.definition, s.number AS section, s.text AS section_text
LIMIT 5;

Full auto-generated schema (authoritative reference):
{schema}

Question:
{question}
"""

QA_TEMPLATE = """
You are answering questions using ONLY the Neo4j query results below.

Rules:
- If the context is empty ([]), reply exactly: I don't know based on the graph.
- Otherwise, extract the relevant fields from context and answer the question directly.
- Do NOT say "I don't know" if context contains relevant information.
- If the context includes a section number, cite it in your answer, e.g. "(Section 24)".
- Keep the answer concise (2-6 sentences).

Question:
{question}

Context (Neo4j rows):
{context}

Answer:
"""


VECTOR_QA_TEMPLATE = """
You are answering questions using ONLY the retrieved vector-search context below.

Rules:
- If the retrieved context is empty, reply exactly: I don't know based on the retrieved context.
- Otherwise, answer directly from the context.
- Do not invent anything not present in the context.
- Keep the answer concise (2-6 sentences).

Question:
{question}

Retrieved context:
{retrieved_context}

Answer:
"""

PROMPTS = {
    "cypher_generation": CYPHER_GENERATION,
    "graph_qa":          QA_TEMPLATE,
    "vector_qa":         VECTOR_QA_TEMPLATE,
}

# PROMPTS = {
#     "cypher_generation": CYPHER_GENERATION,
#     "graph_qa":          GRAPH_QA,
#     "vector_qa":         VECTOR_QA,
# }