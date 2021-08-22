"""
Checks wikipedia as a last resort to get episodes.
"""
import re

import wikipedia as wkp
from bs4 import BeautifulSoup as bs
import logging
from datetime import datetime
from fuzzywuzzy import process

logger = logging.getLogger("ozma.tv_wikipedia")


def wikipedia_tv_episode_search(series_name:str, season_number, episode_number):
    logger.debug("Using wikipedia for episode search")
    wikipedia_page = wkp.page(wkp.search(f"{series_name} (Season {season_number})")[0])
    soup = bs(wikipedia_page.html(), "html.parser")
    table = soup.find("table", {"class": "wikiepisodetable"})
    try:
        relevent_row = table.findChild("td", string=str(episode_number)).findParent("tr")
    except UnboundLocalError as e:
        logger.error(f"Unbound local error when getting relevant row: {e}")
        return "_"
    episode_name = relevent_row.findChildren("td")[1].text.replace('"', '')
    airdate = datetime.strptime(re.findall(r"\(.+\)", relevent_row.findChildren("td")[4].text)[0][1:-1], "%Y-%m-%d").date()
    return episode_name, airdate


def enforce_series_with_wikipedia(series_name:str)->str:
    logger.debug("Using wikipedia to enforce series name.")
    wiki_pages = [item for item in wkp.search(series_name) if "(" not in item and "List" not in item][0]
    best_match = process.extract(series_name, wiki_pages)[0]
    if best_match[1] > 90:
        return best_match[0]
    else:
        logger.debug(f"Didn't  get a very good match for {series_name}, just using the original.")
        return series_name


def check_movie_with_wikipedia(movie_title:str, release_year:str=""):
    wiki_search = wkp.search(f"{movie_title} ({release_year} film)")[0]
    year_raw = re.findall(r"\(.+\)", wiki_search)[0]
    movie_title = wiki_search.strip(year_raw).strip()
    year_of_release = re.findall(r'(20\d{2}|19\d{2})', year_raw)[0]
    return movie_title, year_of_release


def wikipedia_movie_search(movie_title:str, release_year:str):
    wikipedia_page = wkp.page(wkp.search(f"{movie_title} ({release_year} film)")[0])
    soup = bs(wikipedia_page.html(), "html.parser")
    table = soup.find("table", {"class": "infobox"})
    director = table.findChild("th", string="Directed by").find_next_sibling().text
    starring = table.findChild("th", string="Starring").find_next_sibling().text.strip().splitlines()
    return director, starring

