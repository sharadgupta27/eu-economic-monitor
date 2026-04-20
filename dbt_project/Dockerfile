FROM python:3.11-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

RUN uv pip install --system --no-cache dbt-bigquery==1.7.9

WORKDIR /dbt

COPY . .

CMD ["dbt", "run"]
