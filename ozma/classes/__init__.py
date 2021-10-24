from pathlib import Path, PurePath
from ozma.tools import *
import sys, inspect
import logging
import jinja2
from ozma.tools.muta import *


logger = logging.getLogger(__name__)

class MediaObject(object):

    def __init__(self, filepath):
        self.settings = get_config()
        self.filepath = Path(filepath)
        if 'development' in self.settings:
            self.development = self.settings['development']
        else:
            self.development = False
        if 'move' in self.settings:
            self.move = self.settings['move']
        else:
            self.move = False
        if not self.filepath.exists():
            raise FileNotFoundError("File provided does not actually exist!")
        self.basefile = self.filepath.stem
        self.extension = self.filepath.suffix
        if self.extension not in get_allowed_extensions():
            raise TypeError("That filetype is not allowed in Ozma as of yet.")
        self.parse_media_type()
        self.run_parse()
        self.render_schema()
        self.create_destination()
        self.mutate_file()
        logger.debug(f"We're going to use this object: {self.__dict__}")

    def parse_media_type(self):
        self.media_type = get_media_type(self.extension)
        # create a map of all classes in this module with lower case names as keys
        class_map = {name.lower(): obj for name, obj in inspect.getmembers(sys.modules[__name__]) if
                     inspect.isclass(obj)}
        if self.media_type == "video":
            # Differentiate between TV and Movie if video file
            if check_if_tv(self.basefile):
                self.media_type = "tv"
            else:
                self.media_type = "movie"
        elif self.media_type == "audio":
            # todo possibly try to make audiobooks?
            self.media_type = "song"
        try:
            # cast this class as the class of the found media type
            self.__class__ = class_map[self.media_type]
        except TypeError:
            logger.error(f"Object {class_map[self.media_type]} type is not allowed.")
        # get config settings of the found media type
        try:
            self.class_settings = get_config(section=self.media_type)
        except Exception:
            logger.error(f"Settings for class not found in config file.")


    def run_parse(self):
        logger.debug(f"This is the run parse of the parent class: {self.__class__.__name__}")


    def mutate_file(self):
        logger.debug(f"This is the mutate file of the parent class: {self.__class__.__name__}")

    def render_schema(self):
        schema = jinja2.Template(self.class_settings[f"{self.media_type}_schema"])
        self.final_filename = schema.render(self.__dict__)

    def create_destination(self):
        try:
            schema = jinja2.Template(self.class_settings[f"{self.media_type}_destination"])
        except KeyError:
            logger.debug(f"No specific destination schema found for {self.media_type}. Falling back to destination_dir")
            schema = jinja2.Template(self.settings["destination_dir"])
        final_destination = schema.render(self.__dict__)
        # self.final_destination = PurePath(final_destination, self.final_filename).__str__()
        self.final_destination = final_destination + self.final_filename
        self.final_destination = self.final_destination.replace(":", "")

    def move_file(self):
        if self.final_destination[:3] == "smb":
            logger.debug("We've got a samba destination")
            samba_move_file(self.filepath.__str__(), self.final_destination, self.development)
        else:
            normal_move_file(self.filepath.__str__(), self.final_destination, self.development, self.move)
        # update_libraries()



class TV(MediaObject):

    def run_parse(self):
        # I want to try and enforce the series name with plex if it exists in the config and wikipedia if not.
        self.series_name = enforce_series_name(self.basefile)
        self.season_number, self.episode_number = get_season_and_episode(self.basefile)
        logger.debug("The auth isn't working for thetvdb v4 api ATM so it is being disabled for now.")
        try:
            del self.class_settings['thetvdbkey']
        except KeyError:
            logger.error("Okay, thetvdbkey didn't exist in the first place.")
        self.episode_name, temp_airdate = get_episode_name(self.series_name, self.season_number, self.episode_number, self.class_settings)
        self.airdate = temp_airdate.strftime(self.settings['date_format'])
        self.series_name = move_article_to_end(self.series_name)

    def mutate_file(self):
        mutate_tv(self.__dict__)


class Movie(MediaObject):

    def run_parse(self):
        self.movie_title, self.movie_release_year = check_movie_title(self.basefile)
        self.director, self.starring = get_movie_details(self.movie_title, self.movie_release_year)
        self.movie_title = move_article_to_end(self.movie_title)

    def mutate_file(self):
        mutate_movie(self.__dict__)


class Song(MediaObject):

    def run_parse(self):
        self.artist_name = move_article_to_end(check_artist_name(self.basefile, song_config=self.class_settings))
        self.track_title = check_song_name(self.basefile, self.artist_name, song_config=self.class_settings)
        self.album_name, self.track_number = get_song_details(self.artist_name, self.track_title, self.class_settings)

    def mutate_file(self):
        mutate_song(self.__dict__)