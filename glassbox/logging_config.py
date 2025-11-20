"""
GlassBox Logging Configuration

Provides structured JSON logging for production environments.
"""

import logging
import sys
from typing import Optional
from datetime import datetime
import json


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs logs as JSON for structured logging.

    This makes logs easily parseable by log aggregation systems like
    ELK stack, Datadog, CloudWatch, etc.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add extra fields if present
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "model"):
            log_data["model"] = record.model
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        if hasattr(record, "status_code"):
            log_data["status_code"] = record.status_code

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


class SimpleFormatter(logging.Formatter):
    """
    Human-readable formatter for development.

    Outputs colorful, easy-to-read logs for local development.
    """

    # Color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        color = self.COLORS.get(record.levelname, self.RESET)
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Build base message
        message = f"{color}[{timestamp}] {record.levelname:8s}{self.RESET} {record.name}: {record.getMessage()}"

        # Add request_id if present
        if hasattr(record, "request_id"):
            message += f" (req_id={record.request_id})"

        # Add exception if present
        if record.exc_info:
            message += "\n" + self.formatException(record.exc_info)

        return message


def setup_logging(
    level: str = "INFO",
    format_type: str = "simple",
    logger_name: Optional[str] = None
) -> logging.Logger:
    """
    Configure logging for GlassBox.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: "simple" for development, "json" for production
        logger_name: Name of logger to configure (None = root logger)

    Returns:
        Configured logger instance

    Example:
        >>> # Development
        >>> logger = setup_logging(level="DEBUG", format_type="simple")
        >>> logger.info("Server started")

        >>> # Production
        >>> logger = setup_logging(level="INFO", format_type="json")
        >>> logger.info("Request processed", extra={"request_id": "abc123", "duration_ms": 45})
    """
    # Get logger
    logger = logging.getLogger(logger_name)
    logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level.upper()))

    # Set formatter based on type
    if format_type == "json":
        formatter = StructuredFormatter()
    else:
        formatter = SimpleFormatter()

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Don't propagate to root logger (avoid duplicate logs)
    logger.propagate = False

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.

    Args:
        name: Module name (usually __name__)

    Returns:
        Logger instance

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing request")
    """
    return logging.getLogger(name)


# Default logger for the glassbox package
logger = setup_logging(logger_name="glassbox")
