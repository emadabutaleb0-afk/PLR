import time
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

REQS = Counter("merch_http_requests_total", "HTTP requests", ["method", "path", "status"])
LAT = Histogram("merch_http_request_seconds", "HTTP latency", ["method", "path"], buckets=(.01, .05, .1, .25, .5, 1, 2.5, 5, 10, 30))
ERRS = Counter("merch_http_errors_total", "HTTP 5xx errors", ["path"])
JOB_DUR = Histogram("merch_job_duration_seconds", "Background job duration", ["kind"], buckets=(1, 5, 15, 30, 60, 120, 300, 900))
IMPORT_FAIL = Counter("merch_data_import_failures_total", "Failed or partial data imports")
MODEL_AGE = Gauge("merch_model_age_days", "Age of the active model", ["model"])
DATA_AGE = Gauge("merch_data_age_days", "Age of newest data")


def render():
    return generate_latest(), CONTENT_TYPE_LATEST


def observe_request(method, path, status, started):
    REQS.labels(method, path, str(status)).inc()
    LAT.labels(method, path).observe(time.time() - started)
    if status >= 500:
        ERRS.labels(path).inc()
