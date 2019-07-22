#!/usr/bin/env python

import os
import ozma
import logging
import logging.handlers
import sys
from contextlib import redirect_stderr


class StreamToLogger(object):
   """
   Fake file-like stream object that redirects writes to a logger instance.
   """
   def __init__(self, logger, log_level=logging.INFO):
      self.logger = logger
      self.log_level = log_level
      self.linebuf = ''

   def write(self, buf):
      for line in buf.rstrip().splitlines():
         self.logger.log(self.log_level, line.rstrip())

logger = logging.getLogger('ozma')
logger.setLevel(logging.DEBUG)
# create file handler which logs even debug messages
fh = logging.handlers.RotatingFileHandler(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ozma.log'), mode='a', maxBytes=100000, backupCount=3, encoding=None, delay=False)
fh.setLevel(logging.DEBUG)
fh.name = "File"
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.WARNING)
ch.name = "Stream"
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(fh)
logger.addHandler(ch)
stderr_logger = logging.getLogger('STDERR')
sl = StreamToLogger(stderr_logger, logging.ERROR)
sys.stderr = sl
logger.debug("Starting Run.")
ozma.main()