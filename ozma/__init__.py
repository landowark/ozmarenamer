from subprocess import Popen, PIPE, STDOUT
import sys
from .setup import get_config, get_params, get_filepath, get_media_types
from .tools import *
from pytvdbapi import api
from imdb import IMDb
import logging
from plexapi.server import PlexServer
import datetime
from .tools import transmission


logger = logging.getLogger("ozma.parser")

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


class MediaManager():

    def __init__(self):
        self.settings = dict(**get_params(), **get_config())
        self.filepath = get_filepath()
        self.mediaobjs = []

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
            if mediatype == 'video':
                if self.season:
                    mediatype = 'tv'
                else:
                    mediatype = 'movies'
            logger.debug("Setting media type as {}.".format(mediatype))
            func = FUNCTION_MAP[mediatype]
            func()
            self.final_filename = self.final_filename.replace(":", "-")
            rsync_mkdirs = os.path.join(self.settings['make_dir_schema'].format(media_type=mediatype),
                                             os.path.split(self.final_filename)[0])
            rsync_mkdirs = rsync_mkdirs.replace("(", "\\(")
            rsync_mkdirs = rsync_mkdirs.replace(")", "\\)")
            rsync_target = self.settings['rsync_schema'].format(media_type=mediatype) + self.final_filename
            rsync_target = rsync_target.replace("(", "\\(")
            rsync_target = rsync_target.replace(")", "\\)")
            self.mediaobjs.append(MediaObject(filepath, rsync_mkdirs, rsync_target, self.settings['rsync_user'], self.settings['rsync_pass']))


    def search_book(self):
        logger.error("Book functionality not yet implemented.")
        sys.exit("No functionality.")


    def search_tv(self):
        tvdb_apikey = self.settings['thetvdbkey']
        tvdb = api.TVDB(tvdb_apikey)
        try:
            series = tvdb.search(self.filename, self.settings['main_language'])[0]
            # make sure dir created by pytvdbapi is useable by all in group
            logger.debug('Making sure dir created by pytvdbapi is useable by all in group')
            return_code = change_permission('/tmp/pytvdbapi')
            if return_code == 0:
                logger.debug("chmod successful.")
            else:
                logger.error("Problem with chmod")
        except PermissionError as e:
            logger.error("Permission error for {}".format(e.filename))
        series_name = move_article_to_end(series.SeriesName)
        if isinstance(self.season, datetime.date):
            logger.debug("Season given as date, using search by date: {}.".format(self.season))
            temp_episode = series.api.get_episode_by_air_date(language=self.settings['main_language'], air_date=self.season, series_id=series.seriesid)
            self.season = temp_episode.SeasonNumber
            self.episode = temp_episode.EpisodeNumber
        logger.debug("Found series {}.".format(series_name))
        episode_name = series[self.season][self.episode].EpisodeName
        logger.debug("Found episode {}".format(episode_name))
        self.final_filename = self.settings['tv_schema'].format(
            series_name=series_name,
            season_number=str(self.season).zfill(2),
            episode_number=str(self.episode).zfill(2),
            episode_name=episode_name,
            extension=self.extension
        )


    def search_movie(self):
        ai = IMDb()
        try:
            movie = ai.search_movie(self.filename)[0]
            logger.debug("Found movie {}".format(movie['title']))
        except IndexError:
            logger.warning("Looks like IMDB didn't respond. Falling back to split.")
            movie_list = re.split(r'\s\(', self.filename)
            movie = {'title': movie_list[0], 'year': movie_list[1].strip(")")}
        movie_name = movie['title']
        year_of_release = movie['year']
        self.final_filename = self.settings['movie_schema'].format(
            movie_name=movie_name,
            year_of_release = year_of_release,
            extension = self.extension
        )


    def search_audio(self):
        logger.warning("Audio functionality not yet implemented.")
        sys.exit("No functionality.")


def main():
    mParser = MediaManager()
    mParser.parse_file(mParser.filepath)
    for file in mParser.mediaobjs:
        if os.path.isfile(file.source_file):
            logger.debug("Moving {} to {}.".format(file.source_file, file.destination_file))
            returncode = run_rsync(file)
            if returncode == 0:
                logger.debug("rsync successful.")
                try:
                    logger.debug("Updating Plex library.")
                    plex = PlexServer(mParser.settings['plex_url'], mParser.settings['plex_token'])
                    plex.library.update()
                except Exception as e:
                    logger.error(e)
            else:
                logger.error("Problem with rsync.")
        else:
            logger.error("{} is not a real file.".format(mParser.filepath))
    transmission.remove_ratioed_torrents()
    # remove_temp_files()


def run_rsync(file):
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    process = Popen([
        'linux_scripts/rsync.sh',
        file.source_file,
        file.destination_dir.replace(" ", "\\ "),
        file.destination_file.replace(" ", "\\ "),
        file.rsync_user,
        file.rsync_pass
    ], stdout=PIPE, stderr=STDOUT)
    logger.debug(process.stdout.read())
    if process.stderr != None:
        logger.error(process.stderr)
    process.communicate()
    return process.returncode

def change_permission(directory):
    process = Popen(['chmod', "-R", "770", directory], stdout=PIPE, stderr=STDOUT)
    if process.stderr != None:
        logger.error(process.stderr)
    process.communicate()
    return process.returncode