from argparse import ArgumentParser
from configparser import ConfigParser, ExtendedInterpolation
import os
import json


def get_cliarg():
    aParser = ArgumentParser()
    aParser.add_argument("filename", type=str, help="The file to be parsed.")
    args = aParser.parse_args()
    return args.__dict__


def get_params():
    cli_args = get_cliarg()
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