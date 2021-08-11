import difflib
import re
from datetime import datetime, date
from ssl import SSLCertVerificationError
import jinja2
import wikipedia as wkp
import requests
from bs4 import BeautifulSoup as bs
from pytvdbapi import api
from imdb import IMDb
import requests.exceptions
from pytvdbapi.error import TVDBIndexError, BadData
from ozma.tools.plex import get_all_series_names
from ozma.tools import get_episode_date, move_article_to_end, \
    check_if_television_episode, get_extension, get_media_type, \
    get_parsible_audio_name, remove_extension, split_file_name, check_for_year, strip_list, \
    get_season, get_episode, get_season_episode_dxdd, get_disc, rejected_filenames
from ozma.setup import get_config
import logging
import wordninja as wn


logger = logging.getLogger("ozma.classes")

class MediaObject(object):

    def __init__(self, filepath:str):

        def set_media_type():
            mediatype = get_media_type(self.extension)
            if mediatype == 'video':
                # self.filename, self.season, self.episode, self.disc = get_parsible_video_name(self.filepath)
                # isEpisode = check_if_television_episode(self.source_path)
                if self.season:
                    # If we were able to find a season this is a tv show
                    # mediatype = 'tv'
                    self.__class__ = Episode
                else:
                    # mediatype = 'movies'
                    self.__class__ = Movie
            elif mediatype == "audio":
                pass
            logger.debug(f"Setting media type as {mediatype}.")
            subs_map = {"Episode": "tv", "Movie":"movie", "Song":"music"}
            type = subs_map[self.__class__.__name__]
            print(f"Using media type: {type}")
            self.settings = get_config(section=type)
            try:
                self.schema = jinja2.Template(self.settings[f'{type}_schema'])
            except NameError:
                print("The media object not in the subclasses map.")
                logger.error("The media object not in the subclasses map.")
                temp_settings = self.settings
                del temp_settings['settings']
                self.schema = jinja2.Template("/".join(["{{ " + item + " }}" for item in list(self.settings.keys())]))

        self.source_path = filepath
        self.extension = get_extension(self.source_path)
        set_media_type()

    def create_schema_string(self):
        self.full_file_path = self.schema.render(self.__dict__)

    def get_parsible_video_name(self):
        # remove season number
        filename = remove_extension(split_file_name(self.source_path))
        filename = filename.replace(".", " ")
        # non-greedy regex to remove things in square brackets
        filename = re.sub(re.compile(r'\[.*?\]'), "", filename)
        # Split on year released to remove extraneous info.
        year_released = check_for_year(filename)
        # todo maybe change this to "if filename.etc is not nonetype
        try:
            filename = filename.split(year_released)[0] + year_released
        except TypeError:
            logger.warning("No year found in title, probably a TV show, carrying on.")
        for word in strip_list:
            # regex to remove anything in strip list
            regex = re.compile(r'{}[^\s]*'.format(word), re.IGNORECASE)
            filename = re.sub(regex, "", filename)
        # Seperate method to get season with regex
        season = get_season(filename)
        # Seperate method to get season with regex
        episode = get_episode(filename)
        logger.debug(f"Season: {season}, Episode: {episode}")
        if season and episode:
            # set string containing season/episode with S00E00 format
            seasep = season + episode
            logger.debug(f"Seasep = {seasep}")
            filename = filename.split(seasep)[0].strip()
        # if main method of determining Season/episode didn't work, try dxdd method
        if not season and not episode:
            logger.debug("No season or episode found. Attempting dxdd method.")
            season, episode = get_season_episode_dxdd(filename)
            if season and episode:
                seasep = f"{season}x{episode}"
                filename = filename.split(seasep)[0].strip()
        # if dxdd method didn't work, try with date.
        if not season and not episode:
            logger.debug("No season or episode found. Attempting date method.")
            season = get_episode_date(filename)
            episode = None
            if season:
                filename = filename.split(season)[0].strip()
                try:
                    season = datetime.strptime(season, "%Y %m %d").date()
                except TypeError:
                    logger.debug("No season found.")
        if season:
            try:
                filename = filename.replace(season.upper(), "")
                filename = filename.replace(season.lower(), "")
            except TypeError:
                filename = filename.replace(season.strftime("%Y %m %d"), "")
            except AttributeError:
                filename = filename.replace(season.strftime("%Y %m %d"), "")
            try:
                season = int(season.strip("S"))
            except ValueError:
                season = season
            except AttributeError:
                season = season
        if episode:
            filename = filename.replace(episode.upper(), "")
            filename = filename.replace(episode.lower(), "")
            episode = int(episode.strip("E"))
        # Check for a disc number for whatever reason.
        disc = get_disc(filename)
        if disc:
            filename = filename.replace(disc, "")
            disc = int(disc.strip("D"))
        # Check for a year, should be run after the episode year check.
        year = check_for_year(filename)
        if year:
            filename = filename.replace(year, "")
        # Use word ninja to split apart words that maybe joined due to whitespace errors
        filename = " ".join(wn.split(filename)).title()
        if year: filename = f"{filename} ({year})"
        if filename.lower() in rejected_filenames:
            logger.warning(f"Found a rejected filename: {filename}. Disregarding.")
            filename = None
        logger.debug(f"Using filename={filename}, season={season}, episode={episode}, disc={disc}")
        self.filename = filename
        self.season = season
        self.episode = episode
        self.disc = disc


