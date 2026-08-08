# Mirrors catalog-api/Dockerfile's shape. NOT a solved hosting story — see
# the "Docker / centralized hosting" note in README.md: Claude Code's normal
# auth is an interactive OAuth flow tied to the local machine, so a
# container needs ANTHROPIC_API_KEY (or apiKeyHelper via --settings)
# instead, which this image does not configure. Useful for local
# containerized testing of the UI itself, not for shipping to users today.
#
# Build context MUST be data-reporter/ (not ui/), since odrkit + ui/ need
# each other:
#   docker build -f ui/Dockerfile -t odr-ui .   (run from data-reporter/)

FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

# Copy the whole data-reporter checkout (odrkit + ui/ need each other and
# the repo-relative paths odrkit already assumes — see CLAUDE.md).
COPY . /app

RUN uv sync --extra ui

EXPOSE 8110

CMD ["uv", "run", "uvicorn", "backend.app:app", "--app-dir", "ui", "--host", "0.0.0.0", "--port", "8110"]
