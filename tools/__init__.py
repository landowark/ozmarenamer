import difflib
import os
from typing import List
from configure import get_config
import shutil
import unicodedata
# import exiftool
import pylast
from .plex import get_all_series_names, enforce_series_with_plex, update_plex_library
# from .wikipedia import *
from .lastfm import *
from smb.SMBConnection import SMBConnection
from smb.smb_structs import OperationFailure
from pathlib import Path
from .IMDB import *

logger = logging.getLogger("ozma.tools")

strip_list = ["HDTV", "x264", "x265", "h264", "720p", "1080p", "PROPER", "WEBRip", "WEB", "EXTENDED", "DVDRip", "HC",
              "HDRip", "XviD", "AC3", "BRRip", "Bluray", "Internal", "AAC", "YIFY", "UNCUT"]
rejected_filenames = ['sample']
extensions = {
    "book": [".epub", ".mobi"],
    "video": [".mkv", ".mp4", ".avi", ".m4v"],
    "audio": [".mp3", ".m4a", ".opus"]
}

def get_allowed_extensions():
    return [item for sublist in [extensions[item] for item in extensions] for item in sublist]


# def split_file_name(filepath):
#     return os.path.basename(filepath)
#
#
# def get_extension(filepath):
#     return os.path.splitext(filepath)[1][1:]
#
#
# def remove_extension(filepath):
#     return os.path.splitext(filepath)[0]


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

def get_season(filename):
    season = re.compile(r's(?:eason)?\d{1,2}', re.IGNORECASE)
    try:
        result = re.findall(season, filename)[0].upper()
        return int(result.replace("S", ""))
    except:
        return None

def get_episode(filename):
    episode = re.compile(r'e(?:pisode)?\d{1,2}', re.IGNORECASE)
    try:
        result = re.findall(episode, filename)[0].upper()
        return int(result.replace("E", ""))
    except:
        return None

def get_season_episode_dxdd(filename):
    regex = re.compile(r'\d{1,2}x\d{1,2}', re.IGNORECASE)
    try:
        both = re.findall(regex, filename)
        both = both[0].split('x')
        season = both[0]
        episode = both[1]
        return int(season), int(episode)
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


def get_media_type(extension):
    for type in extensions:
        if extension in extensions[type]:
            logger.debug(f"We got the {type} filetype.")
            return type


def get_year_released(basefile):
    # K, this is a little tricky as the title might contain a year i.e. Wonder Woman 1984, 2012
    # step 1: prefer years in brackets. -1 index will get last year in the list.
    try:
        year_released = re.findall(r'\((20\d{2}|19\d{2})\)', basefile)[-1]
    except IndexError:
        try:
            year_released = re.findall(r'(20\d{2}|19\d{2})', basefile)[-1]
        except IndexError:
            logger.error("Couldn't find year of release.")
            return ""
    logger.debug(f"Returning year released: {year_released}")
    return year_released


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


def extract_files_if_folder(dir_path: Path) -> List[Path]:
    allowed_extensions = get_allowed_extensions()
    # files = [os.path.join(dir_path, item) for item in os.listdir(dir_path) if os.path.splitext(item)[1] in allowed_ext]
    # dirs = [item[0] for item in os.walk(dir_path)]
    # files = files + dirs
    # files.remove(dir_path)
    files = []
    for extension in allowed_extensions:
        files.append(dir_path.glob(f"**/*{extension}"))
    return [item for sublist in files for item in sublist]
    # return files


def remove_temp_files():
    logger.debug("Removing temporary files.")
    shutil.rmtree("/tmp/pytvdbapi", ignore_errors=True)


def escape_specials(input:str) -> str:
    specials = ["&", " ", "'", "(", ")"]
    for special in specials:
        input = input.replace(special, f"\\{special}")
    return input

def replace_forward_slash_in_title(input:str) -> str:
#     step one: get index of forward slash
    try:
        start_idx = input.index("/")
    except ValueError as e:
        return input
    end_idx = input.find(" ", start_idx)
    return f"{input[:start_idx]}({input[start_idx+1:end_idx]}){input[end_idx:]}"



def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    only_ascii = nfkd_form.encode('ASCII', 'ignore')
    return only_ascii.decode("utf-8")


