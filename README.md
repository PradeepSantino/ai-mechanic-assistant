# AI Mechanic Assistant

A local-first retrieval-augmented generation (RAG) platform for mechanics.

## Initial demo goal

1. Import automotive service-manual PDFs.
2. Ask a question about a vehicle or repair procedure.
3. Retrieve the relevant information from the correct manual.
4. Answer with source references.
5. Display an image of the exact supporting excerpt from the manual.

## Planned repository layout

```text
data/
  manuals/   Local source PDFs (not committed)
  indexes/   Generated search/vector indexes (not committed)
src/         Application code
tests/       Automated tests
```

The technology stack and application architecture will be chosen in the next phase.

## Run the local demo

Requirements: Docker Desktop and an OpenAI API key.

```bash
make setup
# Edit .env and add OPENAI_API_KEY
make up
```

Open <http://127.0.0.1:7860>. The initial Kotaemon login is `admin` / `admin`.

PDF quick uploads are forced through **Docling** with layout and table parsing.
OCR is disabled for this demo corpus because all 517 RAV4 PDFs already contain
embedded text. Local data is persisted under `data/kotaemon`; source manuals can
be placed under `data/manuals` and are never committed.

To prepare a local folder of manuals and index any files not already complete:

```bash
python3 scripts/prepare_manuals.py "/path/to/manual folder" data/manuals
docker compose exec -T app \
  /app/.venv/bin/python /app/project-scripts/index_manuals.py
```

The indexer processes one file at a time, reports each result, and continues
past individual failures. Original source PDFs are not modified.

Useful commands:

```bash
make status
make test
make logs
make down
```

The image is pinned by digest for reproducible setup and extended with
Kotaemon's optional Docling dependency. OpenAI `text-embedding-3-small` is the
default embedding model. Answers can cite the source PDF and page number; exact
cropped visual excerpts are a separate UI feature still to be implemented.
