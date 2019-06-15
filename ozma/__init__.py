from subprocess import Popen, PIPE, STDOUT
import sys, os
from .setup import get_config, get_params, get_filepath
from .tools import *
from pytvdbapi import api
from imdb import IMDb
import logging

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
        del self.settings
        del self.FUNCTION_MAP

    def search_book(self):
        logger.error("Book functionality not yet implemented.")
        sys.exit("No functionality.")


    def search_tv(self):
        self.tvdb_apikey = self.settings['thetvdbkey']
        tvdb = api.TVDB(self.tvdb_apikey)
        series = tvdb.search(self.filename, self.settings['main_language'])[0]
        self.series_name = series.SeriesName
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
    print(mParser.__dict__)
    file_destination = mParser.rsync_target.replace(" ", "\\ ")
    file_source = mParser.filepath
    rsync_dir = mParser.rsync_mkdirs.replace(" ", "\\ ")
    username = mParser.rsync_user
    password = mParser.rsync_pass
    # print(file_source, file_destination, username, password)
    logger.debug("Moving {} to {}.".format(file_source, file_destination))
    if os.path.isfile(file_source):
        process = Popen(['linux_scripts/rsync.sh', file_source, rsync_dir, file_destination, username, password], stdout=PIPE,
                        stderr=STDOUT)
        logger.debug(process.stdout.read())
        if process.stderr != None:
            logger.error(process.stderr)
        pass
    else:
        logger.error("{} is not a real file.".format(file_source))