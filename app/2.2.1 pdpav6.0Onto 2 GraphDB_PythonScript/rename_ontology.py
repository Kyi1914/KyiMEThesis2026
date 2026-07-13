#!/usr/bin/env python3
"""
rename_ontology.py
==================

Unify the CLASS IRIs in pdpav6.ttl to underscore/hyphen-free PascalCase so the
IRI local name matches the rdfs:label convention (e.g. :Personal_Data ->
:
), across the declaration AND every reference.

Why this is safe
----------------
* Boundary-anchored: it renames the standalone ':Token' only (a leading ':'
  plus a trailing non-word/non-underscore boundary), so it NEVER corrupts a
  longer name that contains a shorter one. ':Personal_Data' is renamed but
  ':Personal_Data_Protection_Policy' and ':Sensitive_Personal_Data' are left for
  their own explicit rules. The colon anchor also prevents matching inside other
  tokens.
* Format-preserving: it edits the file as text, so all comments, ordering, and
  layout survive (unlike an rdflib re-serialize, which would reflow everything).
* Auditable: the mapping is an explicit list you can read and edit.
* Collision-aware: three class renames (Data_Controller / Data_Processor /
  Data_Subject) would clash with redundant empty ':... a :Entity' placeholder
  individuals. Those stubs carry no data and the build script ignores them, so
  this script removes them first and reports what it removed.

Scope / what is intentionally NOT renamed
------------------------------------------
* Object/datatype properties (has_part, is_part_of, ...). They are camelCase by
  convention, not PascalCase, and `has_part` vs `has_Part` BOTH normalize to
  `hasPart` -> a genuine collision. Rename those by hand if you want, and update
  build_pdpa_graph.py's NS.has_Part / NS.has_Section / NS.has_Chapter lookups to
  match. The build script's canon() already makes the GRAPH underscore-free
  regardless, so this is optional.
* The EX_* / LB_* named individuals keep their prefixes (a deliberate grouping
  convention). build_pdpa_graph.py doesn't depend on the prefix; its canon()
  strips the underscore in the graph anyway (EX_CreditBureau -> EXCreditBureau).
  If you DO add them to CLASS_NAMES below, also update reshape_pdpa_graph.cypher,
  which matches on '/LB_' and '/EX_'.

Usage
-----
  python rename_ontology.py                 # edits pdpav6.ttl in place
  python rename_ontology.py --in pdpav6.ttl --out pdpav6_clean.ttl  # dry copy
  python rename_ontology.py --keep-placeholders   # rename but DON'T delete stubs
"""

import argparse
import re
import sys

# --- Class local names containing '_' or '-'. Targets are derived by canon(),
#     listed here only so the set is explicit and editable. ---------------------
CLASS_NAMES = [
    "Consent_Activity",
    "Controller_Obligation",
    "Cross-border_Transfer",
    "DPO_Obligation",
    "Data_Activity",
    "Data_Controller",
    "Data_Processor",
    "Data_Protection_Officer_DPO",
    "Data_Subject",
    "Data_Subject_Rights",
    "Erase_Data",
    "Insensitive_Personal_Data",
    "Obtaining_Consent_from_Data_Subject",
    "Personal_Data",
    "Personal_Data_Protection_Policy",
    "Processor_Obligation",
    "Rectify_Data",
    "Right_of_Data_Portability",
    "Right_to_Erasure_or_Destruction",
    "Right_to_Object_Processing",
    "Right_to_Rectification",
    "Right_to_Restriction_of_Use",
    "Sensitive_Personal_Data",
    "Share_Personal_Data_with_Third_Party",
    "Use_Data",
    "Withdrawing_Given_Consent",
]

# Redundant ':<name> a :Entity' placeholder individuals whose IRI would collide
# with a renamed class. Removed before renaming (unless --keep-placeholders).
COLLIDING_PLACEHOLDERS = ["DataController", "DataProcessor", "DataSubject"]


def canon(name: str) -> str:
    """Underscore/hyphen-free PascalCase. Must match build_pdpa_graph.canon()."""
    return "".join(seg[:1].upper() + seg[1:] for seg in re.split(r"[-_]", name) if seg)


def remove_placeholder_individual(text: str, name: str) -> tuple[str, bool]:
    """Remove a simple ':<name> a owl:NamedIndividual , :Entity ; ... .' stanza."""
    pattern = re.compile(
        rf"(?ms)^:{re.escape(name)}\s+rdf:type\s+owl:NamedIndividual\s*,"
        rf"\s*:Entity\s*;.*?\.\s*$\n?"
    )
    new_text, n = pattern.subn("", text)
    return new_text, n > 0


def main():
    ap = argparse.ArgumentParser(description="Unify PDPA class IRIs to PascalCase.")
    ap.add_argument("--in", dest="src", default="pdpav6.ttl")
    ap.add_argument("--out", dest="dst", default=None,
                    help="Output path (default: overwrite the input)")
    ap.add_argument("--keep-placeholders", action="store_true",
                    help="Rename classes but do NOT delete the colliding Entity stubs")
    args = ap.parse_args()
    dst = args.dst or args.src

    text = open(args.src, encoding="utf-8").read()
    mapping = {old: canon(old) for old in CLASS_NAMES}

    # --- 1. Sanity: no two class names canonicalize to the same target --------
    seen = {}
    for old, new in mapping.items():
        if new in seen:
            sys.exit(f"ERROR: '{old}' and '{seen[new]}' both -> ':{new}'. Fix the list.")
        seen[new] = old

    # --- 2. Remove colliding placeholder individuals --------------------------
    if not args.keep_placeholders:
        for name in COLLIDING_PLACEHOLDERS:
            text, removed = remove_placeholder_individual(text, name)
            print(f"{'removed' if removed else 'not found'}: placeholder individual :{name}")

    # --- 3. Warn on any remaining collision (target IRI already in the file) ---
    for old, new in mapping.items():
        if old == new:
            continue
        if re.search(rf":{re.escape(new)}(?![A-Za-z0-9_])", text):
            print(f"WARNING: target ':{new}' already appears in the file; "
                  f"renaming ':{old}' will MERGE onto it. Review before trusting.")

    # --- 4. Apply boundary-anchored renames -----------------------------------
    changed = 0
    for old, new in mapping.items():
        if old == new:
            continue
        text, n = re.subn(rf":{re.escape(old)}(?![A-Za-z0-9_])", f":{new}", text)
        if n:
            changed += n
            print(f"renamed :{old} -> :{new}  ({n} occurrences)")

    open(dst, "w", encoding="utf-8").write(text)
    print(f"\nDone. {changed} IRI references rewritten -> {dst}")
    print("Re-run build_pdpa_graph.py (its canon() already matches these names).")


if __name__ == "__main__":
    main()
