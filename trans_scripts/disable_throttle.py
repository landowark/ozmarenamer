#!/home/landon/Scripts/ozmarenamer/venv/bin/python

from transmission_rpc import Client, DEFAULT_PORT
from ozma.setup import get_config
import logging
import os

configs = get_config()
logger = logging.getLogger("ozma.disable_throttle")
try:
    c = Client(port=DEFAULT_PORT, user=configs['transmission_user'], password=configs['transmission_pass'])
except Exception as e:
    logger.error(f"Error in getting transmission client: {e}")
try:
    completed_dir = configs['watch_dir']
except Exception as e:
    logger.error(f"Error in finding completed dir in settings: {e}")

logger.info(f"Disabling throttling...")
c.session.alt_speed_enabled = False