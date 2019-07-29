import os
import re
import wordninja as wn
from ..setup import get_media_types
import logging
from datetime import datetime
import shutil

logger = logging.getLogger("ozma.tools")
strip_list = ["HDTV", "x264", "x265", "h264", "720p", "1080p", "PROPER", "WEB", "EXTENDED", "DVDRip", "HC",
              "HDRip", "XviD", "AC3", "BRRip"]

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
    filename = re.sub(re.compile(r'\[.*\]'), "", filename)
    for word in strip_list:
        regex = re.compile(r'{}[^\s]*'.format(word), re.IGNORECASE)
        filename = re.sub(regex, "", filename)
    # print("Post strip list: {}".format(filename))
    season = get_season(filename)
    episode = get_episode(filename)
    if not season and not episode:
        logger.debug("No season or episode found. Attempting dxdd method.")
        # print("No season or episode found. Attempting dxdd method.")
        season, episode = get_season_episode_dxdd(filename)
        filename = filename.replace("{}x{}".format(season, episode), "")
        filename = filename.replace("{}x{}".format(season, episode), "")
    # print("Post dxdd method: {}".format(filename))
    if not season and not episode:
        logger.debug("No season or episode found. Attempting date method.")
        # print("No season or episode found. Attempting date method.")
        season = get_episode_date(filename)
        episode = None
        if season:
            filename = filename.split(season)[0].strip()
            try:
                season = datetime.strptime(season, "%Y %m %d").date()
            except TypeError:
                logger.debug("No season found.")
    # print("Post date method: {}".format(filename))
    if season:
        try:
            filename = filename.replace(season.upper(), "")
            filename = filename.replace(season.lower(), "")
        except TypeError:
            filename = filename.replace(season.strftime("%Y %m %d"), "")
        except AttributeError:
            filename = filename.replace(season.strftime("%Y %m %d"), "")
        try:
            season = int(season.strip("S"))
        except ValueError:
            season = season
        except AttributeError:
            season = season
    # print("Post season: {}".format(filename))
    if episode:
        filename = filename.replace(episode.upper(), "")
        filename = filename.replace(episode.lower(), "")
        episode = int(episode.strip("E"))
    # print("Post episode: {}".format(filename))
    disc = get_disc(filename)
    if disc:
        filename = filename.replace(disc, "")
        disc = int(disc.strip("D"))
    # print("Post disc: {}".format(filename))
    year = check_for_year(filename)
    if year:
        filename = filename.replace(year, "")
    # print("Post year: {}".format(filename))
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
    regex = re.compile(r"^(The|A|An)\s")
    title = re.split(regex, filename)[1:]
    if len(title) > 0:
        title.append(", ")
        title.append(title.pop(0))
        title = "".join(title).strip()
        return title
    else:
        return filename


def extract_files_if_folder(dir_path):
    types_dict = get_media_types()
    allowed_ext = [item for sublist in [types_dict[item] for item in types_dict] for item in sublist]
    files = [os.path.join(dir_path, item) for item in os.listdir(dir_path) if os.path.splitext(item)[1][1:] in allowed_ext]
    dirs = [item[0] for item in os.walk(dir_path)]
    files = files + dirs
    files.remove(dir_path)
    return files


def remove_temp_files():
    logger.debug("Removing temporary files.")
    shutil.rmtree("/tmp/pytvdbapi", ignore_errors=True)