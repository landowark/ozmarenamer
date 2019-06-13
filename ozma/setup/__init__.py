from argparse import ArgumentParser
from configparser import ConfigParser, ExtendedInterpolation
import os
import json
import logging

logger = logging.getLogger("ozma.setup")

def get_cliarg():
    aParser = ArgumentParser()
    aParser.add_argument("filename", type=str, help="The file to be parsed.")
    aParser.add_argument("-v", "--verbose", help="Verbose mode on", action="store_true")
    args = aParser.parse_args()

    logger.debug(args.__str__())
    return args.__dict__


def get_params():
    cli_args = get_cliarg()
    if cli_args['verbose']:
        handler = [item for item in logger.parent.handlers if item.name == "Stream"][0]
        handler.setLevel(logging.DEBUG)
    del cli_args['filename']
    return cli_args


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