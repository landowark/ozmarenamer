#!/usr/bin/env python

import ozma
from ozma.setup import get_cliarg
import logging

logger = logging.getLogger("ozma.cli")

logger.debug("Command line called.")
params = get_cliarg()
logger.debug(f"Command line parameters: {params}")
ozma.main(params)