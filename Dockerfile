FROM ghcr.io/cinnamon/kotaemon@sha256:cb4b71561e529398bacdf12f1289c32290f6c70f286b8efb7a1ed7e66d089b66

# Kotaemon launches from /app/.venv, so install the optional Docling reader into
# that exact environment rather than the container's system Python.
RUN uv pip install --python /app/.venv/bin/python -e "libs/kotaemon[docling]"

# Kotaemon's Quick Upload normally forces PDFs back to its default reader even
# when Docling is selected in Settings. Make Docling the default and enforce it
# for quick uploads so demo indexes cannot silently use PDFThumbnailReader.
COPY docker/force_docling.py /tmp/force_docling.py
RUN /app/.venv/bin/python /tmp/force_docling.py && rm /tmp/force_docling.py
