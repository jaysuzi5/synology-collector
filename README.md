# synology-collector:
This is a simple python application to get basic synology information and logs it to Postgres by calling an local API

## Project Structure

```bash
.
├── Dockerfile
├── requirements.txt
├── src/
│   └── synology-collector.py
│   └──configuration/
│      └── configuration.yaml
└── .env
```

## .env
The following environment variables need to be setup

```bash
NAS_USER="tbd"
NAS_PASSWORD="tbd"
NAS_IP="192.168.86.210"
NAS_PORT=5000
LOCAL_API_BASE_URL='http://home.dev.com/api/v1/synology'
```

## Error Handling

There is no specific retry logic at this time. If there are errors with one session, this should be logged and it will
retry the same pull for a full 24 hours. 

## Traces, Logs, and Metrics

Logs are exposed as OpenTelemetry.  When running locally, the collector will capture Traces to Tempo, Logs to Splunk, 
and metrics to Prometheus. 

## Docker File

```bash
docker login
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t jaysuzi5/synology-collector:latest \
  --push .
```
