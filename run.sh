#!/bin/sh
# OTel zero-code instrumentation only when an OTLP endpoint is configured —
# otherwise zero overhead and no double-wrap when the OTel Operator injects it.
set -e
if [ -n "${OTEL_EXPORTER_OTLP_ENDPOINT}" ]; then
    exec opentelemetry-instrument python main.py
else
    exec python main.py
fi
