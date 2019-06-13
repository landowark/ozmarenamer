#!/usr/bin/env python


import ozma
import logging
import logging.handlers

logger = logging.getLogger('ozma')
logger.setLevel(logging.DEBUG)
# create file handler which logs even debug messages
fh = logging.handlers.RotatingFileHandler('ozma.log', mode='a', maxBytes=100000, backupCount=3, encoding=None, delay=False)
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

ozma.main()