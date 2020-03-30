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

from .setup.custom_loggers import GroupWriteRotatingFileHandler


logger = setup_logger()
config = dict(**get_config())

from .tools import transmission, tv_wikipedia, img_scraper, get_extension, get_media_type, get_parsible_file_name, move_article_to_end, escape_specials, extract_files_if_folder

def rreplace(s, old, new, occurrence):
     li = s.rsplit(old, occurrence)
     return new.join(li)


class MediaObject():
    def __init__(self, source_file, destination_dir, destination_file, rsync_user, rsync_pass):
        self.source_file = source_file
        self.destination_dir = destination_dir
        self.destination_file = destination_file
        self.rsync_user = rsync_user
        self.rsync_pass = rsync_pass
        self.extra_files = []


class MediaManager():

    def __init__(self, filepath:str, extras:bool):
        self.settings = config
        self.filepath = filepath
        self.mediaobjs = []
        self.extras = extras

    def parse_file(self, filepath):
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
            # Ensure that a filename exists.
            if self.filename:
                if mediatype == 'video':
                    if self.season:
                        mediatype = 'tv'
                    else:
                        mediatype = 'movies'
                logger.debug("Setting media type as {}.".format(mediatype))
                func = FUNCTION_MAP[mediatype]
                func()
                self.final_filename = self.final_filename.replace(":", "-").replace('"', '')
                rsync_mkdirs = escape_specials(os.path.join(self.settings['make_dir_schema'].format(media_type=mediatype),
                                                 os.path.split(self.final_filename)[0]))
                rsync_target = escape_specials(self.settings['rsync_schema'].format(media_type=mediatype) + self.final_filename)
                new_medObj = MediaObject(filepath, rsync_mkdirs, rsync_target, self.settings['rsync_user'], self.settings['rsync_pass'])
                if self.extras:
                    logger.debug("Extras requested.")
                    new_medObj.extra_files = img_scraper.google_search_for_images(" ".join(os.path.splitext(os.path.basename(self.final_filename))[0].split(".")[:-1]))
                else:
                    logger.debug("Extras not requested.")
                self.mediaobjs.append(new_medObj)


    def search_book(self):
        logger.error("Book functionality not yet implemented.")
        sys.exit("No functionality.")


    def search_tv(self):
        tvdb_apikey = self.settings['thetvdbkey']
        try:
            tvdb = api.TVDB(tvdb_apikey)
        except ConnectionError:
            series = ""
            logger.error("TVDB did not connect.")
        try:
            series = tvdb.search(self.filename, self.settings['main_language'])
            series = [item for item in series if
             item.SeriesName in difflib.get_close_matches(self.filename, [item.SeriesName for item in series], 1)][0]
        except TVDBIndexError:
            logger.error("Looks like no result was found")
            logger.debug("Falling back to IMDB")
            ai = IMDb()
            series = ai.search_movie(self.filename)[0]
        except UnboundLocalError:
            logger.error("Looks like TVDB was not found.")
            logger.debug("Falling back to IMDB")
            ai = IMDb()
            series = ai.search_movie(self.filename)[0]
        try:
            # make sure dir created by pytvdbapi is useable by all in group
            logger.debug('Making sure dir created by pytvdbapi is useable by all in group')
            return_code = change_permission('/tmp/pytvdbapi')
            if return_code == 0:
                logger.debug("chmod successful.")
            else:
                logger.error("Problem with chmod")
        except PermissionError as e:
            logger.error("Permission error for {}".format(e.filename))
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
            logger.debug("Season given as date, using search by date: {}.".format(self.season))
            try:
                temp_episode = series.api.get_episode_by_air_date(language=self.settings['main_language'], air_date=self.season, series_id=series.id)
                self.season = temp_episode.SeasonNumber
                self.episode = temp_episode.EpisodeNumber
            except BadData as e:
                logger.error("TVDB returned bad data.")
        logger.debug("Found series {}.".format(series_name))
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
        elif isinstance(series, Movie):
            logger.debug("Using Wikipedia for episode name.")
            episode_name = tv_wikipedia.wikipedia_tv_episode_search(series_name, self.season, self.episode).replace('"', '')
        else:
            logger.debug("Using Wikipedia for episode name.")
            episode_name = tv_wikipedia.wikipedia_tv_episode_search(series_name, self.season, self.episode).replace('"', '')
        logger.debug("Found episode {}".format(episode_name))
        self.final_filename = self.settings['tv_schema'].format(
            series_name=series_name,
            season_number=str(self.season).zfill(2),
            episode_number=str(self.episode).zfill(2),
            episode_name=episode_name,
            extension=self.extension
        )
        logger.debug(f"Using {self.final_filename} as final file name.")


    def search_movie(self):
        ai = IMDb()
        split = False
        try:
            movie = ai.search_movie(self.filename)[0]
            logger.debug("Found movie {}".format(movie['title']))
        except IndexError:
            logger.warning("Looks like IMDB didn't respond. Falling back to split.")
            split = True
            movie_list = re.split(r'\s\(', self.filename)
            logger.debug(movie_list)
            movie = {'title': movie_list[0], 'year': movie_list[1].strip(")")}
        movie_name = movie['title']
        year_of_release = movie['year']
        self.final_filename = self.settings['movie_schema'].format(
            movie_name=movie_name,
            year_of_release = year_of_release,
            extension = self.extension
        )
        if not split and "extras" in  self.settings:
            logger.debug("We want extras!")



    def search_audio(self):
        logger.warning("Audio functionality not yet implemented.")
        sys.exit("No functionality.")


def main(*args):
    logger.debug(f"Running main with arguments: {args}")
    filepath = args[0]['filename']
    extras = args[0]['extras']
    mParser = MediaManager(filepath, extras=extras)
    mParser.parse_file(mParser.filepath)
    rsync_trigger = False
    for file in mParser.mediaobjs:
        if os.path.isfile(file.source_file):
            logger.debug("Moving {} to {}.".format(file.source_file, file.destination_file))
            returncode = run_rsync(file, mParser.extras)
            if returncode == 0:
                logger.debug("rsync successful.")
                rsync_trigger = True
            elif returncode == 1:
                logger.debug("No sync on testing platform.")
            else:
                logger.error("Problem with rsync.")
        else:
            logger.error("{} is not a real file.".format(mParser.filepath))
    try:
        transmission.remove_ratioed_torrents()
    except NameError:
        pass
    if rsync_trigger:
        try:
            logger.debug("Updating Plex library.")
            plex = PlexServer(mParser.settings['plex_url'], mParser.settings['plex_token'])
            plex.library.update()
        except Exception as e:
            logger.error(e)


def run_rsync(file, extras:bool=False):
    main_return = rsync_runner(file.source_file,
                               file.destination_dir,
                               file.destination_file,
                               file.rsync_user,
                               file.rsync_pass
                               )
    if main_return == 0 or main_return == 1:
        logger.debug("Rsync ran successfully for main file.")
        if extras == True:
            for item in file.extra_files:
                print(item, escape_specials(file.destination_dir), escape_specials(os.path.basename(item)))
                extra_return = rsync_runner(item,
                                            escape_specials(file.destination_dir),
                                            escape_specials(os.path.basename(item)),
                                            file.rsync_user,
                                            file.rsync_pass
                                           )
                if extra_return == 0:
                    logger.debug(f"Rsync ran successfully for {item}")
                elif extra_return == 1:
                    logger.debug(f"No sync for {item} on testing platform.")
                else:
                    logger.error(f"Error running rsync on {item}")
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