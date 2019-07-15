from loguru import logger

import sys

logger.remove(0)
#logger.add(sys.stderr, level="TRACE")
logger.add(sys.stderr, level="DEBUG")
#logger = logger.opt(ansi=True)
