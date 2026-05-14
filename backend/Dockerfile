FROM python:3.12-slim AS builder
WORKDIR /build
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"
COPY pyproject.toml README.md ./
COPY app/ ./app/
RUN pip install --upgrade pip && pip install --no-cache-dir .

FROM python:3.12-slim AS runtime
RUN groupadd --gid 1001 app && useradd --uid 1001 --gid app --no-create-home app
COPY --from=builder /venv /venv
WORKDIR /app
ENV PATH="/venv/bin:$PATH"
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--log-level", "info"]
