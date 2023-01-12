"""
Checks wikipedia as a last resort to get episodes.
"""
import re

import requests
import wikipedia as wkp
from bs4 import BeautifulSoup as bs
import logging
from datetime import datetime
from fuzzywuzzy import process
from urllib.parse import urljoin

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

def wikipedia_artist_search(basefile:str):
    # Runs wiki search and gets first match with 'discography' in the name.
    try:
        search = [item for item in wkp.search(basefile) if "discography" in item][0]
    except IndexError:
        logger.error("No discography found in wikipedia. Falling back to best match with song & strip.")
        search = process.extractOne(basefile, [item for item in wkp.search(basefile)], score_cutoff=90)[0]
        search = re.findall(r"(\(.+ song\))", search)[0].strip("(").strip("song)").strip()
    artist = re.sub(r"(albums)?(singles)? discography", "", search).strip()
    return re.sub(r"\(.+\)", "", artist).strip()


def wikipedia_song_search(basefile:str, artist:str)->str:
    song = basefile.replace(artist, "")
    try:
        search = [item for item in wkp.search(song) if f"({artist} song)" in item][0]
    except IndexError:
        logger.error("Song not found for artist, falling back to best match.")
        print(wkp.search(song))
        search = process.extractOne(song, [item for item in wkp.search(song)], score_cutoff=90)[0]
    return re.sub(r"\(.+\)", "", search).strip()


def wikipedia_song_details(artist_name:str, song_title:str):
    try:
        soup = bs(wkp.page([item for item in wkp.search(f"{artist_name} {song_title}") \
                            if "List of songs" in item][0]).html(), "html.parser")
        return using_list_of_songs(song_title, soup)
    except IndexError:
        logger.error(f"No 'List of songs' for {artist_name}.")
        # soup = bs(wkp.page([item for item in wkp.search(f"{artist_name} {song_title}") \
        #                     if f"({artist_name} song)" in item][0]).html(), "html.parser")
        return None, None, None, None


def using_list_of_songs(song_title, soup):
    table = \
        [item for item in soup.find_all("table", {"class": ["wikitable", "sortable"]}) if "sortable" in item['class']][0]
    try:
        relevant_row = table.findChild("a", string={song_title}).findParent("tr")
    except AttributeError:
        relevant_row = table.findChild("th", string=re.compile(rf'\"{song_title}\"\s?')).findParent("tr")
    details = relevant_row.findAll("td")
    # writer = details[0].text.strip()
    album = details[1].text.strip()
    # release_year = details[2].text.strip()
    track_number = wikipedia_album_search(details[1].findChild("a")['href'])
    return album, track_number



def wikipedia_album_search(wiki_url:str, song_title:str):
    req_url = urljoin("https://en.wikipedia.org", wiki_url)
    page = requests.get(req_url)
    soup = bs(page.content, "html.parser")
    tables = soup.find_all("table", {"class":"tracklist"})
    # flatten tracklist if sides are indicated
    track_list = [item.findParent().text for sublist in
                 [table.findChildren("th", {"id": re.compile(r"track\d")}) for table in tables] for item in sublist]
    track_number = [i for i, s in enumerate(track_list) if f'"{song_title}"' in s][0]
    return track_number



