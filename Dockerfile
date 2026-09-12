FROM ghcr.io/cinnamon/kotaemon@sha256:cb4b71561e529398bacdf12f1289c32290f6c70f286b8efb7a1ed7e66d089b66

# Kotaemon launches from /app/.venv, so install the optional Docling reader into
# that exact environment rather than the container's system Python.
RUN uv pip install --python /app/.venv/bin/python -e "libs/kotaemon[docling]"
