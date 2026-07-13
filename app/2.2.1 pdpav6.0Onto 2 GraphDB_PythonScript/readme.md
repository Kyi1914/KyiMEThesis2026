### The script runs on your machine (not inside Neo4j) and talks to your running Neo4j over Bolt.

Here's the end-to-end. The script runs on your machine (not inside Neo4j) and talks to your running Neo4j over Bolt.

**1. Prerequisites**

- Python 3.10 or newer (the script uses `int | None` type syntax that needs 3.10+).
- Your Neo4j Desktop DBMS started and running, version 5.11+ (vector indexes require that; recent Desktop is fine).
- The three files in one folder: `build_pdpa_graph.py`, `pdpav6.ttl`, and `pdpa_Extract113.pdf`. Download the two project files and put them next to the script.

**2. Install the dependencies**

```
pip install rdflib pdfplumber neo4j sentence-transformers
```
These libraries do different jobs:

| Library                 | Purpose                                |
| ----------------------- | -------------------------------------- |
| `rdflib`                | Reads your Turtle ontology file `.ttl` |
| `pdfplumber`            | Extracts text from the PDPA PDF        |
| `neo4j`                 | Connects Python to Neo4j               |
| `sentence-transformers` | Creates embeddings for vector search   |


Heads up: `sentence-transformers` pulls in PyTorch and the embedding model is ~400 MB on first use, so this step and the first run take a while.


**3. Get your connection details from Neo4j Desktop**

The Bolt URI is almost always `bolt://localhost:7687`, the user is `neo4j`, and the password is whatever you set when you created the DBMS. (In Desktop, click your database → Connection details if you're unsure.)

URI: bolt://localhost:7687
User: neo4j
Password: your Neo4j password

**4. Do a fast dry run first (no embeddings)**

This validates the PDF parsing and the graph writes in seconds, without the slow model download:

```
python build_pdpa_graph.py \
  --ttl pdpav6.ttl \
  --pdf pdpa_Extract113.pdf \
  --uri bolt://localhost:7687 \
  --user neo4j \
  --password YOUR_PASSWORD \
  --wipe --no-embeddings
```

```
python build_pdpa_graph.py \
  --ttl pdpav6.ttl \
  --pdf pdpa_Extract113.pdf \
  --uri bolt://localhost:7687 \
  --user neo4j \
  --password 11111111 \
  --wipe --no-embeddings
```
```
python build_pdpa_graph.py `
  --ttl pdpav6.ttl `
  --pdf pdpa_Extract113.pdf `
  --uri bolt://localhost:7687 `
  --user neo4j `
  --password 11111111 `
  --wipe --no-embeddings
  ```

Watch the printout. You want to see something like `extracted text for sections: [1, 2, 3, ... 29]`. If any in-scope section is missing, it warns you — that's the PDF split needing a tweak, and worth fixing before you go further.

**5. Run the full build**

Once the dry run looks right, drop `--no-embeddings`:

```
python build_pdpa_graph.py \
  --ttl pdpav6.ttl \
  --pdf pdpa_Extract113.pdf \
  --uri bolt://localhost:7687 \
  --user neo4j \
  --password YOUR_PASSWORD \
  --wipe
```
```
python build_pdpa_graph.py `
  --ttl pdpav6.ttl `
  --pdf pdpa_Extract113.pdf `
  --uri bolt://localhost:7687 `
  --user neo4j `
  --password 11111111 `
  --wipe
  ```

**6. Verify in Neo4j Browser**

Run a few checks:

```cypher
// sections have real text
MATCH (s:Section) RETURN s.number, s.has_text, left(s.text,80) ORDER BY s.number;

// citations resolve concept -> section
MATCH (c:Concept)-[:CITED_IN|DEFINED_IN]->(s:Section)
RETURN c.name, collect(DISTINCT s.number) ORDER BY c.name;

// vector indexes exist and are ONLINE
SHOW INDEXES;
```

A couple of things to keep in mind. `--wipe` does `DETACH DELETE` on the **entire** target database, so point it at a fresh/dedicated DB rather than the one holding your n10s import you want to keep — or use `--database NAME` to target a separate one. And re-runs without `--wipe` are safe and idempotent (everything MERGEs on `Section.number` / `Concept.name`), so after editing `pdpav6.ttl` you can just re-run to update.

If the dry run shows missing section text or a connection error, paste me the console output and I'll pinpoint it.
