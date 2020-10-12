import shutil
import subprocess
import sys
from pytvdbapi.error import TVDBIndexError, ConnectionError, BadData
import os
from .setup import get_config, get_filepath, get_media_types, setup_logger
from pytvdbapi import api
from imdb import IMDb
from imdb.Movie import Movie
from plexapi.server import PlexServer
import datetime
import re
import difflib
from .tools.plex import get_all_series_names
from ssl import SSLCertVerificationError
from .tools import tv_wikipedia, get_extension, get_media_type, get_parsible_file_name, \
    move_article_to_end, escape_specials, extract_files_if_folder, check_for_year
from .setup.custom_loggers import GroupWriteRotatingFileHandler
from smb.SMBConnection import SMBConnection
from smb.smb_structs import OperationFailure
from pathlib import Path


logger = setup_logger()

def rreplace(s, old, new, occurrence):
     li = s.rsplit(old, occurrence)
     return new.join(li)


class MediaObject():
    def __init__(self, source_file, destination_dir:str="", destination_file:str="", rsync_user:str="", rsync_pass:str=""):
        self.source_file = source_file
        self.destination_dir = destination_dir
        self.destination_file = destination_file
        self.rsync_user = rsync_user
        self.rsync_pass = rsync_pass


class MediaManager():

    def __init__(self, filepath:str, config:dict):
        self.settings = config
        # Where the origin file is
        self.filepath = filepath
        self.mediaobjs = []

    def parse_file(self, filepath:str):
        FUNCTION_MAP = {"book": self.search_book,
                        "tv": self.search_tv,
                        "movies": self.search_movie,
                        "audio": self.search_audio}
        logger.debug("Starting run on {}".format(filepath))
        # if the torrent is a folder recur for each file in folder of appropriate type.
        if os.path.isdir(filepath):
            logger.debug("Filepath {} is a directory, extracting files.".format(filepath))
            file_list = extract_files_if_folder(dir_path=filepath)
            if file_list != []:
                logger.debug("Look out, it's recursion time!")
                for file in file_list:
                    self.parse_file(filepath=file)
            else:
                logger.error("There are no appropriate files in {}".format(filepath))
        else:
            self.extension = get_extension(filepath)
            mediatype = get_media_type(self.extension)
            self.filename, self.season, self.episode, self.disc = get_parsible_file_name(filepath)
            # Ensure that filename was not rejected.
            if self.filename:
                if mediatype == 'video':
                    if self.season:
                        # If we were able to find a season this is a tv show
                        mediatype = 'tv'
                    else:
                        mediatype = 'movies'
                logger.debug(f"Setting media type as {mediatype}.")
                func = FUNCTION_MAP[mediatype]
                logger.debug(f"Selected {func} as search function.")
                func()
                self.final_filename = self.final_filename.replace(":", " -").replace('"', '')
                logger.debug(f"Using {self.final_filename} as final file name.")
                try:
                    logger.debug(f"Attempting to set {mediatype}_dir")
                    _target = escape_specials(self.settings[f'{mediatype}_dir'].format(media_type=mediatype) + self.final_filename)
                    logger.debug(f"...{_target}")
                except KeyError:
                    logger.debug(f"{mediatype}_dir not found, attempting destination dir.")
                    _target = escape_specials(self.settings['destination_dir'].format(media_type=mediatype) + self.final_filename)
                    logger.debug(f"...{_target}")
                logger.debug(f"Using {_target}")
                new_medObj = MediaObject(filepath, os.path.dirname(_target), _target, self.settings['smb_user'], self.settings['smb_pass'])
                self.mediaobjs.append(new_medObj)


    def search_book(self):
        logger.error("Book functionality not yet implemented.")
        sys.exit("No functionality.")


    def search_tv(self):
        # TODO make use IMDB if tvdb fails.
        logger.debug("Hello from search_tv.")
        try:
            logger.debug("Getting tvdbkey.")
            tvdb_apikey = self.settings['thetvdbkey']
        except KeyError:
            logger.debug("No tvdb api key found, falling back to IMDb")
            tvdb_apikey = ""
        if tvdb_apikey != "":
            try:
                ai = api.TVDB(tvdb_apikey)
            except (ConnectionError, TimeoutError, SSLCertVerificationError):
                series = ""
                logger.error("TVDB did not connect.")
        else:
            logger.debug("tvdbkey was empty, using IMDb.")
            ai = IMDb()
        series = self.parse_series_name(self.filename, ai)
        logger.debug(f"Got {series} as series.")
        if isinstance(series, api.Show):
            logger.debug("Using TVDb for series name.")
            series_name = move_article_to_end(series.SeriesName)
        elif isinstance(series, Movie):
            logger.debug("Using IMDB for series name.")
            series_name = move_article_to_end(series.data['title'])
        else:
            logger.debug("Can't use that as a series name.")
            series_name = move_article_to_end(series)
        if isinstance(self.season, datetime.date):
            logger.debug(f"Season given as date, using search by date: {self.season}.")
            try:
                temp_episode = series.api.get_episode_by_air_date(language=self.settings['main_language'], air_date=self.season, series_id=series.id)
                self.season = temp_episode.SeasonNumber
                self.episode = temp_episode.EpisodeNumber
            except BadData as e:
                logger.error("TVDB returned bad data.")
        logger.debug(f"Found series {series_name}.")
        if isinstance(series, api.Show):
            logger.debug("Using TVDb for episode name.")
            try:
                episode_name = series[self.season][self.episode].EpisodeName
            except (ConnectionError, TVDBIndexError, TimeoutError, KeyError) as e:
                logger.error(f"Connection error to tvdb: {e}")
                episode_name = tv_wikipedia.wikipedia_tv_episode_search(series_name, self.season, self.episode).replace(
                    '"', '')
        elif isinstance(series, Movie):
            logger.debug("Using Wikipedia for episode name.")
            episode_name = tv_wikipedia.wikipedia_tv_episode_search(series_name, self.season, self.episode).replace('"', '')
        else:
            logger.debug("Using Wikipedia for episode name.")
            episode_name = tv_wikipedia.wikipedia_tv_episode_search(series_name, self.season, self.episode).replace('"', '')
        episode_name = episode_name.replace("'", "")
        logger.debug("Found episode {}".format(episode_name))
        self.final_filename = self.settings['tv_schema'].format(
            series_name=series_name,
            season_number=str(self.season).zfill(2),
            episode_number=str(self.episode).zfill(2),
            episode_name=episode_name,
            extension=self.extension
        )
        logger.debug(f"Using {self.final_filename} as final file name.")


    def parse_series_name(self, series_name, ai):
        if isinstance(ai, api.TVDB):
            try:
                series_name = ai.search(series_name, self.settings['main_language'])
                logger.debug(f"Series search results: {[item.SeriesName for item in series_name]}")
                try:
                    series_name = [item for item in series_name if item.SeriesName in difflib.get_close_matches(self.filename,
                                                                                                                [item.SeriesName for
                                                                                                                 item in series_name], 1)][0]
                except IndexError:
                    logger.error(
                        f"Search on {series_name} came back empty. Sanitizing using plex to scrape series and retrying.")
                    series_name = difflib.get_close_matches(self.filename, get_all_series_names(self.settings['plex_url'], self.settings['plex_token']), 1)[0]
                    logger.debug(f"Series returned from plex: {series_name}")
                    self.parse_series_name(series_name, ai)
            except (TVDBIndexError, UnboundLocalError) as e:
                logger.error(f"Looks like no result was found: {e}")
                logger.debug("Falling back to IMDB")
                series_name = self.parse_series_name(self.filename, IMDb())
        elif isinstance(ai, IMDb):
            # Todo flesh this out more.
            series_name = ai.search_movie(self.filename)[0]
        else:
            try:
                logger.error(f"Yeah, so for some reason couldn't get a series name. {type(ai).__name__}")
            except:
                logger.error("It doesn't look like ai object exists.")
        return series_name

    def search_movie(self):
        logger.debug("Hello from search_movie.")
        ai = IMDb()
        split = False
        try:
            movie = ai.search_movie(self.filename)[0]
            logger.debug("Found movie {}".format(movie['title']))
        except IndexError:
            logger.warning("Looks like IMDB didn't respond. Falling back to split.")
            movie_list = re.split(r'\s\(', self.filename)
            logger.debug(movie_list)
            movie = {'title': movie_list[0], 'year': check_for_year(filename=self.filename)}
        movie_name = movie['title']
        # Remove any extra instances of the movie's year.
        year_regex = re.compile(r'\({year}\)'.format(year=movie['year']))
        movie_name = year_regex.sub("", movie_name)
        # ensure 'the', 'an', 'a', etc is moved to the end of the movie name.
        movie_name = move_article_to_end(movie_name)
        year_of_release = movie['year']
        final_filename = self.settings['movie_schema'].format(
            movie_name=movie_name,
            year_of_release = year_of_release,
            extension = self.extension
        )
        # remove any extra spaces
        self.final_filename = re.sub(' +', ' ', final_filename)
        logger.debug(f"Using {self.final_filename} as final file name.")


    def search_audio(self):
        logger.warning("Audio functionality not yet implemented.")
        sys.exit("No functionality.")


