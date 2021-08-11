import difflib
from datetime import datetime, date
from ssl import SSLCertVerificationError
import logging
import wikipedia as wkp
import requests
from bs4 import BeautifulSoup as bs
# import pytvdbapi.api
from pytvdbapi import api
from imdb import IMDb
import requests.exceptions
from pytvdbapi.error import TVDBIndexError, BadData
from ozma.tools.plex import get_all_series_names
from ozma.tools import get_episode_date
from ozma.classes import MediaObject

logger = logging.getLogger("ozma.classes.episode")
logger.setLevel(logging.DEBUG)


class Episode(MediaObject):

    def __init__(self, series_name, season_number, episode_number=""):
        super(Episode, self).__init__()
        self.series_name = series_name
        self.season_number = season_number
        self.episode_number = episode_number

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