class Episode(MediaObject):

    # def __init__(self, series_name, season_number, episode_number=""):
    #     super(Episode, self).__init__()
    #     self.series_name = series_name
    #     self.season_number = season_number
    #     self.episode_number = episode_number


    def get_all_info_with_thetvdb(self):
        """
        For this to work we need to get the series name (more for enforcement) and the episode name.
        :param settings: settings dict from config
        :return:
        """
        def get_series_with_thetvdb():
            """
            returns results from thetvdb for the series given during init.
            This is done more to enforce proper naming for the series.
            :return: the series given by thetvdb
            """
            try:
                ai = api.TVDB(self.settings['thetvdbkey'])
            except (ConnectionError, TimeoutError, SSLCertVerificationError):
                series = ""
                logger.error("TVDB did not connect.")
                return None
            try:
                series = ai.search(self.series_name, self.settings['main_language'])
                logger.debug(f"Series search results: {[item.SeriesName for item in series]}")
                try:
                    series = \
                        [item for item in series if item.SeriesName in difflib.get_close_matches(self.series_name,
                                                                                                 [item.SeriesName for
                                                                                                  item in series],
                                                                                                 1)][0]
                except IndexError:
                    logger.error(
                        f"Search on {series} came back empty. Sanitizing using plex to scrape series and retrying.")
                    try:
                        plex_series = get_all_series_names(self.settings['plex_url'], self.settings['plex_token'])
                    except requests.exceptions.ConnectionError:
                        logger.debug("No plex")
                        plex_series = [series.SeriesName]
                    try:
                        series = difflib.get_close_matches(self.series_name, plex_series, 1)[0]
                    except NameError as e:
                        logger.debug(f"We got no plex.")
                        series = self.series_name
                    logger.debug(f"Series returned from plex: {series}")
                    series = self.get_series_with_thetvdb()
            except (TVDBIndexError, UnboundLocalError) as e:
                logger.error(f"Looks like no result was found: {e}")
                return None
            self.api_series = series
            self.series_name = self.api_series.SeriesName


        def get_episode_info_tvdb():
            """
            Gets the episode if it is a straight S00E00 format.
            :param settings:
            :return:
            """
            logger.debug("Using TVDb for episode name.")
            try:
                if isinstance(self.season_number, date):
                    # Checks if season is in datetime format
                    logger.debug(f"Season given as date, using search by date: {self.season_number}.")
                    try:
                        get_episode_by_airdate_tvdb()
                    except BadData as e:
                        logger.error("TVDB returned bad data.")
                else:
                    self.api_episode = self.api_series[self.season_number][self.episode_number]
                self.episode_name = self.api_episode.EpisodeName
                self.airdate = self.api_episode.FirstAired
            except (ConnectionError, TVDBIndexError, TimeoutError, KeyError) as e:
                logger.error(f"Connection error to tvdb: {e}")
                self.get_all_info_with_wikipedia()


        def get_episode_by_airdate_tvdb():
            print(type(self.season_number))
            try:
                self.api_episode = self.api_series.api.get_episode_by_air_date(language=self.settings['main_language'], air_date=self.season_number, series_id=self.api_series.id)
            except Exception as e:
                print(f"Big problem: {e}")
            print(self.api_episode)
            self.season_number = self.api_episode.SeasonNumber
            print(self.api_episode.EpisodeNumber)
            self.episode_number = self.api_episode.EpisodeNumber
            self.episode_name = self.api_episode.EpisodeName
            self.airdate = self.api_episode.FirstAired


        # step one, get the series info
        get_series_with_thetvdb()
        logger.debug(f"Found series {self.api_series.SeriesName}.")
        # once we have a series object we can use it to get episode info.
        # next step, determine if the episode is listed by airdate.
        # if it's not listed by airdate (as most won't)
        get_episode_info_tvdb()
        logger.debug(f"Found episode {self.episode_name}.")

    def get_all_info_with_wikipedia(self):
        wikipedia_page = wkp.page(wkp.search(f"{self.series_name} (Season {self.season_number})")[0])
        page = requests.get(wikipedia_page.url)
        soup = bs(page.content, "html.parser")
        table = soup.find("table", {"class":"wikiepisodetable"})
        try:
            relevent_row = table.findChild("td", string=str(self.episode_number)).findParent("tr")
        except UnboundLocalError as e:
            logger.error(f"Unbound local error when getting relevant row: {e}")
            return "_"
        self.episode_name = relevent_row.findChildren("td")[1].text.replace('"', '')
        self.airdate = datetime.strptime(get_episode_date(relevent_row.findChildren("td")[4].text), "%Y-%m-%d").date()


    def get_all_info_with_IMDb(self):
        ai = IMDb()
        showID = ai.search_movie(self.series_name)[0].getID()
        print(showID)
        page = requests.get(f"http://www.imdb.com/title/tt{showID}/episodes?season={self.season_number}")
        self.soup = bs(page.content, "html.parser")
        if self.episode_number-1 < 0:
            season_index = 0
        else:
            season_index = self.episode_number-1
        episode = self.soup.find_all("div", {"class":"list_item"})[season_index]
        self.episode_name = episode.find("a", {"itemprop":"name"}).get("title")
        self.airdate = datetime.strptime(episode.find("div", {"class":"airdate"}).text.strip(), "%d %b. %Y").date()


    def set_season_and_episode(self):
        self.season_number = str(self.season_number).zfill(2)
        self.episode_number = str(self.episode_number).zfill(2)



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