# def exiftool_change(input_dict, filename):
#     logger.debug(f"Attempting to set metadata {input_dict} of {filename} with exiftool")
#     with exiftool.ExifTool(executable_="/usr/bin/exiftool") as tool:
#         tool.set_tags(input_dict, filename)
#     original_path = filename + "_original"
#     if os.path.exists(original_path):
#         os.remove(original_path)
#     else:
#         logger.debug("Original file does not exist.")


def get_album_info(track_title:str, album:pylast.Album):
    track_list = [track.get_name().lower() for track in album.get_tracks()]
    track_title = difflib.get_close_matches(track_title, track_list)[0].title()
    try:
        track_number = str([i for i, x in enumerate(track_list) if x == track_title.lower()][0] + 1).zfill(2)
    except IndexError as e:
        logger.error(f"Couldn't get track number of {track_title} in {track_list}")
    track_total = str(len(track_list))
    return track_title, track_number, track_total


def check_if_tv(filename):
    if get_season(filename) != None:
        return True
    elif get_episode(filename) != None:
        return True
    elif get_season_episode_dxdd(filename) != (None, None):
        return True
    else:
        return False


def sanitize_file_name(raw:str):
    raw = raw + "."
    raw = raw.replace(" ", ".")
    raw = re.sub(r"\[.+\]", "", raw)
    for item in strip_list:
        raw = re.sub(rf"[\.|\s|-]?{item}[\.|\s|-]", " ", raw, flags=re.I)
    raw = raw.strip().split(" ")[0].replace(".", " ")
    logger.debug(f"Returning sanitized filename: {raw}")
    return raw


def remove_season_episode(raw:str):
    raw = re.sub(r'[\.|\s|-]?s(?:eason)?\d{1,2}.*', " ", raw, flags=re.I)
    raw = re.sub(r'[\.|\s|-]?e(?:pisode)?\d{1,2}.*', " ", raw, flags=re.I)
    raw = re.sub(r'\d{1,2}x\d{1,2}.*', " ", raw, flags=re.I)
    return raw.strip()

def enforce_series_name(basefile:str, context: dict):
    # First santize the file base name
    series_name = sanitize_file_name(basefile)
    series_name = remove_season_episode(series_name)
    # We'll make the plex attempt first
    try:
        plex_config = context["plex"]
    except KeyError:
        logger.warning("Plex not found in settings")
    if "plex_config" in locals():
        return enforce_series_with_plex(series_name, plex_config)
    else:
        try:
            return enforce_series_with_IMDB(series_name)
        except Exception as e:
            logger.error(f"IMDB bugged out for enforcement: {e}")
            # return enforce_series_with_wikipedia(series_name)



def get_season_and_episode(basefile):
    season = get_season(basefile)
    episode = get_episode(basefile)
    if season == None:
        logger.debug(f"Checking season with dxdd")
        season, _ = get_season_episode_dxdd(basefile)
    if episode == None:
        logger.debug(f"Checking episode with dxdd")
        _, episode = get_season_episode_dxdd(basefile)
    logger.debug(f"We got season {season} & episode {episode}.")
    return season, episode


def get_episode_name(series_name:str, season_number:int, episode_number:int, tv_config:dict={}):
    if "thetvdbkey" in tv_config:
        pass
    else:
        # try:
        episode_name, airdate = IMDB_episode_search(series_name, season_number, episode_number)
        # except Exception as e:
        #     logger.error(f"IMDB bugged out for episode name: {e}.")
            # episode_name, airdate = wikipedia_tv_episode_search(series_name, season_number, episode_number)
        episode_name = escape_specials(replace_forward_slash_in_title(episode_name))
        logger.debug(f"Got episode name:{episode_name}, airdate: {airdate}.")
        return episode_name, airdate


def check_movie_title(basefile:str):
    movie_title = sanitize_file_name(basefile)
    year_of_release = get_year_released(movie_title)
    movie_title = re.sub(rf'\(?{year_of_release}\)?', "", movie_title)
    logger.debug(f"Using movie title: {movie_title}")
    # movie_title = movie_title.replace(year_of_release, "").strip()
    # Currently only wikipedia exists
    try:
        movie_title, year_of_release = check_movie_with_IMDB(movie_title, year_of_release)
    except Exception as e:
        logger.error(f"IMDb crapped out with: {e}")
        # movie_title, year_of_release = check_movie_with_wikipedia(movie_title, year_of_release)
    logger.debug(f"Got movie title: {movie_title}, year of release: {year_of_release}")
    return movie_title, year_of_release


