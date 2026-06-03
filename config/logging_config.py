"""
Centralized logging configuration for CTOLens
Provides structured file-based logging with rotation and proper formatting
"""

import os
import json
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record):
        """Format log record as JSON with consistent structure"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process_id": os.getpid(),
            "thread_name": record.threadName
        }
        
        # Add extra context if available
        extra_fields = ['user_id', 'workspace_id', 'assignment_id', 'request_id', 
                       'connector_type', 'operation', 'duration_ms', 'status_code']
        
        for field in extra_fields:
            if hasattr(record, field):
                log_entry[field] = getattr(record, field)
        
        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
            
        # Add stack trace for errors
        if record.levelno >= logging.ERROR and hasattr(record, 'stack_info'):
            log_entry["stack_trace"] = record.stack_info
            
        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging(
    log_level: str = None,
    log_dir: str = None,
    app_name: str = "ctolens",
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 10
):
    """
    Setup centralized logging configuration
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files (defaults to logs/)
        app_name: Application name for log files
        max_file_size: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
    """
    
    # Configure log level
    log_level = log_level or os.getenv("LOG_LEVEL", "INFO")
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configure log directory
    if log_dir is None:
        # Use Railway volume mount in production, local logs/ in development
        if os.getenv("RAILWAY_ENVIRONMENT"):
            log_dir = "/data/logs"
        else:
            log_dir = "logs"
    
    log_dir = Path(log_dir)
    
    # Create log directory with fallback for read-only systems
    try:
        log_dir.mkdir(exist_ok=True, parents=True)
    except (OSError, PermissionError) as e:
        # Fallback to local directory if Railway volume mount fails
        print(f"Warning: Could not create log directory {log_dir}: {e}")
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True, parents=True)
        print(f"Using fallback log directory: {log_dir}")
    
    # Configure log file paths
    main_log_file = log_dir / f"{app_name}.log"
    error_log_file = log_dir / f"{app_name}-errors.log"
    
    # Clear any existing handlers to prevent duplication
    logging.getLogger().handlers = []
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # JSON formatter for structured logging
    json_formatter = JSONFormatter()
    
    # Main log file handler (all levels)
    main_handler = logging.handlers.RotatingFileHandler(
        main_log_file,
        maxBytes=max_file_size,
        backupCount=backup_count,
        encoding='utf-8'
    )
    main_handler.setLevel(numeric_level)
    main_handler.setFormatter(json_formatter)
    root_logger.addHandler(main_handler)
    
    # Error log file handler (errors and critical only)
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_file,
        maxBytes=max_file_size,
        backupCount=backup_count,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(json_formatter)
    root_logger.addHandler(error_handler)
    
    # Console handler for development (only if not in production)
    if not os.getenv("RAILWAY_ENVIRONMENT"):
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Simple format for console
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    # Configure specific loggers to prevent spam
    # Reduce noise from third-party libraries
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    
    # Log startup information
    startup_logger = logging.getLogger("ctolens.startup")
    startup_logger.info(
        "Logging configured successfully",
        extra={
            "log_level": log_level,
            "log_dir": str(log_dir),
            "main_log": str(main_log_file),
            "error_log": str(error_log_file),
            "environment": os.getenv("RAILWAY_ENVIRONMENT", "development")
        }
    )
    
    return {
        "log_dir": str(log_dir),
        "main_log": str(main_log_file),
        "error_log": str(error_log_file),
        "level": log_level
    }


def get_logger(name: str = None):
    """
    Get a logger instance with proper configuration
    
    Args:
        name: Logger name (defaults to calling module)
    """
    if name is None:
        import inspect
        frame = inspect.currentframe().f_back
        name = frame.f_globals.get('__name__', 'unknown')
    
    return logging.getLogger(name)


def log_function_call(func_name: str, **kwargs):
    """
    Helper function to log function calls with context
    
    Args:
        func_name: Name of the function being called
        **kwargs: Additional context to log
    """
    logger = get_logger("ctolens.function_calls")
    logger.info(
        f"Function called: {func_name}",
        extra={
            "function": func_name,
            "operation": "function_call",
            **kwargs
        }
    )


def log_api_request(method: str, path: str, status_code: int = None, duration_ms: float = None, **kwargs):
    """
    Helper function to log API requests
    
    Args:
        method: HTTP method
        path: Request path
        status_code: HTTP status code
        duration_ms: Request duration in milliseconds
        **kwargs: Additional context
    """
    logger = get_logger("ctolens.api")
    logger.info(
        f"{method} {path}",
        extra={
            "operation": "api_request",
            "http_method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": duration_ms,
            **kwargs
        }
    )


def log_error(message: str, exception: Exception = None, **kwargs):
    """
    Helper function to log errors with proper context
    
    Args:
        message: Error message
        exception: Exception object if available
        **kwargs: Additional context
    """
    logger = get_logger("ctolens.errors")
    
    extra = {
        "operation": "error",
        **kwargs
    }
    
    if exception:
        extra["exception_type"] = type(exception).__name__
        extra["exception_message"] = str(exception)
        logger.error(message, extra=extra, exc_info=exception)
    else:
        logger.error(message, extra=extra)


def log_performance(operation: str, duration_ms: float, **kwargs):
    """
    Helper function to log performance metrics
    
    Args:
        operation: Operation name
        duration_ms: Duration in milliseconds
        **kwargs: Additional context
    """
    logger = get_logger("ctolens.performance")
    logger.info(
        f"Performance: {operation} took {duration_ms:.2f}ms",
        extra={
            "operation": "performance",
            "performance_operation": operation,
            "duration_ms": duration_ms,
            **kwargs
        }
    )