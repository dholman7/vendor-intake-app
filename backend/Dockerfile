# Build context is the repo root so the root .python-version is available; uv installs that Python.
FROM ghcr.io/astral-sh/uv:bookworm-slim

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_INSTALL_DIR=/opt/python \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app
COPY .python-version backend/pyproject.toml backend/uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY backend/src ./src
RUN uv sync --locked --no-dev \
    && useradd --create-home --uid 10001 app \
    && mkdir -p /app/data \
    && chown app /app/data

USER app
EXPOSE 8000
# Seeding is idempotent: it skips when demo tenants already exist.
CMD ["sh", "-c", "python -m vendor_intake.seed && exec uvicorn vendor_intake.main:create_app --factory --host 0.0.0.0 --port 8000"]
