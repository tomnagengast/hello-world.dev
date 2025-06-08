"""Logging configuration and utilities."""

import sys
import logging
import logging.handlers
import structlog
from pathlib import Path
from datetime import datetime
import json
from typing import Optional, Union


def setup_logging(
    debug: bool = False,
    log_file: bool = True,
    log_level: str = "INFO",
    log_format: str = "json",
    log_dir: Optional[Union[str, Path]] = None,
    session_id: Optional[str] = None,
    file_rotation_mb: int = 10,
    file_backup_count: int = 7,
) -> None:
    """
    Configure structured logging for the application.

    Args:
        debug: Enable debug logging (overrides log_level)
        log_file: Whether to log to file in addition to console
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_format: Log format (json, dev)
        log_dir: Directory for log files
        session_id: Optional session ID for session-specific logs
        file_rotation_mb: File rotation size in MB
        file_backup_count: Number of backup files to keep
    """
    # Configure log level
    if debug:
        log_level = "DEBUG"

    # Create logs directory
    if log_file:
        log_dir = Path(log_dir or "./logs")
        log_dir.mkdir(exist_ok=True)

        # Generate log file name
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        if session_id:
            log_filename = f"session_{session_id}_{timestamp}.log"
        else:
            log_filename = f"conversation_{timestamp}.log"
        log_path = log_dir / log_filename

    # Configure processors based on format
    base_processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    # Choose renderer based on format and output
    if log_format == "dev" or (sys.stderr.isatty() and log_format != "json"):
        console_processor = structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())
    else:
        console_processor = structlog.processors.JSONRenderer()

    processors = base_processors + [console_processor]

    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Clear any existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Configure console logging
    console_handler = logging.StreamHandler(sys.stdout if debug else sys.stderr)
    console_handler.setLevel(getattr(logging, log_level))

    # Use appropriate formatter for console
    if log_format == "dev" or (sys.stderr.isatty() and log_format != "json"):
        console_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )
    else:
        console_formatter = JsonFormatter()

    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # Configure file logging if enabled
    if log_file:
        # Create file handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=file_rotation_mb * 1024 * 1024,  # Convert MB to bytes
            backupCount=file_backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(getattr(logging, log_level))

        # Always use JSON formatter for file logs
        file_formatter = JsonFormatter()
        file_handler.setFormatter(file_formatter)

        # Add handler to root logger
        root_logger.addHandler(file_handler)

        # Log the log file location
        logger = structlog.get_logger()
        logger.info(
            "Logging configured",
            log_file=str(log_path),
            log_level=log_level,
            log_format=log_format,
        )

    # Set log level on root logger
    root_logger.setLevel(getattr(logging, log_level))


class JsonFormatter(logging.Formatter):
    """Custom JSON formatter for structured logs."""

    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        try:
            # Base log dictionary
            log_dict = {
                "timestamp": datetime.utcfromtimestamp(record.created).isoformat()
                + "Z",
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
                "process": record.process,
                "thread": record.thread,
            }

            # Add exception info if present
            if record.exc_info:
                log_dict["exception"] = {
                    "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                    "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                    "traceback": self.formatException(record.exc_info)
                    if record.exc_info
                    else None,
                }

            # Add extra fields from structlog event_dict
            if self.include_extra and hasattr(record, "_record"):
                # Structlog adds the event_dict to _record
                event_dict = getattr(record._record, "event_dict", {})
                if event_dict:
                    # Filter out standard fields to avoid duplication
                    standard_fields = {
                        "timestamp",
                        "level",
                        "logger",
                        "message",
                        "event",
                    }
                    extra_fields = {
                        k: v for k, v in event_dict.items() if k not in standard_fields
                    }
                    if extra_fields:
                        log_dict["extra"] = extra_fields

            # Add any additional attributes set on the record
            if self.include_extra:
                extra_attrs = {}
                for key, value in record.__dict__.items():
                    if (
                        key not in log_dict
                        and not key.startswith("_")
                        and key
                        not in [
                            "name",
                            "msg",
                            "args",
                            "levelname",
                            "levelno",
                            "pathname",
                            "filename",
                            "module",
                            "exc_info",
                            "exc_text",
                            "stack_info",
                            "lineno",
                            "funcName",
                            "created",
                            "msecs",
                            "relativeCreated",
                            "thread",
                            "threadName",
                            "processName",
                            "process",
                            "getMessage",
                            "message",
                        ]
                    ):
                        extra_attrs[key] = value

                if extra_attrs:
                    log_dict["attributes"] = extra_attrs

            return json.dumps(log_dict, ensure_ascii=False, separators=(",", ":"))

        except Exception as e:
            # Fallback to simple format if JSON serialization fails
            return json.dumps(
                {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "level": "ERROR",
                    "logger": "JsonFormatter",
                    "message": f"Failed to format log record: {str(e)}",
                    "original_message": record.getMessage()
                    if hasattr(record, "getMessage")
                    else str(record),
                }
            )


def setup_session_logging(session_id: str, **kwargs) -> None:
    """Setup logging for a specific session."""
    setup_logging(session_id=session_id, **kwargs)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


def cleanup_old_logs(
    log_dir: Optional[Union[str, Path]] = None, keep_days: int = 7
) -> None:
    """Clean up log files older than specified days."""
    log_dir = Path(log_dir or "./logs")

    if not log_dir.exists():
        return

    cutoff_time = datetime.now().timestamp() - (keep_days * 24 * 60 * 60)

    for log_file in log_dir.glob("*.log*"):
        try:
            if log_file.stat().st_mtime < cutoff_time:
                log_file.unlink()
                logger = get_logger("logging.cleanup")
                logger.info(
                    "Removed old log file",
                    file=str(log_file),
                    age_days=(datetime.now().timestamp() - log_file.stat().st_mtime)
                    / (24 * 60 * 60),
                )
        except OSError as e:
            logger = get_logger("logging.cleanup")
            logger.warning(
                "Failed to remove old log file", file=str(log_file), error=str(e)
            )
