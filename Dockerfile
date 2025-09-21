FROM python:3.12.9-slim-bookworm
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ /app/src/
ENV LOCAL_API_BASE_URL='http://home.dev.com/api/v1/synology'
ENV NAS_USER="tbd"
ENV NAS_PASSWORD="tbd"
ENV NAS_IP="192.168.86.210"
ENV NAS_PORT=5000
ENV LOCAL_API_BASE_URL='http://home.dev.com/api/v1/synology'

CMD ["opentelemetry-instrument", "--logs_exporter", "otlp", "--traces_exporter", "otlp", "python", "/app/src/synology-collector.py"]
