"""
prompt4.py — Prompt version 4.

Change vs prior cypher prompt: this revision targets two distinct, diagnosed
Cypher-retrieval failure classes, while leaving graph_qa and vector_qa BYTE-FOR-
BYTE identical to prompt2 (so the Cypher prompt remains the only experimental
variable for scoring).

Diagnosed failures addressed
----------------------------
1. PDPA-003 ("What is a personal data protection policy?") — ZERO-RESULT.
   Stored labels are PascalCase with no spaces (PersonalDataProtectionPolicy),
   but the model wrote a spaced phrase into CONTAINS, so the literal substring
   never matched -> graph_rows = [] -> vector fallback retrieved the wrong nodes.
   Fix: label NORMALIZATION rule + examples (de-space both the property and the
   search term; also search the natural-language `definition` field).

2. PDPA-016 ("Does the collection-notice require the data owner's signature?") —
   TOPIC DRIFT (false-positive retrieval). The answer lives on the PrivacyNotice
   concept ("Signature required?: No"), but the model anchored on 'consent' and
   pasted the full question phrase 'signature of the data owner' into CONTAINS
   (which matches nothing). It returned 7 consent rows in `graph` mode and the
   generator correctly refused.
   Fix: SALIENT-KEYWORD rule (search short terms, never full sentences),
   ANTI-OVER-ANCHOR rule (OR several salient terms; don't commit to one wrong
   keyword), and a QUESTION-TYPE ROUTING block that sends compliance-document /
   procedural questions to the :Rule subclasses (PrivacyNotice, Policy) instead
   of :Consent.

Also folded in
--------------
- DEDUP return shape: a concept linked to several sections used to fan out into
  one duplicate row per edge (e.g. Consent x {19,20,21}). Examples now aggregate
  with `WITH c, collect(DISTINCT s.number) AS sections` so each concept is ONE
  row carrying a section list — cleaner context, no wasted LIMIT budget.

Keep the SAME interface: VERSION (str) and PROMPTS (dict with the three keys).
"""

VERSION = "prompt4"

