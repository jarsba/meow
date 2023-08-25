from pydantic import BaseModel
import typing as t


class LogConfig(BaseModel):
    """Logging configuration"""

    LOGGER_NAME: str = "meow"
    LOG_FORMAT: str = "%(levelprefix)s | %(asctime)s | %(message)s"
    LOG_LEVEL: str = "DEBUG"

    # Logging config
    version: int = 1
    disable_existing_loggers: bool = False
    formatters: t.Mapping = {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": LOG_FORMAT,
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    }
    handlers: t.Mapping = {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
    }
    loggers: t.Mapping = {
        LOGGER_NAME: {"handlers": ["default"], "level": LOG_LEVEL},
    }
