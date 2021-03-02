import logging
import os
from logging.handlers import TimedRotatingFileHandler


LOGS_DIR = "/logs"


def get_logger(name="root", logs_dir=LOGS_DIR):
    logger = logging.Logger(name)
    log_formatter = logging.Formatter(
        "%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s"
    )

    if not os.path.isdir(LOGS_DIR):
        os.mkdir(LOGS_DIR)

    file_handler = TimedRotatingFileHandler(
        os.path.join(logs_dir, f"oakoakbot.log"), when="midnight", interval=1
    )
    file_handler.suffix = "%Y%m%d"
    file_handler.setFormatter(log_formatter)
    logger.addHandler(file_handler)

    log_handler = logging.StreamHandler()
    log_handler.setFormatter(log_formatter)
    logger.addHandler(log_handler)
    return logger
