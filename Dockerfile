FROM node:22-bookworm-slim AS web
WORKDIR /app/web
COPY web/package*.json ./
RUN npm ci
COPY web/ ./
RUN npm run build
FROM python:3.11-slim
WORKDIR /app
ENV LLM_EVAL_HOME=/app
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .
COPY artifacts ./artifacts
COPY reports ./reports
COPY assets ./assets
COPY --from=web /app/web/dist ./web/dist
RUN useradd -m runner && mkdir -p data && chown -R runner:runner /app
USER runner
EXPOSE 8013
CMD ["uvicorn","llm_eval_lab.api:app","--host","0.0.0.0","--port","8013"]
