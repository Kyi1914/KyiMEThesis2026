"""
prompt3.py — Prompt version 3.

Change vs prompt2: the cypher_generation prompt gains an explicit
QUESTION TYPE -> PATTERN routing block and four additional worked examples
(Roles & Actors, Definition & Scope, Classification via SUBCLASS_OF taxonomy
traversal, and Operational / Procedural). The intent-routing block tells the
model which graph shape to reach for before it writes Cypher, which targets the
structural/enumeration questions that text-to-Cypher tends to mangle. The two
answer prompts (graph_qa, vector_qa) are UNCHANGED from prompt2.

Keep the SAME interface as prompt1/prompt2: VERSION (str) and PROMPTS (dict with
the three keys "cypher_generation", "graph_qa", "vector_qa"). Only the text
inside changes.

NOTE: the cypher_generation examples contain literal braces, e.g.
(:Section {number: 24}) and (:Concept {name, label, ...}). These strings must NOT
be passed through PromptTemplate f-string formatting (it would read the braces as
variables). The notebook fills {schema}/{question} by plain .replace() instead
(see the _build_cypher_prompt RunnableLambda cell).
"""

VERSION = "prompt3"

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
- IMPORTANT: Concept `label` and `name` are stored in PascalCase with NO spaces
  (e.g. PersonalDataProtectionPolicy, DataSubject, DataController). A spaced phrase
  will NEVER match them with CONTAINS. When matching against label/name, write your
  search term with NO spaces, and de-space the property too:
      toLower(replace(c.label,' ','')) CONTAINS 'personaldataprotectionpolicy'
- Natural-language wording lives in `definition` and `text`. Match THOSE with the
  normal spaced phrase. Always do BOTH so the match succeeds whichever field holds
  the term:
      WHERE toLower(replace(c.label,' ','')) CONTAINS 'personaldataprotectionpolicy'
         OR toLower(c.definition) CONTAINS 'personal data protection policy'

QUESTION TYPE -> PATTERN (pick the matching shape, then adapt the search terms):
- Definition ("what is X")            -> match the Concept; return definition + DEFINED_IN section.
- Definition & Scope ("is X covered") -> match the concept AND its contrasting concepts
                                          (natural vs legal person); reason about in/out of scope.
- Roles & Actors ("who is responsible")-> match the role concepts (controller/processor) AND the
                                          edge between them; responsibility follows the relationship.
- List / enumerate ("what are the X") -> match ALL instances of a type
                                          (LawfulBasis/Exemption/ConsentException) + GROUNDED_IN section.
- Classification ("is item Y a kind of Z") -> find the class, traverse SUBCLASS_OF UP to it, and
                                          enumerate its members to judge membership.
- Reverse ("which section says X")    -> match the Section, traverse BACK to its concepts/instances.
- Operational / Procedural ("must I do X, by when") -> match the procedural concept + REQUIRES edges
                                          + grounding section.

EXAMPLES:

1. Question: What is personal data?
MATCH (c:Concept)
WHERE toLower(replace(c.label,' ','')) CONTAINS 'personaldata'
   OR toLower(replace(c.name ,' ','')) CONTAINS 'personaldata'
   OR toLower(c.definition) CONTAINS 'personal data'
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
WHERE toLower(c.label) CONTAINS 'transfer' OR toLower(c.label) CONTAINS 'crossborder'
OPTIONAL MATCH (c)-[:DEFINED_IN|CITED_IN]->(s:Section)
RETURN c.label, c.definition, s.number AS section, s.text AS section_text
LIMIT 5;

7. Question (Roles & Actors): If an external organisation uses my company's facilities, who is responsible for data management?
Cypher:
MATCH (c:Concept)
WHERE toLower(c.label) CONTAINS 'controller' OR toLower(c.label) CONTAINS 'processor'
OPTIONAL MATCH (c)-[:DEFINED_IN]->(s:Section)
OPTIONAL MATCH (c)-[r:RELATES|REQUIRES]-(m:Concept)
RETURN c.label, c.definition, type(r) AS relationship, m.label AS related_role, s.number AS section
LIMIT 25;

8. Question (Definition & Scope): Are a company's name, address, and commercial or financial information personal data?
Cypher:
MATCH (c:Concept)
WHERE toLower(c.label) CONTAINS 'personaldata'
   OR toLower(c.label) CONTAINS 'datasubject'
   OR toLower(c.label) CONTAINS 'datacontroller'
   OR toLower(c.label) CONTAINS 'dataprocessor'
OPTIONAL MATCH (c)-[:DEFINED_IN]->(s:Section)
RETURN c.label, c.definition, c.text, s.number AS section, s.text AS section_text
ORDER BY section
LIMIT 10;

9. Question (Classification, reason up the taxonomy): Is employee/executive salary considered sensitive personal data under the PDPA?
Cypher:
MATCH (cls:Concept)
WHERE toLower(cls.label) CONTAINS 'sensitive'
OPTIONAL MATCH (member:Concept)-[:SUBCLASS_OF*1..3]->(cls)
OPTIONAL MATCH (cls)-[:DEFINED_IN]->(s:Section)
RETURN cls.label AS class, cls.definition, collect(DISTINCT member.label) AS items_in_class, s.number AS section;

10. Question (Operational / Procedural): Must the Personal Data Protection Policy and Privacy Notice be completed before the PDPA takes effect?
Cypher:
MATCH (c:Concept)
WHERE toLower(c.label) CONTAINS 'privacynotice'
   OR toLower(c.label) CONTAINS 'protectionpolicy'
   OR toLower(c.label) CONTAINS 'effective'
   OR toLower(c.label) CONTAINS 'enforcement'
OPTIONAL MATCH (c)-[r:REQUIRES|RELATES]-(m:Concept)
OPTIONAL MATCH (c)-[:DEFINED_IN|CITED_IN]->(s:Section)
RETURN c.label, c.definition, type(r) AS relationship, m.label AS related, s.number AS section
LIMIT 25;

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
