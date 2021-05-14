import os
import re
import wordninja as wn
from ..setup import get_media_types, get_allowed_extensions
import logging
from datetime import datetime
import shutil
import unicodedata
import exiftool

logger = logging.getLogger("ozma.tools")
strip_list = ["HDTV", "x264", "x265", "h264", "720p", "1080p", "PROPER", "WEB", "EXTENDED", "DVDRip", "HC",
              "HDRip", "XviD", "AC3", "BRRip", "Bluray", "Internal", "AAC", "YIFY", "UNCUT"]
rejected_filenames = ['sample']

def split_file_name(filepath):
    return os.path.basename(filepath)

def get_extension(filepath):
    return os.path.splitext(filepath)[1][1:]

def remove_extension(filepath):
    return os.path.splitext(filepath)[0]


def get_episode_date(filename):
    season = re.compile(r'((19\d{2}|20\d{2})\s(0|1)?\d\s[0,1,2,3]?\d)')
    try:
        # check if season is a tuple, if yes get first entry
        if isinstance(re.findall(season, filename)[0], tuple):
            return re.findall(season, filename)[0][0]
        # if not return whole thing.
        else:
            return re.findall(season, filename)[0]
    except:
        return None


def get_parsible_video_name(filepath:str):
    # remove season number
    filename = remove_extension(split_file_name(filepath))
    filename = filename.replace(".", " ")
    # non-greedy regex to remove things in square brackets
    filename = re.sub(re.compile(r'\[.*?\]'), "", filename)
    for word in strip_list:
        # regex to remove anything in strip list
        regex = re.compile(r'{}[^\s]*'.format(word), re.IGNORECASE)
        filename = re.sub(regex, "", filename)
    # Seperate method to get season with regex
    season = get_season(filename)
    # Seperate method to get season with regex
    episode = get_episode(filename)
    logger.debug(f"Season: {season}, Episode: {episode}")
    if season and episode:
        # set string containing season/episode with S00E00 format
        seasep = season + episode
        logger.debug(f"Seasep = {seasep}")
        filename = filename.split(seasep)[0].strip()
    # if main method of determining Season/episode didn't work, try dxdd method
    if not season and not episode:
        logger.debug("No season or episode found. Attempting dxdd method.")
        season, episode = get_season_episode_dxdd(filename)
        if season and episode:
            seasep = f"{season}x{episode}"
            filename = filename.split(seasep)[0].strip()
    # if dxdd method didn't work, try with date.
    if not season and not episode:
        logger.debug("No season or episode found. Attempting date method.")
        season = get_episode_date(filename)
        episode = None
        if season:
            filename = filename.split(season)[0].strip()
            try:
                season = datetime.strptime(season, "%Y %m %d").date()
            except TypeError:
                logger.debug("No season found.")
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
    if episode:
        filename = filename.replace(episode.upper(), "")
        filename = filename.replace(episode.lower(), "")
        episode = int(episode.strip("E"))
    # Check for a disc number for whatever reason.
    disc = get_disc(filename)
    if disc:
        filename = filename.replace(disc, "")
        disc = int(disc.strip("D"))
    # Check for a year, should be run after the episode year check.
    year = check_for_year(filename)
    if year:
        filename = filename.replace(year, "")
    # Use word ninja to split apart words that maybe joined due to whitespace errors
    filename = " ".join(wn.split(filename)).title()
    if year: filename = f"{filename} ({year})"
    if filename.lower() in rejected_filenames:
        logger.warning(f"Found a rejected filename: {filename}. Disregarding.")
        filename = None
    logger.debug(f"Using filename={filename}, season={season}, episode={episode}, disc={disc}")
    return filename, season, episode, disc


def get_parsible_audio_name(filepath:str):
    # remove season number
    filename = remove_extension(split_file_name(filepath))
    filename = filename.replace(".", " ")
    # non-greedy regex to remove things in square brackets
    filename = re.sub(re.compile(r'\[.*?\]'), "", filename)
    for word in strip_list:
        # regex to remove anything in strip list
        regex = re.compile(r'{}[^\s]*'.format(word), re.IGNORECASE)
        filename = re.sub(regex, "", filename)
    title, artist = get_title_artist(filename)
    return filename, title, artist


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


def get_title_artist(filename:str):
    # for music
    title = filename.split("-")[1].strip()
    logger.debug(f"Got {title} for title.")
    artist = filename.split("-")[0].strip()
    logger.debug(f"Got {artist} for artist.")
    return title, artist


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
    allowed_ext = get_allowed_extensions()
    files = [os.path.join(dir_path, item) for item in os.listdir(dir_path) if os.path.splitext(item)[1][1:] in allowed_ext]
    dirs = [item[0] for item in os.walk(dir_path)]
    files = files + dirs
    files.remove(dir_path)
    return files


def remove_temp_files():
    logger.debug("Removing temporary files.")
    shutil.rmtree("/tmp/pytvdbapi", ignore_errors=True)


def escape_specials(input:str) -> str:
    specials = ["&", " ", "'", "(", ")"]
    for special in specials:
        input = input.replace(special, f"\\{special}")
    return input

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    only_ascii = nfkd_form.encode('ASCII', 'ignore')
    return only_ascii.decode("utf-8")


def exiftool_change(input_dict, filename):
    logger.debug(f"Attempting to set metadata {input_dict} of {filename} with exiftool")
    with exiftool.ExifTool(executable_="/usr/bin/exiftool") as tool:
        tool.set_tags(input_dict, filename)
    original_path = filename + "_original"
    if os.path.exists(original_path):
        os.remove(original_path)
    else:
        logger.debug("Original file does not exist.")


