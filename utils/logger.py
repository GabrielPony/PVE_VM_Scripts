import logging
import colorlog
from typing import Optional

# Configure logging
class Logger:
    _instance: Optional['Logger'] = None
    _logger: Optional[logging.Logger] = None

    def __new__(cls) -> 'Logger':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Ensure initialization occurs only once
        if self._logger is None:
            self._setup_logger()

    def _setup_logger(self):
        """Setup colored logging"""
        # Create logger
        self._logger = logging.getLogger('ProxmoxManager')
        self._logger.setLevel(logging.INFO)

        # Clear existing handlers
        if self._logger.handlers:
            self._logger.handlers.clear()

        # Console handler (with colors)
        console_handler = colorlog.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # File handler (without colors)
        file_handler = logging.FileHandler('./logs/vm_creation.log')
        file_handler.setLevel(logging.INFO)

        # Color scheme
        colors = {
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }

        # Console formatter (with colors)
        console_formatter = colorlog.ColoredFormatter(
            '%(log_color)s%(asctime)s - %(levelname)s - %(message)s',
            log_colors=colors,
            reset=True,
            style='%'
        )

        # File formatter (without colors)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )

        # Set formatters
        console_handler.setFormatter(console_formatter)
        file_handler.setFormatter(file_formatter)

        # Add handlers
        self._logger.addHandler(console_handler)
        self._logger.addHandler(file_handler)

    @classmethod
    def get_logger(cls) -> logging.Logger:
        """Get logger instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance._logger
