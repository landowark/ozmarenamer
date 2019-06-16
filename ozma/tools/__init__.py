import os
import re
import wordninja as wn
from ..setup import get_media_types
import logging
from datetime import datetime

logger = logging.getLogger("ozma.tools")
strip_list = ["HDTV", "x264", "x265", "h264", "720p", "1080p", "PROPER", "WEB", "EXTENDED"]

def split_file_name(filepath):
    return os.path.basename(filepath)

def get_extension(filepath):
    return os.path.splitext(filepath)[1][1:]

def remove_extension(filepath):
    return os.path.splitext(filepath)[0]


def get_episode_date(filename):
    season = re.compile(r'((19\d{2}|20\d{2})\s(0|1)?\d\s[0,1,2,3]?\d)')
    try:
        if isinstance(re.findall(season, filename)[0], tuple):
            return re.findall(season, filename)[0][0]
        else:
            return re.findall(season, filename)[0]
    except:
        return None


def get_parsible_file_name(filepath):
    # remove season number
    filename = remove_extension(split_file_name(filepath))
    filename = filename.replace(".", " ")
    for word in strip_list:
        regex = re.compile(r'{}[^\s]*'.format(word), re.IGNORECASE)
        filename = re.sub(regex, "", filename)
    season = get_season(filename)
    episode = get_episode(filename)
    if not season and not episode:
        season, episode = get_season_episode_dxdd(filename)
        filename = filename.replace("{}x{}".format(season, episode), "")
    if not season and not episode:
        season = get_episode_date(filename)
        episode = None
        filename = filename.split(season)[0].strip()
        season = datetime.strptime(season, "%Y %m %d").date()
    if season:
        try:
            filename = filename.replace(season, "")
        except TypeError:
            filename = filename.replace(season.strftime("%Y %m %d"), "")
        try:
            season = int(season.strip("S"))
        except ValueError:
            season = season
        except AttributeError:
            season = season
    if episode:
        filename = filename.replace(episode, "")
        episode = int(episode.strip("E"))
    disc = get_disc(filename)
    if disc:
        filename = filename.replace(disc, "")
        disc = int(disc.strip("D"))
    year = check_for_year(filename)
    if year:
        filename = filename.replace(year, "")
    filename = " ".join(wn.split(filename)).title()
    if year: filename = "{filename} ({year})".format(filename=filename, year=year)
    logger.debug("Using filename={}, season={}, episode={}, disc={}".format(filename, str(season), str(episode), str(disc)))
    return filename, season, episode, disc


def get_season(filename):
    season = re.compile(r's(?:eason)?\d{1,2}', re.IGNORECASE)
    try:
        return re.findall(season, filename)[0].upper()
    except:
        return None

def get_episode(filename):
    episode = re.compile(r'e(?:pisode)?\d{1,2}', re.IGNORECASE)
    try:
        return re.findall(episode, filename)[0].upper()
    except:
        return None

def get_season_episode_dxdd(filename):
    regex = re.compile(r'\d{1,2}x\d{1,2}', re.IGNORECASE)
    try:
        both = re.findall(regex, filename)
        both = both[0].split('x')
        season = both[0]
        episode = both[1]
        return season, episode
    except:
        return None, None

def get_disc(filename):
    # for use with dvd rips
    disc = re.compile(r'd(?:isc)?\d{1,2}', re.IGNORECASE)
    try:
        return re.findall(disc, filename)[0].upper()
    except:
        return None

def get_media_type(extenstion):
    types = get_media_types()
    for type in types.keys():
        if extenstion in types[type]:
            return type


def check_for_year(filename):
    year = re.compile(r'(20\d{2}|19\d{2})')
    try:
        return re.findall(year, filename)[0].upper()
    except:
        return None


def move_article_to_end(filename):
    regex = re.compile(r"^(The|A|An)")
    title = re.split(regex, filename)[1:]
    if len(title) > 0:
        title.append(", ")
        title.append(title.pop(0))
        title = "".join(title).strip()
        return title
    else:
        return filename


