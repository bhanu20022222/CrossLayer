FROM python:3.12-slim

LABEL maintainer="CrossLayer Research Project"
LABEL project="crosslayer"
LABEL component="document-retrieval"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 8080

ENV SERVICE_NAME=document-retrieval
ENV SERVICE_VERSION=0.1.0

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--threads", "4", "--access-logfile", "-", "app:app"]
