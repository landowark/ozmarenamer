import requests
from lxml import html
import re
from typing import List
from dateutil import parser
import logging

logger = logging.getLogger(f"ozma.{__name__}")

class IMDBSearch(object):

    def __init__(self, title, default: bool = True):
        self.id = None
        self.title = title
        self.base_url = "https://www.imdb.com"
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 6.1; rv:2.2) Gecko/20110201'}
        url = f"{self.base_url}/search/title/?title={title}"
        self.response = requests.get(url=url, headers=self.headers)
        self.items: List[html.Element] = html.fromstring(self.response.content).xpath('//a[@class="ipc-title-link-wrapper"]')
        self.cast = []
        self.director = None
        self.release_date = None
        self.runtime = "0m"
        if default:
            self.full_html = self.get_full_item()
            self.cast = self.get_cast()
            self.director = self.get_director()
            self.release_date, self.runtime = self.get_basic_info()

    def __repr__(self):
        return f"IMDB<{self.title}>"

    def check_items(self) -> List[str]:
        return [re.sub(r"^\d\.\s", "", t.text_content()) for t in self.items]

    def get_full_item(self, index: int = 0) -> str:
        item = self.items[index]
        url = f"{self.base_url}{item.values()[0]}"
        m = re.search(r"^/title/(?P<id>.*)/", item.values()[0])
        self.id = m.groupdict()['id']
        self.response = requests.get(url=url, headers=self.headers)
        return self.response.content

    def get_basic_info(self):
        tree = html.fromstring(self.full_html)
        runs = tree.xpath('//li[@class="ipc-inline-list__item"]')
        runtime = [item.text for item in runs if item.text is not None][0]
        release = tree.xpath('//a[@class="ipc-link ipc-link--baseAlt ipc-link--inherit-color"]')
        release = [re.search(r"\d{4}", item.text) for item in release if item.text is not None]
        release_date = [item.group() for item in release if item is not None][0]
        logger.debug(f"Elements: {tree}")
        return release_date, runtime

    def get_cast(self):
        return [item.text for item in html.fromstring(self.full_html).xpath('//a[@data-testid="title-cast-item__actor"]')]

    def get_director(self):
        try:
            return html.fromstring(self.response.content).xpath('//a[@class="ipc-metadata-list-item__list-content-item ipc-metadata-list-item__list-content-item--link"]')[0].text_content()
        except:
            return None

    def find_episode(self, season: str | int, episode: str | int):
        url = f"{self.base_url}/title/{self.id}/episodes/?season={str(season)}"
        response = requests.get(url=url, headers=self.headers)
        # return response
        tree = html.fromstring(response.content).xpath('//a[@class="ipc-title-link-wrapper"]')
        element = tree[episode - 1]
        return Episode(url=f"{self.base_url}{element.values()[0]}", element=element)

class Episode(object):

    def __init__(self, url: str, element: html.Element):
        self.url = url
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 6.1; rv:2.2) Gecko/20110201'}
        m = re.search(r"^S(?P<season>\d+).E(?P<episode>\d+) ∙ (?P<title>.*)$", element.text_content()).groupdict()
        self.episode = str(m['episode']).zfill(2)
        self.season = str(m['season']).zfill(2)
        self.title = m['title']
        self.response = requests.get(self.url, headers=self.headers)
        self.cast = self.fetch_cast()
        self.date_aired, self.runtime = self.fetch_update_episode()
        self.director = self.fetch_director()

    def __repr__(self):
        return f"Episode<{self.title}>"

    def fetch_update_episode(self):
        tree = html.fromstring(self.response.content).xpath('//li[contains(@class, "ipc-inline-list__item")]')
        basic_info = [item.text for item in tree if item.text is not None]
        if len(basic_info) < 1:
            return None, None
        date_aired = parser.parse(basic_info[0].replace('Episode aired ', "")).date()
        try:
            runtime = basic_info[1]
        except IndexError:
            runtime = "0m"
        return date_aired, runtime

    def fetch_cast(self):
        return [item.text for item in html.fromstring(self.response.content).xpath('//a[@data-testid="title-cast-item__actor"]')]

    def fetch_director(self):
        return html.fromstring(self.response.content).xpath('//a[@class="ipc-metadata-list-item__list-content-item ipc-metadata-list-item__list-content-item--link"]')[0].text_content()
