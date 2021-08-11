"""
Checks wikipedia as a last resort to get episodes.
"""

import wikipedia as wkp
import requests
from bs4 import BeautifulSoup as bs
import logging
import datetime

logger = logging.getLogger("ozma.tv_wikipedia")


def wikipedia_tv_episode_search(show: str, season, episode: int):
    page = wkp.page(wkp.search(f"List of {show} episodes")[0])
    if isinstance(season, str):
        season = int(season)
    print(season)
    # The Simpsons required two wikipedia pages... so...
    if show == "Simpsons, The" and season <=20:
        url = page.url + "_(seasons_1–20)#Episodes"
    elif show == "Daily Show, The" or isinstance(season, datetime.date):
        # Need to build some functionality for this one.
        return "_"
    else:
        url = page.url
    soup = bs(requests.get(url).content, "html.parser")
    table_title = soup.find("span", id=lambda x: x and f"Season_{season}" in x)
    try:
        table = table_title.find_parent("h3").find_next_sibling("table")
    except AttributeError as e:
        logger.error(f"Attribute error getting table: {e}")
        return "_"
    try:
        relevent_row = table.findChild("td", string=str(episode)).findParent("tr")
    except UnboundLocalError as e:
        logger.error(f"Unbound local error when getting relevant row: {e}")
        return "_"
    episode_title = relevent_row.findChildren("td")[1].text
    return episode_title