CYPHER_GENERATION = """ 
You are a Cypher query generator for a Neo4j knowledge graph of Thailand's PDPA (Sections 1-29).
Generate ONE Cypher query that answers the question using ONLY the graph below.

GRAPH STRUCTURE:
- (:Concept {name, label, definition, text}) - domain concepts (e.g. PersonalData, DataSubject,
  Consent, PrivacyNotice, PersonalDataProtectionPolicy). `label`/`name` are the identifiers;
  `definition` holds the natural-language explanation (and, for :Rule concepts, curated answer
  notes such as required elements or "Signature required?: No").
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
- LABEL NORMALIZATION: `label` and `name` are stored in PascalCase with NO spaces
  (PersonalDataProtectionPolicy, DataSubject, PrivacyNotice). A spaced phrase will NEVER match
  them with CONTAINS. When matching label/name, write the search term with NO spaces AND de-space
  the property too, e.g.
      toLower(replace(c.label,' ','')) CONTAINS 'personaldataprotectionpolicy'
- NATURAL LANGUAGE lives in `definition` and `text` (and section `text`). Match THOSE with the
  normal spaced wording, and ALWAYS pair them with the de-spaced label match so the query
  succeeds whichever field holds the term.
- SALIENT KEYWORDS ONLY: search 1-3 short key terms, NEVER a whole question sentence. Pasting a
  long phrase into CONTAINS almost always returns nothing. Example: for "...require the signature
  of the data owner?" search 'signature', not 'signature of the data owner'.
- DO NOT OVER-ANCHOR: OR together several salient terms across label and definition rather than
  committing to one keyword. If a question is about a notice/document, do not collapse it onto
  'consent' just because consent is nearby.
- DEDUP: a concept may link to several sections and will otherwise produce one duplicate row per
  edge. Aggregate instead: `WITH c, collect(DISTINCT s.number) AS sections` and return `sections`.
- Section numbers are integers: match as (:Section {number: 24}).
- Use single quotes for strings. Add LIMIT 10 unless more rows are clearly needed.
- Return ONLY the Cypher. No explanation, no markdown fences.

QUESTION-TYPE -> PATTERN (route before you write the query):
- DEFINITION ("What is X?") -> match Concept by de-spaced label OR definition keyword;
  return definition + sections.
- ROLES & ACTORS ("Who ...?") -> match DataSubject / DataController / DataProcessor labels.
- LAWFUL BASIS ("When can data be collected/used/disclosed?") -> match (:LawfulBasis).
- EXEMPTIONS ("When does the PDPA not apply?") -> match (:Exemption).
- SECTION LOOKUP ("What does Section N say?") -> match (:Section {number: N}); return s.text.
- CLASSIFICATION / hierarchy -> traverse (:Concept)-[:SUBCLASS_OF*1..3]->(:Concept).
- COMPLIANCE DOCUMENTS & PROCEDURAL ("Does document X require Y?", "what must be included in...",
  "is a signature/notice needed?") -> these map to the :Rule subclasses PrivacyNotice and
  PersonalDataProtectionPolicy. Search their definition/text for the document type AND the
  requirement keyword (e.g. 'notice', 'inform', 'signature'). DO NOT default to :Consent.

EXAMPLES:

1. Question: What is personal data?
Cypher:
MATCH (c:Concept)
WHERE toLower(replace(c.label,' ','')) CONTAINS 'personaldata'
   OR toLower(c.definition) CONTAINS 'personal data'
OPTIONAL MATCH (c)-[:DEFINED_IN]->(s:Section)
WITH c, collect(DISTINCT s.number) AS sections
RETURN c.label, c.definition, c.text, sections
LIMIT 5;

2. Question: Who are the individuals involved in personal data?
Cypher:
MATCH (c:Concept)
WHERE toLower(replace(c.label,' ','')) CONTAINS 'datasubject'
   OR toLower(replace(c.label,' ','')) CONTAINS 'datacontroller'
   OR toLower(replace(c.label,' ','')) CONTAINS 'dataprocessor'
OPTIONAL MATCH (c)-[:DEFINED_IN]->(s:Section)
WITH c, collect(DISTINCT s.number) AS sections
RETURN c.label, c.definition, c.text, sections
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
WHERE toLower(replace(c.label,' ','')) CONTAINS 'transfer'
   OR toLower(c.definition) CONTAINS 'transfer'
   OR toLower(c.definition) CONTAINS 'cross border'
OPTIONAL MATCH (c)-[:DEFINED_IN|CITED_IN]->(s:Section)
WITH c, collect(DISTINCT s.number) AS sections, c.text AS section_text
RETURN c.label, c.definition, c.text, sections, section_text
LIMIT 5;

7. Question: What is a personal data protection policy?
   (DEFINITION — note de-spaced label match; spaced phrase only against definition.)
Cypher:
MATCH (c:Concept)
WHERE toLower(replace(c.label,' ','')) CONTAINS 'personaldataprotectionpolicy'
   OR toLower(c.definition) CONTAINS 'protection policy'
OPTIONAL MATCH (c)-[:DEFINED_IN|CITED_IN]->(s:Section)
WITH c, collect(DISTINCT s.number) AS sections
RETURN c.label, c.definition, c.text, sections
LIMIT 5;

8. Question: Does the document informing the data owner of the collection of personal data
   require the signature of the data owner?
   (COMPLIANCE DOCUMENT / PROCEDURAL — route to :Rule concepts via 'notice'/'inform'/'signature';
   short salient keywords only; DO NOT anchor on 'consent'.)
Cypher:
MATCH (c:Concept)
WHERE toLower(replace(c.label,' ','')) CONTAINS 'privacynotice'
   OR toLower(c.definition) CONTAINS 'notice'
   OR toLower(c.definition) CONTAINS 'inform'
   OR toLower(c.definition) CONTAINS 'signature'
OPTIONAL MATCH (c)-[:DEFINED_IN|CITED_IN]->(s:Section)
WITH c, collect(DISTINCT s.number) AS sections
RETURN c.label, c.definition, c.text, sections
LIMIT 10;

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
