import logging
from logging import StreamHandler
from logging.handlers import TimedRotatingFileHandler

from config import config


def create_logger():
    logger = logging.getLogger()

    formatter = logging.Formatter(
        fmt="%(levelname)s|%(asctime)s|%(process)d|%(thread)d|%(filename)s:%(lineno)s|%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S")
    stream_handler = StreamHandler()
    file_handler = TimedRotatingFileHandler(filename=config.LOG_FILE_PATH, when='D', backupCount=10)

    if config.LOG_LEVEL == "DEBUG":
        handlers = [stream_handler]
    else:
        handlers = [stream_handler, file_handler]

    for handler in handlers:
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(config.LOG_LEVEL)



