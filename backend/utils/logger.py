# Copyright 2026 smart-ebocr Contributors
# SPDX-License-Identifier: Apache-2.0

"""Logging configuration and utilities for 电费分析工具 backend.

Provides structured logging with:
- Rotating file handlers for app, request, and error logs
- Environment-based log levels (DEBUG for dev, WARNING for prod)
- Consistent log format with timestamps and module info
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


# Log directory - relative to backend directory
LOG_DIR = Path(__file__).parent.parent / 'logs'
LOG_DIR.mkdir(exist_ok=True)

# Log file paths
APP_LOG = LOG_DIR / 'app.log'
REQUEST_LOG = LOG_DIR / 'request.log'
ERROR_LOG = LOG_DIR / 'error.log'
OCR_LOG = LOG_DIR / 'ocr.log'

# Log format
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# Max log file size: 10MB
MAX_BYTES = 10 * 1024 * 1024
# Keep 5 backup files
BACKUP_COUNT = 5


def get_log_level():
    """Get log level based on FLASK_ENV environment variable.

    Returns:
        logging.DEBUG for development environment
        logging.WARNING for production environment
    """
    env = os.environ.get('FLASK_ENV', 'development')
    return logging.DEBUG if env == 'development' else logging.WARNING


def setup_logger(name, log_file, level=None):
    """Set up a logger with rotating file handler.

    Args:
        name: Logger name (usually __name__ of the calling module)
        log_file: Path to log file
        level: Log level (defaults to get_log_level())

    Returns:
        logging.Logger: Configured logger instance
    """
    if level is None:
        level = get_log_level()

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # File handler with rotation
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setLevel(level)

    # Console handler for development
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if level == logging.DEBUG else logging.INFO)

    # Formatter
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def get_logger(name):
    """Get a logger instance for the given module name.

    Usage:
        from backend.utils.logger import get_logger
        logger = get_logger(__name__)
        logger.info('Something happened')

    Args:
        name: Logger name (usually __name__ of the calling module)

    Returns:
        logging.Logger: Logger instance for app.log
    """
    return setup_logger(name, APP_LOG)


def get_request_logger():
    """Get the request logger for HTTP request/response logging.

    Returns:
        logging.Logger: Logger instance for request.log
    """
    logger = logging.getLogger('request')
    if not logger.handlers:
        return setup_logger('request', REQUEST_LOG)
    return logger


def get_error_logger():
    """Get the error logger for exception and error logging.

    Returns:
        logging.Logger: Logger instance for error.log
    """
    logger = logging.getLogger('error')
    if not logger.handlers:
        return setup_logger('error', ERROR_LOG, level=logging.ERROR)
    return logger


def get_ocr_logger():
    """Get the OCR process logger for detailed OCR pipeline logging.

    Writes to a dedicated ocr.log file for easier debugging of OCR issues.

    Returns:
        logging.Logger: Logger instance for ocr.log
    """
    logger = logging.getLogger('ocr')
    if not logger.handlers:
        return setup_logger('ocr', OCR_LOG)
    return logger


def log_exception(logger, exc, context=None):
    """Log an exception with context information.

    Args:
        logger: Logger instance
        exc: Exception object
        context: Optional context dictionary with additional info
    """
    error_logger = get_error_logger()
    msg = f"Exception: {type(exc).__name__}: {str(exc)}"
    if context:
        msg += f" | Context: {context}"
    error_logger.error(msg, exc_info=True)
    logger.error(msg, exc_info=True)