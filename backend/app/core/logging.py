import logging

from pythonjsonlogger import jsonlogger


class SensitiveDataFilter(logging.Filter):
    def filter(self, record):
        # Basic redaction, extend as needed
        if hasattr(record, "message") and isinstance(record.message, str):
            for secret in ["SECRET", "KEY", "TOKEN", "PASSWORD"]:
                if secret in record.message.upper():
                    record.message = "***REDACTED***"
        return True

def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    logHandler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(name)s %(message)s')
    logHandler.setFormatter(formatter)
    
    logger.addHandler(logHandler)
    logger.addFilter(SensitiveDataFilter())

setup_logging()
