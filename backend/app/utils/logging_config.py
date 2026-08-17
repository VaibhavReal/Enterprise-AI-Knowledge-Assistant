"""
Structured logger and timing utilities.

Provides a consistent logging format across all backend modules.
Includes a context manager for timing operations and logging their duration.

Security note: Never log API keys, passwords, JWT tokens, or sensitive document content.
"""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
import sys


def get_logger(name: str) -> logging.Logger:
    """
    Create or retrieve a logger with consistent formatting.

    Logs to stdout so output is captured by Docker, systemd, and most
    deployment environments without additional configuration.

    Format: 2024-01-15 10:23:45,123 | INFO | module.name | message
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(logging.INFO)

        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        # Prevent double-logging if the root logger is also configured
        logger.propagate = False

    return logger


@contextmanager
def timer(logger: logging.Logger, operation_name: str):
    """
    Context manager that measures and logs the duration of an operation.

    Usage:
        with timer(logger, "embedding generation"):
            embeddings = model.encode(texts)

    Output: '2024-01-15 ... | INFO | ... | embedding generation completed in 1.2345 seconds'
    """
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        logger.info(f"{operation_name} completed in {duration:.4f}s")
