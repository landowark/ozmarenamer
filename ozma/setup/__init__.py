from argparse import ArgumentParser
from configparser import ConfigParser, ExtendedInterpolation
import os
import json
import logging
from .custom_loggers import GroupWriteRotatingFileHandler

logger = logging.getLogger("ozma.setup")


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


def get_cliarg():
    aParser = ArgumentParser()
    aParser.add_argument("filename", type=str, help="The file to be parsed.")
    aParser.add_argument("-v", "--verbose", help="Verbose mode on", action="store_true")
    aParser.add_argument("-e", "--extras", help="Scrape movies for extras.", action="store_true")
    args = aParser.parse_args().__dict__
    logger.debug("Arguments given: {}".format(args))
    if args['verbose']:
        handler = [item for item in logger.parent.handlers if item.name == "Stream"][0]
        handler.setLevel(logging.DEBUG)
    return args


def get_filepath():
    cli_args = get_cliarg()
    return cli_args['filename']


def get_config():
    cParser = ConfigParser(interpolation=ExtendedInterpolation())
    settings_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'settings.ini')
    cParser.read(settings_path)
    return {s:dict(cParser.items(s)) for s in cParser.sections()}['settings']


def get_media_types():
    with open(os.path.join(os.path.dirname(__file__), "media_extensions.json"), 'r') as f:
        types = json.load(f)
    return types

def get_allowed_extensions():
    types_dict = get_media_types()
    return [item for sublist in [types_dict[item] for item in types_dict] for item in sublist]


def setup_logger():
    logger = logging.getLogger('ozma')
    logger.setLevel(logging.DEBUG)
    # create file handler which logs even debug messages
    fh = GroupWriteRotatingFileHandler(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'ozma.log'), mode='a',
                                       maxBytes=100000, backupCount=3, encoding=None, delay=False)
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
    return logger
    # sl = StreamToLogger(stderr_logger, logging.ERROR)
    # sys.stderr = sl