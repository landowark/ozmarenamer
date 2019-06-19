from subprocess import Popen, PIPE, STDOUT
import sys, os
from .setup import get_config, get_params, get_filepath
from .tools import *
from pytvdbapi import api
from imdb import IMDb
import logging
from plexapi.server import PlexServer
import datetime
from .tools import transmission

logger = logging.getLogger("ozma.parser")

class MediaParser():

    def __init__(self):
        self.settings = dict(**get_params(), **get_config())
        self.FUNCTION_MAP = {"book": self.search_book,
                             "tv": self.search_tv,
                             "movie": self.search_movie,
                             "audio": self.search_audio}
        self.rsync_user = self.settings['rsync_user']
        self.rsync_pass = self.settings['rsync_pass']

    def parse_file(self):
        self.filepath = get_filepath()
        logger.debug("Starting run on {}".format(self.filepath))
        # todo add option to run on downloaded directory.
        self.extenstion = get_extension(self.filepath)
        self.mediatype = get_media_type(self.extenstion)
        self.filename, self.season, self.episode, self.disc = get_parsible_file_name(self.filepath)
        if self.mediatype == 'video':
            if self.season:
                self.mediatype = 'tv'
            else:
                self.mediatype = 'movie'
        logger.debug("Setting media type as {}.".format(self.mediatype))
        func = self.FUNCTION_MAP[self.mediatype]
        func()
        del self.FUNCTION_MAP

    def search_book(self):
        logger.error("Book functionality not yet implemented.")
        sys.exit("No functionality.")


    def search_tv(self):
        self.tvdb_apikey = self.settings['thetvdbkey']
        tvdb = api.TVDB(self.tvdb_apikey)
        series = tvdb.search(self.filename, self.settings['main_language'])[0]
        self.series_name = move_article_to_end(series.SeriesName)
        if isinstance(self.season, datetime.date):
            logger.debug("Season given as date, using search by date: {}.".format(self.season))
            temp_episode = series.api.get_episode_by_air_date(language=self.settings['main_language'], air_date=self.season, series_id=series.seriesid)
            self.season = temp_episode.SeasonNumber
            self.episode = temp_episode.EpisodeNumber
        logger.debug("Found series {}.".format(self.series_name))
        self.episode_name = series[self.season][self.episode].EpisodeName
        logger.debug("Found episode {}".format(self.episode_name))
        self.final_filename = self.settings['tv_schema'].format(
            series_name=self.series_name,
            season_number=str(self.season).zfill(2),
            episode_number=str(self.episode).zfill(2),
            episode_name=self.episode_name,
            extension=self.extenstion)
        self.rsync_mkdirs = os.path.join(self.settings['make_dir_schema'].format(media_type=self.mediatype), os.path.split(self.final_filename)[0])
        self.rsync_target = self.settings['rsync_schema'].format(media_type=self.mediatype) + self.final_filename


    def search_movie(self):
        ai = IMDb()
        movie = ai.search_movie(self.filename)[0]
        self.movie_name = movie['title']
        logger.debug("Found movie {}".format(self.movie_name))
        self.year_of_release = movie['year']
        self.final_filename = self.settings['movie_schema'].format(
            movie_name=self.movie_name,
            year_of_release = self.year_of_release,
            extension = self.extenstion
        )


    def search_audio(self):
        logger.warning("Audio functionality not yet implemented.")
        sys.exit("No functionality.")


def main():
    mParser = MediaParser()
    mParser.parse_file()
    logger.debug("Moving {} to {}.".format(mParser.filepath, mParser.rsync_target))
    if os.path.isfile(mParser.filepath):
        returncode = run_rsync(mParser)
        if returncode == 0:
            logger.debug("rsync successful.")
            try:
                logger.debug("Updating Plex library.")
                plex = PlexServer(mParser.settings['plex_url'], mParser.settings['plex_token'])
                plex.library.refresh()
            except Exception as e:
                logger.error(e)
        else:
            logger.error("Problem with rsync.")
    else:
        logger.error("{} is not a real file.".format(mParser.filepath))
    transmission.remove_ratioed_torrents()


def run_rsync(mParser):
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    process = Popen([
        'linux_scripts/rsync.sh',
        mParser.filepath,
        mParser.rsync_mkdirs.replace(" ", "\\ "),
        mParser.rsync_target.replace(" ", "\\ "),
        mParser.rsync_user,
        mParser.rsync_pass
    ], stdout=PIPE, stderr=STDOUT)
    logger.debug(process.stdout.read())
    if process.stderr != None:
        logger.error(process.stderr)
    process.communicate()
    return process.returncode