def construct_ffmpeg_copy(source_file:str, destination_file:str) -> list:
    logger.debug(f"Making ffmpeg paths with {source_file} and {destination_file}")
    return ["ffmpeg", "-i", source_file, "-c", "copy", "-map_metadata", "-1", destination_file]

def main(*args):
    config = dict(**get_config(args[0]['config']))
    # merge args into config, overwriting values in config.
    config.update(args[0])
    filepath = config['filename']
    logger.debug(f"Running main with parameters: {config}")
    mParser = MediaManager(filepath, config=config)
    mParser.parse_file(mParser.filepath)
    # A trigger to keep track of if the move was successful.
    move_trigger = False
    for file in mParser.mediaobjs:
        # Make sure the source file is actually there.
        if os.path.isfile(file.source_file):
            logger.debug(f"Moving {file.source_file} to {file.destination_file}.")
            # Check for smb file destination
            if file.destination_file[:3] == "smb":
                if os.uname().nodename != 'landons-laptop':
                    logger.debug(f"There is an smb in {file.destination_file}, using smb.")
                    # apparently pysmb doesn't like backslashes.
                    path_list = file.destination_file.replace("\\", "").split("/")
                    server_address = path_list[2]
                    share = path_list[3]
                    folders = path_list[4:-1]
                    file_path = "/".join(path_list[4:])
                    logger.debug(f"File path {file_path}")
                    conn = SMBConnection(config['smb_user'], config['smb_pass'], "client", "host", use_ntlm_v2=True)
                    try:
                        conn.connect(server_address)
                    except Exception as e:
                        logger.error(f"SMB connection failed: {e}")
                    fullpath = ""
                    for folder in folders:
                        fullpath += f"/{folder}"
                        # Check if directory exists, if not, make it.
                        try:
                            conn.listPath(share, fullpath)
                        except OperationFailure:
                            conn.createDirectory(share, fullpath)
                    logger.debug("Writing file.")
                    # Write the file.
                    with open(file.source_file, "rb") as f:
                        try:
                            resp = conn.storeFile(share, file_path, f)
                            logger.debug(f"SMB protocol returned {resp}")
                            move_trigger = True
                        except Exception as e:
                            logger.error(f"Problem with writing file on smb: {e}")
                else:
                    logger.warning("No moving on test platform.")
            else:
                if os.uname().nodename != 'landons-laptop':
                    # if config['move']:
                    #     logger.debug("Commencing move.")
                    #     if not os.path.exists(os.path.dirname(file.destination_file)):
                    #         os.makedirs(os.path.dirname(file.destination_file))
                    #     if config['use_ffmpeg']:
                    #         logger.debug("Using ffmpeg.")
                    #         child = subprocess.Popen(construct_ffmpeg_copy(file.source_file, file.destination_file),
                    #                                  stdout=subprocess.PIPE)
                    #         streamdata = child.communicate()[0]
                    #         rc = child.returncode
                    #         if rc == 0:
                    #             move_trigger = True
                    #         else:
                    #             logger.error("There was a problem with FFMPEG.")
                    #     else:
                    #         shutil.copy2(src=file.source_file, dst=file.destination_file, follow_symlinks=True)
                    #         move_trigger = True
                    # else:
                    logger.debug("Commencing copy.")
                    if not os.path.exists(os.path.dirname(file.destination_file)):
                        logger.debug(f"Making directory {os.path.dirname(file.destination_file)}")
                        os.makedirs(os.path.dirname(file.destination_file))
                    if config['use_ffmpeg']:
                        logger.debug("Using ffmpeg.")
                        child = subprocess.Popen(construct_ffmpeg_copy(file.source_file, file.destination_file),
                                                 stdout=subprocess.PIPE)
                        streamdata = child.communicate()[0]
                        rc = child.returncode
                        if rc == 0:
                            move_trigger = True
                        else:
                            logger.error("There was a problem with FFMPEG.")
                    else:
                        shutil.copy2(src=file.source_file, dst=file.destination_file, follow_symlinks=True)
                        move_trigger = True
                else:
                    logger.warning("No moving on test platform.")
        else:
            logger.error(f"{mParser.filepath} is not a real file.")
    # if the move is successful and there's plex in the config, update the library.
    if move_trigger and "plex_url" in config.keys():
        try:
            logger.debug("Updating Plex library.")
            plex = PlexServer(mParser.settings['plex_url'], mParser.settings['plex_token'])
            plex.library.update()
        except Exception as e:
            logger.error(e)
