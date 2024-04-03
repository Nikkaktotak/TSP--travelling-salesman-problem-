import logging

logger = logging.getLogger("mat")
logger.setLevel(logging.DEBUG)

# Create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)
