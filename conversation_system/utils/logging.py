"""Logging configuration and utilities."""

import sys
import structlog
from pathlib import Path
from datetime import datetime
import json
from typing import Any, Dict


def setup_logging(debug: bool = False, log_file: bool = True) -> None:
    """
    Configure structured logging for the application.
    
    Args:
        debug: Enable debug logging
        log_file: Whether to log to file in addition to console
    """
    # Configure log level
    log_level = "DEBUG" if debug else "INFO"
    
    # Create logs directory
    if log_file:
        log_dir = Path("./logs")
        log_dir.mkdir(exist_ok=True)
        log_path = log_dir / f"conversation_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
    
    # Configure processors
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    # Add development processors for console output
    if sys.stderr.isatty():
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors.append(structlog.processors.JSONRenderer())
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # PSEUDOCODE: Configure file logging if enabled
    # if log_file:
    #     import logging.handlers
    #     
    #     # Create file handler with rotation
    #     file_handler = logging.handlers.RotatingFileHandler(
    #         log_path,
    #         maxBytes=10 * 1024 * 1024,  # 10MB
    #         backupCount=7
    #     )
    #     
    #     # Configure JSON formatter for file
    #     file_formatter = JsonFormatter()
    #     file_handler.setFormatter(file_formatter)
    #     
    #     # Add handler to root logger
    #     logging.root.addHandler(file_handler)
    
    # Set log level
    import logging
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(message)s",
        stream=sys.stdout if debug else sys.stderr,
    )


class JsonFormatter(object):
    """Custom JSON formatter for structured logs."""
    
    def format(self, record: Any) -> str:
        """Format log record as JSON."""
        # PSEUDOCODE: Format log record
        # log_dict = {
        #     "timestamp": datetime.utcnow().isoformat(),
        #     "level": record.levelname,
        #     "logger": record.name,
        #     "message": record.getMessage(),
        # }
        # 
        # # Add extra fields
        # if hasattr(record, "event_dict"):
        #     log_dict.update(record.event_dict)
        # 
        # # Add exception info if present
        # if record.exc_info:
        #     log_dict["exception"] = self.format_exception(record.exc_info)
        # 
        # return json.dumps(log_dict)
        
        return "{}"