FROM apache/spark:3.5.3
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

USER root

RUN uv pip install --system --no-cache \
    google-cloud-bigquery==3.17.2 \
    google-cloud-storage==2.16.0 \
    pyarrow==14.0.2 \
    pandas==2.0.3

WORKDIR /app

COPY batch_job.py .
COPY streaming_job.py .

USER spark
