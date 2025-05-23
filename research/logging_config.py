"""
Logging configuration for SolVolumeBot research layer.
Provides structured logging with file rotation and multiple output formats.
"""

import os
import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging"""
    
    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra
        
    def format(self, record: logging.LogRecord) -> str:
        # Base format
        timestamp = datetime.fromtimestamp(record.created).isoformat()
        
        # Build structured message
        log_data = {
            'timestamp': timestamp,
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add extra fields if present
        if self.include_extra and hasattr(record, '__dict__'):
            extra_fields = {
                k: v for k, v in record.__dict__.items() 
                if k not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                           'filename', 'module', 'lineno', 'funcName', 'created', 'msecs', 
                           'relativeCreated', 'thread', 'threadName', 'processName', 
                           'process', 'stack_info', 'exc_info', 'exc_text', 'message']
            }
            if extra_fields:
                log_data['extra'] = extra_fields
                
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
            
        # Format as key=value pairs for easy parsing
        formatted_parts = []
        for key, value in log_data.items():
            if isinstance(value, dict):
                # Flatten nested dict
                for sub_key, sub_value in value.items():
                    formatted_parts.append(f"{key}.{sub_key}={sub_value}")
            else:
                formatted_parts.append(f"{key}={value}")
                
        return " | ".join(formatted_parts)


class TradingLoggerAdapter(logging.LoggerAdapter):
    """Logger adapter for trading-specific context"""
    
    def __init__(self, logger: logging.Logger, context: Optional[Dict[str, Any]] = None):
        super().__init__(logger, context or {})
        
    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        # Add trading context to all log messages
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
            
        kwargs['extra'].update(self.extra)
        return msg, kwargs
        
    def trade_signal(self, signal_type: str, price: float, volume_drop: float, 
                    rsi: float, **kwargs):
        """Log trade signal with structured data"""
        self.info(
            f"TRADE_SIGNAL: {signal_type}",
            extra={
                'signal_type': signal_type,
                'sol_price': price,
                'volume_drop_pct': volume_drop,
                'rsi': rsi,
                **kwargs
            }
        )
        
    def api_call(self, api_name: str, endpoint: str, status_code: int, 
                response_time_ms: float, **kwargs):
        """Log API call with performance metrics"""
        level = logging.WARNING if status_code >= 400 else logging.DEBUG
        self.log(
            level,
            f"API_CALL: {api_name} {endpoint}",
            extra={
                'api_name': api_name,
                'endpoint': endpoint,
                'status_code': status_code,
                'response_time_ms': response_time_ms,
                **kwargs
            }
        )
        
    def data_collection(self, data_type: str, record_count: int, 
                       collection_time_ms: float, **kwargs):
        """Log data collection metrics"""
        self.info(
            f"DATA_COLLECTION: {data_type}",
            extra={
                'data_type': data_type,
                'record_count': record_count,
                'collection_time_ms': collection_time_ms,
                **kwargs
            }
        )


def setup_logging(config: Dict[str, Any]) -> TradingLoggerAdapter:
    """Setup logging configuration"""
    
    log_config = config.get('logging', {})
    log_level = getattr(logging, log_config.get('level', 'INFO').upper())
    log_format = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log_file = log_config.get('file', 'logs/solvolume_bot.log')
    max_size_mb = log_config.get('max_size_mb', 100)
    backup_count = log_config.get('backup_count', 5)
    console_output = log_config.get('console', True)
    
    # Create logs directory
    log_path = Path(log_file)
    log_path.parent.mkdir(exist_ok=True)
    
    # Get root logger for the application
    logger = logging.getLogger('solvolume_bot')
    logger.setLevel(log_level)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # File handler with rotation
    if log_file:
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=max_size_mb * 1024 * 1024,  # Convert MB to bytes
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        
        # Use structured formatter for file output
        file_formatter = StructuredFormatter(include_extra=True)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        
        # Use simple formatter for console output
        console_formatter = logging.Formatter(log_format)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    # Create adapter with trading context
    context = {
        'component': 'research_layer',
        'version': '1.0.0',
        'environment': os.getenv('ENVIRONMENT', 'development')
    }
    
    adapter = TradingLoggerAdapter(logger, context)
    
    # Log startup
    adapter.info("Logging system initialized", extra={
        'log_level': log_level,
        'log_file': str(log_file) if log_file else None,
        'console_output': console_output
    })
    
    return adapter


def configure_third_party_logging():
    """Configure logging for third-party libraries"""
    
    # Reduce noise from HTTP libraries
    logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
    logging.getLogger('requests.packages.urllib3').setLevel(logging.WARNING)
    
    # Set pandas to only show warnings
    logging.getLogger('pandas').setLevel(logging.WARNING)
    
    # Limit other noisy loggers
    for logger_name in ['chardet.charsetprober', 'asyncio']:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


class PerformanceTimer:
    """Context manager for measuring and logging performance"""
    
    def __init__(self, logger: TradingLoggerAdapter, operation: str, **context):
        self.logger = logger
        self.operation = operation
        self.context = context
        self.start_time = None
        
    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.debug(f"Starting {self.operation}", extra=self.context)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration_ms = (datetime.now() - self.start_time).total_seconds() * 1000
            
            if exc_type:
                self.logger.error(
                    f"Failed {self.operation}",
                    extra={
                        'duration_ms': duration_ms,
                        'error': str(exc_val),
                        **self.context
                    }
                )
            else:
                self.logger.debug(
                    f"Completed {self.operation}",
                    extra={
                        'duration_ms': duration_ms,
                        **self.context
                    }
                )


# Convenience function for getting logger in other modules
def get_logger(name: str = None) -> TradingLoggerAdapter:
    """Get logger instance for a module"""
    base_logger = logging.getLogger(name or 'solvolume_bot')
    return TradingLoggerAdapter(base_logger)