import shutil
from subprocess import Popen, PIPE, STDOUT
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
                func()
                self.final_filename = self.final_filename.replace(":", " -").replace('"', '')
                rsync_mkdirs = escape_specials(os.path.join(self.settings['make_dir_schema'].format(media_type=mediatype),
                                                 os.path.split(self.final_filename)[0]))
                if "@" in self.settings['destination_dir']:
                    logger.debug(f"@ seen in {self.settings['destination_dir']}")
                    try:
                        logger.debug(f"Attempting to set {mediatype}_dir")
                        rsync_target = escape_specials(self.settings[f'{mediatype}_dir'].format(media_type=mediatype) + self.final_filename)
                        logger.debug(f"...{rsync_target}")
                    except KeyError:
                        logger.debug(f"{mediatype}_dir not found")
                        rsync_target = escape_specials(
                            self.settings['destination_dir'].format(media_type=mediatype) + self.final_filename)
                        logger.debug(f"...{rsync_target}")
                else:
                    try:
                        logger.debug(f"Attempting to set {mediatype}_dir")
                        rsync_target = os.path.join(self.settings[f'{mediatype}_dir'].format(media_type=mediatype), self.final_filename)
                        logger.debug(f"...{rsync_target}")
                    except KeyError:
                        logger.debug(f"{mediatype}_dir not found")
                        rsync_target = os.path.join(self.settings['destination_dir'].format(media_type=mediatype),
                                                    self.final_filename)
                        logger.debug(f"...{rsync_target}")
                logger.debug(f"Using {rsync_target}")
                new_medObj = MediaObject(filepath, rsync_mkdirs, rsync_target, self.settings['rsync_user'], self.settings['rsync_pass'])
                self.mediaobjs.append(new_medObj)


    def search_book(self):
        logger.error("Book functionality not yet implemented.")
        sys.exit("No functionality.")


    def search_tv(self):
        # TODO make use IMDB if tvdb fails.
        try:
            tvdb_apikey = self.settings['thetvdbkey']
        except KeyError:
            logger.debug("No tvdb api key found, falling back to IMDb")
            tvdb_apikey = ""
        if tvdb_apikey != "":
            try:
                ai = api.TVDB(tvdb_apikey)
            except ConnectionError:
                series = ""
                logger.error("TVDB did not connect.")
            except TimeoutError:
                series = ""
                logger.error("TVDB did not connect.")
            except SSLCertVerificationError:
                series = ""
                logger.error("TVDB did not connect.")
        else:
            ai = IMDb()
        series = self.parse_series_name(self.filename, ai)
        try:
            # make sure dir created by pytvdbapi is useable by all in group
            logger.debug('Making sure dir created by pytvdbapi is useable by all in group')
            return_code = change_permission('/tmp/pytvdbapi')
            if return_code == 0:
                logger.debug("chmod successful.")
            else:
                logger.error("Problem with chmod")
        except PermissionError as e:
            logger.error(f"Permission error for {e.filename}")
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
            except KeyError as e:
                logger.error(f"Problem using TVDB for episode name: {e}")
                episode_name = tv_wikipedia.wikipedia_tv_episode_search(series_name, self.season, self.episode).replace(
                    '"', '')
            except ConnectionError as e:
                logger.error(f"Connection error to tvdb: {e}")
                episode_name = tv_wikipedia.wikipedia_tv_episode_search(series_name, self.season, self.episode).replace(
                    '"', '')
            except TVDBIndexError as e:
                logger.error(f"Couldn't find episode: {e}")
                episode_name = tv_wikipedia.wikipedia_tv_episode_search(series_name, self.season, self.episode).replace(
                    '"', '')
            except TimeoutError as e:
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
            except TVDBIndexError:
                logger.error("Looks like no result was found")
                logger.debug("Falling back to IMDB")
                series_name = self.parse_series_name(self.filename, IMDb())
            except UnboundLocalError:
                logger.error("Looks like TVDB was not found.")
                logger.debug("Falling back to IMDB")
                series_name = self.parse_series_name(self.filename, IMDb())
        elif isinstance(ai, IMDb):
            # Todo flesh this out more.
            series_name = ai.search_movie(self.filename)[0]
        return series_name

    def search_movie(self):
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


def main(*args):
    config = dict(**get_config(args[0]['config']))
    # merge args into config, overwriting values in config.
    config.update(args[0])
    filepath = config['filename']
    logger.debug(f"Running main with parameters: {config}")
    mParser = MediaManager(filepath, config=config)
    mParser.parse_file(mParser.filepath)
    rsync_trigger = False
    for file in mParser.mediaobjs:
        if os.path.isfile(file.source_file):
            logger.debug(f"Moving {file.source_file} to {file.destination_file}.")
            if "@" in file.destination_file:
                logger.debug(f"There is an @ in {file.destination_file}, using rsync.")
                returncode = run_rsync(file)
                if returncode == 0:
                    logger.debug("rsync successful.")
                    rsync_trigger = True
                elif returncode == 1:
                    logger.debug("No sync on testing platform.")
                else:
                    logger.error("Problem with rsync.")
            else:
                if os.uname().nodename != 'landons-laptop':
                    if config['move']:
                        logger.debug("Commencing move.")
                        if not os.path.exists(os.path.dirname(file.destination_file)):
                            os.makedirs(os.path.dirname(file.destination_file))
                        shutil.copy2(src=file.source_file, dst=file.destination_file, follow_symlinks=True)
                    else:
                        logger.debug("Commencing copy.")
                        if not os.path.exists(os.path.dirname(file.destination_file)):
                            os.makedirs(os.path.dirname(file.destination_file))
                        shutil.copy2(src=file.source_file, dst=file.destination_file, follow_symlinks=True)
                else:
                    logger.debug("No moving on test platform.")
        else:
            logger.error(f"{mParser.filepath} is not a real file.")
    if rsync_trigger:
        try:
            logger.debug("Updating Plex library.")
            plex = PlexServer(mParser.settings['plex_url'], mParser.settings['plex_token'])
            plex.library.update()
        except Exception as e:
            logger.error(e)


def run_rsync(file):
    main_return = rsync_runner(file.source_file,
                               file.destination_dir,
                               file.destination_file,
                               file.rsync_user,
                               file.rsync_pass
                               )
    if main_return == 0 or main_return == 1:
        logger.debug("Rsync ran successfully for main file.")
    return main_return


def rsync_runner(source_file:str, destination_dir:str, destination_file:str, rsync_user:str, rsync_pass:str) -> int:
    if os.uname().nodename != 'landons-laptop':
        os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        process = Popen([
            'linux_scripts/rsync.sh',
            source_file,
            destination_dir,
            destination_file,
            rsync_user,
            rsync_pass
        ], stdout=PIPE, stderr=STDOUT)
        logger.debug(process.stdout.read())
        if process.stderr != None:
            logger.error(process.stderr)
        process.communicate()
        return process.returncode
    else:
        return 1

def change_permission(directory):
    process = Popen(['chmod', "-R", "770", directory], stdout=PIPE, stderr=STDOUT)
    if process.stderr != None:
        msg = process.stderr
        logger.error("Problem in change_permission def: {}".format(msg))
    process.communicate()
    return process.returncode