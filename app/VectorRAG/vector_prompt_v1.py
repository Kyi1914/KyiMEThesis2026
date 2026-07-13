"""
vector_prompt_v1.py — Vector RAG (VRAG) prompt, version 1.

Mirrors the GRAG `promptTemplate/` module interface (VERSION + PROMPTS) so the VRAG
notebook can load it exactly the way it loads prompt2/prompt3/prompt4:

    import importlib, vector_prompt_v1 as pmod
    importlib.reload(pmod)                 # picks up edits without a kernel restart
    P, PROMPT_VERSION = pmod.PROMPTS, pmod.VERSION
    VECTOR_QA_TEMPLATE = P["vector_qa"]

Interface (kept parallel to the GRAG modules):
    VERSION : str
    PROMPTS : dict   -> single key "vector_qa"  (VRAG has no Cypher; one answer prompt)

Design notes
------------
- Variables are {question} and {context}, matching the LCEL chain in the reference
  notebook:
      rag_chain = (
          {"context": retriever | format_docs, "question": RunnablePassthrough()}
          | prompt | gpt4omini_model | StrOutputParser()
      )
  so it is a drop-in for that chain (just swap the inline prompt for this module).

- Section citation (primary metric): the template assumes each context block is
  prefixed with its source, e.g. "(cite: Section 6)". The `format_docs` helper at the
  bottom produces that prefix from chunk metadata, giving the model clean "Section N"
  tokens to copy. This prefixing is REQUIRED — without it the citation rule is inert
  and section-citation recall collapses to ~0.

- The refusal line matches GRAG's vector path ("I don't know based on the retrieved
  context.") so the same out-of-scope / graceful-degradation detection works for both
  systems.

Changes vs the old VRAG prompt
------------------------------
- Added the Citations block (cite every relied-upon Section as "(Section N)").
- Aligned the refusal string with GRAG's vector path for consistent scoring.
- Kept the originals: answer-from-context-only, don't-say-don't-know-if-answer-present,
  no apologies / no meta-commentary, concise.

This template is safe with `ChatPromptTemplate.from_template(...)`: it contains only the
{question} and {context} variables and no literal curly braces, so there is no brace-
escaping problem (unlike the GRAG Cypher prompt).
"""

VERSION = "vector_prompt_v1"

VECTOR_QA_TEMPLATE = """\
Task: Question answering about Thailand's Personal Data Protection Act (PDPA Thailand).
You are an expert assistant. Answer strictly from the retrieved context below.

Rules:
- Use ONLY the retrieved context to answer. Do not use outside knowledge and do not
  invent facts not present in the context.
- Make sure the answer is relevant to the question and supported by the context.
- Do NOT say you don't know if the context does contain the answer.
- If the context is empty or contains nothing relevant, reply exactly:
  I don't know based on the retrieved context.
- Be concise (2-6 sentences). Do not include explanations, apologies, or meta-commentary.

Citations (important):
- Each context block begins with its source, e.g. "(cite: Section 6)".
- Cite the section of EVERY block you actually rely on, written as "(Section N)".
- If several sections support the answer, cite each one, e.g. "(Section 19) (Section 24)".
- If a block shows "(cite: no section)", you may use its content but must not invent a
  section number for it.

Question:
{question}

Context:
{context}

Answer:
"""

# Parallel to the GRAG modules' PROMPTS dict. VRAG has a single answer prompt, so only
# the "vector_qa" key is present (same key name GRAG uses for its vector answer prompt).
PROMPTS = {
    "vector_qa": VECTOR_QA_TEMPLATE,
}


# ---------------------------------------------------------------------------
# Optional convenience: context formatter that surfaces the citable Section.
#
# Use this as the `format_docs` in your LCEL chain so the {context} the model sees
# actually contains "(cite: Section N)" markers. Pair it with the template above.
#
#     from vector_prompt_v1 import PROMPTS, format_docs
#     from langchain_core.prompts import ChatPromptTemplate
#     from langchain_core.runnables import RunnablePassthrough
#     from langchain_core.output_parsers import StrOutputParser
#
#     prompt = ChatPromptTemplate.from_template(PROMPTS["vector_qa"])
#     rag_chain_gpt4o = (
#         {"context": retriever | format_docs, "question": RunnablePassthrough()}
#         | prompt | gpt4omini_model | StrOutputParser()
#     )
#
# (If you prefer the manual `.replace()` style, the same template works:
#     PROMPTS["vector_qa"].replace("{question}", q).replace("{context}", format_docs(docs)) )
# ---------------------------------------------------------------------------
import re as _re


def _section_label(meta: dict) -> str:
    """Render a chunk's `section` metadata (int, list, or messy string) as 'Section N, ...'."""
    sec = (meta or {}).get("section")
    nums = []
    if isinstance(sec, (list, tuple, set)):
        for x in sec:
            if isinstance(x, bool):
                continue
            if isinstance(x, (int, float)):
                nums.append(int(x))
            elif isinstance(x, str):
                nums += [int(n) for n in _re.findall(r"\d+", x)]
    elif isinstance(sec, bool):
        pass
    elif isinstance(sec, (int, float)):
        nums.append(int(sec))
    elif isinstance(sec, str):
        nums += [int(n) for n in _re.findall(r"\d+", sec)]
    nums = sorted(set(nums))
    return ", ".join(f"Section {n}" for n in nums) if nums else "no section"


def format_docs(docs) -> str:
    """Serialize retrieved docs, prefixing each with its citable Section (and page if present).

    Each block looks like:
        [Doc 1] (cite: Section 6 | p.2)
        <chunk text>
    so the model has explicit "Section N" tokens to copy into "(Section N)" citations.
    """
    blocks = []
    for i, d in enumerate(docs, start=1):
        meta = getattr(d, "metadata", None) or {}
        page = meta.get("page")
        tail = f" | p.{page}" if page else ""
        text = getattr(d, "page_content", str(d))
        blocks.append(f"[Doc {i}] (cite: {_section_label(meta)}{tail})\n{text}")
    return "\n\n".join(blocks) if blocks else ""


if __name__ == "__main__":
    # quick self-check
    assert "{question}" in PROMPTS["vector_qa"] and "{context}" in PROMPTS["vector_qa"]
    assert "{" not in PROMPTS["vector_qa"].replace("{question}", "").replace("{context}", ""), \
        "Template must contain no stray braces beyond {question}/{context}."

    class _D:  # tiny stand-in for a LangChain Document
        def __init__(self, t, m): self.page_content, self.metadata = t, m

    sample = [
        _D("Personal data means information identifying a person.", {"section": 6, "page": 2}),
        _D("A controller may collect data without consent in some cases.", {"section": [19, 24], "page": 5}),
        _D("General provision.", {"section": None}),
    ]
    print("VERSION:", VERSION, "| keys:", list(PROMPTS))
    print("-" * 60)
    print(format_docs(sample))
