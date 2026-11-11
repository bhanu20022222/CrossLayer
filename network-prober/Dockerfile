FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY src/network_prober /app/network_prober

USER 0:0
EXPOSE 9116

CMD ["python", "-m", "network_prober"]
