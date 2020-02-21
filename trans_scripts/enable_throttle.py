#!/home/landon/Scripts/ozmarenamer/venv/bin/python

import sys
sys.path.append("..") # Adds higher directory to python modules path.
from transmission_rpc import Client, DEFAULT_PORT
from ozma.setup import get_config
import logging
import os

configs = get_config()
logger = logging.getLogger("ozma.enable_throttle")
try:
    c = Client(port=DEFAULT_PORT, user=configs['transmission_user'], password=configs['transmission_pass'])
except Exception as e:
    logger.error(f"Error in getting transmission client: {e}")
try:
    completed_dir = configs['watch_dir']
except Exception as e:
    logger.error(f"Error in finding completed dir in settings: {e}")

logger.info(f"Enabling throttling...")
c.session.alt_speed_enabled = True