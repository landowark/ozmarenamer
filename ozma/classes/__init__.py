from pathlib import Path
from ozma.tools import *
import sys, inspect
import logging
import jinja2


logger = logging.getLogger(__name__)

class MediaObject(object):

    def __init__(self, filepath):
        self.settings = get_config()
        self.filepath = Path(filepath)
        if not self.filepath.exists():
            raise FileNotFoundError("File provided does not actually exist!")
        self.basefile = self.filepath.stem
        self.extension = self.filepath.suffix
        if self.extension not in get_allowed_extensions():
            raise TypeError("That filetype is not allowed in Ozma as of yet.")
        self.parse_media_type()
        self.run_parse()
        self.render_schema()

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


    def render_schema(self):
        self.schema = jinja2.Template(self.class_settings[f"{self.media_type}_schema"])
        self.final_filename = self.schema.render(self.__dict__)



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


class Movie(MediaObject):

    def run_parse(self):
        self.movie_title, self.movie_release_year = check_movie_title(self.basefile)
        self.director, self.starring = get_movie_details(self.movie_title, self.movie_release_year)
