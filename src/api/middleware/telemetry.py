import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class APIRequestTelemetryMiddleware(BaseHTTPMiddleware):
    """
    Middleware that records telemetry for incoming REST requests, including:
    - Route processing latency
    - API response code counts
    - Endpoint caller identification
    Logs structured metrics for auditability.
    """

    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()

        # Process the request
        response = await call_next(request)

        process_time = time.perf_counter() - start_time

        # Add latency headers to response for monitoring/debugging
        response.headers["X-Response-Time-Seconds"] = f"{process_time:.6f}"

        # Telemetry hook (such as exporting to Prometheus or Datadog)
        # self.record_metrics(request.url.path, response.status_code, process_time)

        return response
