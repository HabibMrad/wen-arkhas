import logging
import logging.handlers
import os
from datetime import datetime


class LoggerSetup:
    """Configure logging for the application"""

    @staticmethod
    def setup_logging(
        log_level: str = "INFO",
        log_dir: str = "logs",
        log_file: str = None
    ) -> logging.Logger:
        """
        Set up logging with both file and console handlers

        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_dir: Directory for log files
            log_file: Optional custom log file name

        Returns:
            Configured logger instance
        """
        # Create logs directory if it doesn't exist
        os.makedirs(log_dir, exist_ok=True)

        # Set up log file path
        if log_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = f"wen_arkhas_{timestamp}.log"

        log_path = os.path.join(log_dir, log_file)

        # Create logger
        logger = logging.getLogger("wen_arkhas")
        logger.setLevel(getattr(logging, log_level))

        # Clear existing handlers
        logger.handlers.clear()

        # Define log format
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # File handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(getattr(logging, log_level))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, log_level))
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        return logger


# Initialize root logger
def get_logger(name: str = "wen_arkhas") -> logging.Logger:
    """Get or create a named logger"""
    return logging.getLogger(name)


# Set up main logger on module import
main_logger = LoggerSetup.setup_logging()
