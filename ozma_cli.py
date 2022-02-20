#!/home/landon/Scripts/ozmarenamer/venv/bin/python

import ozma
from ozma.setup import get_cliarg
import logging
import getpass

logger = logging.getLogger("ozma.cli")

params = get_cliarg()
logger.debug(f"Command line called by {getpass.getuser()}.")
logger.debug(f"Command line parameters: {params}")
ozma.main(params)