import logging
import os
import sys

import structlog


def configure_structured_logging() -> None:
    """
    Configures python standard logging and structlog to output structured logs.
    Outputs JSON logs in production environments and colored human-readable logs locally.
    """
    # Read environment log levels, default to INFO
    log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    # Configure root standard logger
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # Define common structlog processors
    processors = [
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    env = os.getenv("ENVIRONMENT", "development").lower()
    if env == "production":
        # JSON logs in production for cloud aggregations (e.g. Datadog, ELK)
        processors.append(structlog.processors.JSONRenderer())
    else:
        # Beautiful colored console logs for development
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    # Configure structlog globally
    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
