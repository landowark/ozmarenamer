import logging
from imdb import IMDb
import re
from ozma.tools import move_article_to_end, escape_specials, check_for_year
from ozma.classes import MediaObject

logger = logging.getLogger("ozma.classes.episode")
logger.setLevel(logging.DEBUG)

class Movie(MediaObject):

    def __init__(self, movie_title, year="", **kwargs):
        super(Movie, self).__init__(**kwargs)
        self.movie_title = movie_title
        self.movie_release_year = year


    def get_all_info_with_imdb(self):
        """
        Gets movie info from imdb
        :param settings: the settings file
        :return:
        """
        ai = IMDb()
        searched_movie = ai.search_movie(self.movie_title)[0]
        logger.debug(f"Found movie {searched_movie['title']}")
        self.movie_title = searched_movie['title']
        self.movie_release_year = searched_movie['year']
        logger.debug(f"Using movie name {searched_movie['title']}")
        # Remove any extra instances of the movie's year.
        year_regex = re.compile(r'\({year}\)'.format(year=searched_movie['year']))
        self.movie_title = year_regex.sub("", self.movie_title)
        director_regex = re.compile(r"Directors? Cut", re.IGNORECASE)
        self.movie_title = director_regex.sub("(Director Cut)", self.movie_title)
        # ensure 'the', 'an', 'a', etc is moved to the end of the movie name.
        self.movie_title = move_article_to_end(self.movie_title)

        def get_closest_movie(movie_title, movie_list):
            pass
