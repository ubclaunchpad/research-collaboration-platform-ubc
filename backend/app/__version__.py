__version__ = "0.1.0"


def print_version():
    import logging

    logger = logging.getLogger(__name__)
    logger.info(f"backend code version: {__version__}")
    print(f"backend code version: {__version__}")


print_version()
