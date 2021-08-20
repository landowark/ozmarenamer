import difflib
import os
import re

import pylast
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

    # Split on year released to remove extraneous info.
    year_released = check_for_year(filename)
    # todo maybe change this to "if filename.etc is not nonetype
    try:
        filename = filename.split(year_released)[0] + year_released
    except TypeError:
        logger.warning("No year found in title, probably a TV show, carrying on.")
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
    title = filename.split(" - ")[1].strip()
    logger.debug(f"Got {title} for title.")
    artist = filename.split(" - ")[0].strip()
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


def get_artist_with_lastfm(settings, artist, **kwargs):
    ai = pylast.LastFMNetwork(api_key=settings['lastfmkey'], api_secret=settings['lastfmsec'])
    searched_artist = pylast.ArtistSearch(artist_name=artist, network=ai).get_next_page()[0]
    logger.debug(f"Returning {searched_artist} as searched artist.")
    return searched_artist


def get_track_with_lastfm(settings:dict, artist, title:str, **kwargs):
    if "optional_recursive_artist" in kwargs:
        #     make switch to avoid recalling
        logger.debug("Running second attempt at search music...")
        artist = kwargs['optional_recursive_artist']
    ai = pylast.LastFMNetwork(api_key=settings['lastfmkey'], api_secret=settings['lastfmsec'])
    # check what kind of artist variable we're being passed.
    if isinstance(artist, pylast.Artist):
        artist_str = artist.get_name()
        logger.debug("Using pylast Artist instance")
    elif isinstance(artist, str):
        logger.debug("Using string for artist name.")
        artist_str = artist
    else:
        logger.error("Artist is not an acceptable class.")
        raise TypeError
    track = pylast.TrackSearch(artist_name=artist_str, track_title=title, network=ai).get_next_page()[0]
    if isinstance(track, pylast.Track):
        return_track = {}
        logger.debug(f"We got this track: {track.__dict__}")
        return_track['track_title'] = track.get_name()
        logger.debug(f"We got {return_track['track_title']} as title.")
        return_track['artist_name'] = move_article_to_end(track.get_artist().get_name())
        logger.debug(f"We got {return_track['artist_name']} as artist.")
        album = track.get_album()
        if isinstance(album, pylast.Album):
            return_track['album_name'] = album.get_name()
            logger.debug(f"We got {return_track['album_name']} as album.")
            return_track['track_title'], return_track['track_number'], return_track['track_total'] = get_album_info(
                return_track['track_title'], album)
            logger.debug(f"Using {return_track} as final track.")
            return return_track
        else:
            logger.warning("Got no album , likely due to faulty artist search. Recursion attempt with article removal.")
            if "optional_recursive_artist" not in kwargs:
                new_artist = re.sub(re.compile(r"the |an |a ", re.IGNORECASE), "", artist_str)
                return_track = get_track_with_lastfm(settings, artist, title, optional_recursive_artist=new_artist)
                logger.debug(f"In the recursion we got {return_track['album_name']} as album.")
                return return_track
    else:
        logger.error("Search was not successful, did not produce track.")
        raise TypeError


def get_album_info(track_title:str, album:pylast.Album):
    track_list = [track.get_name().lower() for track in album.get_tracks()]
    track_title = difflib.get_close_matches(track_title, track_list)[0].title()
    try:
        track_number = str([i for i, x in enumerate(track_list) if x == track_title.lower()][0] + 1).zfill(2)
    except IndexError as e:
        logger.error(f"Couldn't get track number of {track_title} in {track_list}")
    track_total = str(len(track_list))
    return track_title, track_number, track_total

