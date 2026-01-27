import json
import logging
import logging.config
import os
from datetime import datetime
from pathlib import Path

class JSONFormatter(logging.Formatter):
    """
    Formatter that outputs JSON strings after parsing the LogRecord.
    """
    def __init__(self, fmt=None, datefmt=None, style='%', validate=True):
        super().__init__(fmt, datefmt, style, validate)

    def format(self, record):
        """
        Format the specified record as text.
        """
        record.message = record.getMessage()
        
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)

        # Base log object
        log_record = {
            "timestamp": getattr(record, "asctime", datetime.utcnow().isoformat()),
            "level": record.levelname,
            "logger": record.name,
            "message": record.message,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        elif record.stack_info:
            log_record["stack"] = self.formatStack(record.stack_info)
            
        # Add extra fields (context) passed via extra={}
        # We filter out standard LogRecord attributes to avoid clutter
        standard_attrs = {
            "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
            "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
            "created", "msecs", "relativeCreated", "thread", "threadName",
            "processName", "process", "message", "asctime"
        }
        
        for key, value in record.__dict__.items():
            if key not in standard_attrs and not key.startswith("_"):
                # Add to a 'context' sub-object or root? 
                # Strategy said root for context or 'context' key.
                # Let's put specific extras at root for easier parsing (e.g. url, method)
                # or group them. Datadog prefers root attributes.
                log_record[key] = value

        return json.dumps(log_record, default=str)


def setup_logging(config_path="backend/logging_config.json", logs_dir="logs"):
    """
    Setup logging configuration from a JSON file.
    """
    path = Path(config_path)
    
    # Ensure logs directory exists
    Path(logs_dir).mkdir(parents=True, exist_ok=True)
    
    if path.exists():
        with open(path, 'rt') as f:
            config = json.load(f)
        
        # Apply configuration
        logging.config.dictConfig(config)
        print(f"✅ Logging configuration loaded from {config_path}")
    else:
        print(f"⚠️  Logging configuration file not found at {config_path}. Using default.")
        logging.basicConfig(level=logging.INFO)
