"""
prompt1.py — Prompt version 1 (baseline).

Every prompt file must expose the SAME interface so the notebook and the
save/scoring logic stay unchanged when you switch versions:

    VERSION : str           a label that lands in your saved results
    PROMPTS : dict          keys: "cypher_generation", "graph_qa", "vector_qa"

Notebook usage:
    import importlib
    PROMPT_MODULE = "prompt1"
    pmod = importlib.import_module(PROMPT_MODULE)
    importlib.reload(pmod)
    P, PROMPT_VERSION = pmod.PROMPTS, pmod.VERSION

Braces: {schema}, {question}, {context}, {retrieved_context} are runtime
variables (single brace). Literal braces in Cypher must be doubled: {{ }}.
"""

VERSION = "prompt1"

CYPHER_GENERATION = """ 
You are a Cypher query generator for a Neo4j graph database. 
Given the following schema and question, generate a single Cypher query that can be executed against the database to answer the question.

Task: Generate a single Cypher query to answer the question using the schema.

Rules / Instructions:
- Use ONLY classes/labels/relationship types/property keys present in the schema.
- Use single quotes for string literals.
- Use CONTAINS for substring matching when needed.
- If any label/relationship/property contains special characters (e.g., ':'), wrap it in backticks.
- Prefer multi-label matches when schema indicates combined labels (e.g., :Resource:owl__Class).
- Return only the Cypher. No explanations.
- Add LIMIT 5 unless the question explicitly requires more.
- Return only Cypher.
- If the question is ambiguous, generate a query that retrieves relevant information without making assumptions, using the schema to find relevant nodes/relationships that can help answer the question, rather than guessing specific labels or properties.

Schema:
{schema}

Cypher examples:

1. Question: What is PDPA?
Cypher:  
   MATCH (n:Resource)
   WHERE coalesce(n.rdfs__label, '') CONTAINS 'PDPA' OR coalesce(n.rdfs__comment, '') CONTAINS 'PDPA'
   RETURN n.rdfs__comment
   LIMIT 5;

2. Question: What is a personal data protection policy?
Cypher:
   MATCH (n:Resource)
   WHERE coalesce(n.rdfs__label, '') CONTAINS 'PersonalDataProtectionPolicy'
      OR coalesce(n.rdfs__comment, '') CONTAINS 'personal data protection policy'
   RETURN n.rdfs__comment, n.rdfs__isDefinedBy
   LIMIT 5;

3. Question: What are the rights of the data subject?
Cypher:
   MATCH (n:Resource {{ rdfs__label: 'DataSubjectRights' }})
   OPTIONAL MATCH (n)-[r]-(m)
   RETURN n.rdfs__comment, n.rdfs__label, r.rdfs__label, m.rdfs__label, m.rdfs__comment, n.rdfs__isDefinedBy
   LIMIT 5;

4. Question: Is salary information considered sensitive personal data under the PDPA?
Cypher:
MATCH (n:Resource {{ rdfs__label: 'Sensitive Personal Data' }})
OPTIONAL MATCH (n)-[r]-(m)
RETURN n.rdfs__comment, n.rdfs__label, r.rdfs__label, m.rdfs__label, m.rdfs__comment, n.rdfs__isDefinedBy
LIMIT 5;

5. Question: Are a company's name, address, and commercial or financial information personal?
Cypher:
MATCH (n:Resource {{rdfs__label: 'PersonalData'}})
OPTIONAL MATCH (n)-[r]-(m)
RETURN n.rdfs__comment, n.rdfs__label, r.rdfs__label, m.rdfs__label, m.rdfs__comment, n.rdfs__isDefinedBy
LIMIT 5;

Question:
{question}

"""

GRAPH_QA = """
You are answering questions using ONLY the Neo4j query results below.

Rules:
- If the context is empty ([]), reply exactly: I don't know based on the graph.
- Otherwise, extract the relevant fields from context and answer the question directly.
- Do NOT say "I don't know" if context contains relevant information.
- Keep the answer concise (2-6 sentences).

Question:
{question}

Context (Neo4j rows):
{context}

Answer:
"""

VECTOR_QA = """
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
    "graph_qa":          GRAPH_QA,
    "vector_qa":         VECTOR_QA,
}
