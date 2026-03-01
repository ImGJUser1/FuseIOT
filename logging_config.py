import logging
import sys
from typing import Optional, Dict, Any
from pathlib import Path

import structlog


def configure_logging(
    level: str = "INFO",
    json_format: bool = False,
    log_file: Optional[str] = None,
    console: bool = True
) -> None:
    """
    Configure structured logging for FuseIoT.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        json_format: Output JSON for production
        log_file: Optional file path for logs
        console: Enable console output
    """
    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.ExtraAdder(),
    ]
    
    if json_format:
        # Production: JSON format
        formatters = {
            "json": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": structlog.processors.JSONRenderer(),
                "foreign_pre_chain": shared_processors,
            }
        }
        handlers = {}
        if console:
            handlers["console"] = {
                "class": "logging.StreamHandler",
                "formatter": "json",
                "stream": sys.stdout,
            }
    else:
        # Development: pretty console output
        shared_processors.extend([
            structlog.stdlib.filter_by_level,
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
        ])
        
        formatters = {
            "colored": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": structlog.dev.ConsoleRenderer(colors=True),
                "foreign_pre_chain": shared_processors,
            }
        }
        handlers = {}
        if console:
            handlers["console"] = {
                "class": "logging.StreamHandler",
                "formatter": "colored",
                "stream": sys.stdout,
            }
    
    if log_file:
        handlers["file"] = {
            "class": "logging.FileHandler",
            "filename": log_file,
            "formatter": "json" if json_format else "colored",
        }
    
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": formatters,
        "handlers": handlers,
        "loggers": {
            "fuseiot": {
                "handlers": list(handlers.keys()),
                "level": level,
                "propagate": False,
            },
        },
    }
    
    logging.config.dictConfig(logging_config)
    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level)),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: Optional[str] = None) -> structlog.stdlib.BoundLogger:
    """Get a structured logger."""
    return structlog.get_logger(f"fuseiot.{name}" if name else "fuseiot")