import logging


def get_logger(name="root"):
    logger = logging.Logger(name)

    log_handler = logging.StreamHandler()
    log_formatter = logging.Formatter(
        "%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s"
    )
    log_handler.setFormatter(log_formatter)
    logger.addHandler(log_handler)
    return logger