def get_movie_details(movie_title:str, release_year:str):
    # currently only wikipedia is supported
    try:
        director, starring = IMDB_movie_search(movie_title, release_year)
    except Exception as e:
        logger.error(f"IMDB crapped out on movie search: {e}")
        # director, starring =  wikipedia_movie_search(movie_title, release_year)
        director = None
        starring = None
    logger.debug(f"Got director: {director}, starring: {starring}")
    return director, starring


def check_artist_name(basefile:str, song_config={}):
    # if "lastfmkey" in song_config and "lastfmsec" in song_config:
    return check_artist_with_lastfm(basefile, song_config)
    # else:
    #     return wikipedia_artist_search(basefile)


def check_song_name(basefile:str, artist:str, song_config={}):
    logger.debug(f"Hello from {__name__}")
    if "lastfmkey" in song_config and "lastfmsec" in song_config:
        logger.debug("Using lastfm for checking song name.")
        return check_song_name_with_lastfm(basefile, artist, song_config)
    else:
        logger.debug("Gonna use wikipedia for checking song name.")
        # return wikipedia_song_search(basefile, artist)


def get_song_details(artist:str, song:str, song_config={}):
    # if "lastfmkey" in song_config and "lastfmsec" in song_config:
    logger.debug("Using lastfm for song details.")
    return lastfm_song_details(artist, song, song_config)
    # else:
    #     logger.debug("Using wikipedia for song details.")
    #     return wikipedia_song_details(artist, song)


def samba_move_file(smb_config:dict, source_file:str, destination_file:str, development:bool, progress: bool = True):
    # smb_config = get_config(section="smb")
    path_list = destination_file.replace("\\", "").replace("?", "").split("/")
    server_address = path_list[2]
    share = path_list[3]
    folders = path_list[4:-1]
    file_path = "/".join(path_list[4:])
    logger.debug(f"File path {file_path}")
    conn = SMBConnection(smb_config['smb_user'], smb_config['smb_pass'], "client", "host", use_ntlm_v2=True)
    try:
        conn.connect(server_address)
    except Exception as e:
        logger.error(f"SMB connection failed: {e}")
    fullpath = ""
    for folder in folders:
        if not development:
            fullpath += f"/{folder}"
            # Check if directory exists, if not, make it.
            try:
                conn.listPath(share, fullpath)
            except OperationFailure:
                conn.createDirectory(share, fullpath)
        else:
            logger.warning("No folder creation on development environment.")
    # Write the file.
    with open(source_file, "rb") as f:
        # logger.debug(share + file_path)
        try:
            if not development:
                logger.debug("Writing file.")
                resp = conn.storeFile(share, file_path, f, show_progress=progress)
                logger.debug(f"SMB protocol returned {resp}")
                move_trigger = True
            else:
                logger.warning("No moving on development environment.")
        except Exception as e:
            logger.error(f"Problem with writing file on smb: {e}")
    conn.close()


def normal_move_file(source_file:Path, destination_file:str, development:bool, move:bool=False):
    destination_file = destination_file.replace("\\", "")
    if not development:
        Path(destination_file).parent.mkdir(parents=True, exist_ok=True)
        if move:
            logger.debug("Move selected, moving file.")
            shutil.move(source_file, destination_file)
        else:
            logger.debug("Copy selected, copying file.")
            shutil.copy2(source_file, destination_file)
    else:
        logger.warning("No moving on development environment.")


def update_libraries():
    # todo add KODI?
    try:
        plex_config = get_config(section="plex")
        update_plex_library(plex_config)
    except KeyError:
        logger.warning("Plex not found in settings")


def get_basefile_schema(config):
    logger.debug("Overriding destination folder.")
    schema_item = {key:value for key, value in config.items() if 'schema' in key.lower()}
    for item in schema_item.keys():
        path = Path(schema_item[item]).name
        config[item] = path
    return config

