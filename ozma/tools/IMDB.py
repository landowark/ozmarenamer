from imdb import IMDb
import logging
from fuzzywuzzy import process
from datetime import datetime


ia = IMDb()

logger = logging.getLogger("ozma.IMDB")

def enforce_unique_dictionary(dictionary:dict):
    result = {}
    for key, value in dictionary.items():
        if key not in result.keys():
            result[key] = value
    return result

def IMDB_episode_search(series_name:str, season_number, episode_number):
    logger.debug("Getting episode with IMDB")
    if isinstance(season_number, str):
        season_number = int(season_number)
    if isinstance(episode_number, str):
        episode_number = int(episode_number)
    series = ia.search_movie(series_name)[0]
    ia.update(series, "episodes")
    episode = series.data['episodes'][season_number][episode_number]
    episode_name = episode.data['title']
    airdate = datetime.strptime(episode.data['original air date'], "%d %b. %Y").date()
    return episode_name, airdate


def enforce_series_with_IMDB(series_name:str):
    logger.debug(f"Enforcing {series_name} series with IMDB")
    potentials = ia.search_movie(series_name)[:2]
    names = [item['long imdb title'] for item in potentials]
    dicto = {}
    for iii, item in enumerate(names):
        dicto[item] = potentials[iii]
    dicto = enforce_unique_dictionary(dicto)
    best_matches = process.extract(series_name, names)
    if best_matches[0][1] > 90:
        if best_matches[1][1] > 90:
            logger.debug(f"Possible 2 best matches, using long name.")
            return dicto[best_matches[0][0]]['long imdb title'].replace("\"", "")
        else:
            return dicto[best_matches[0][0]]['title'].replace("\"", "")
    else:
        logger.debug(f"Didn't  get a very good match for {series_name}, just using the original.")
        return series_name


def check_movie_with_IMDB(movie_title:str, release_year:str=""):
    # movie = ia.search_movie(f"{movie_title} ({release_year})")[0]
    movie = get_movie_from_IMDb_search(movie_title, release_year)
    movie_title = movie['title']
    year_of_release = movie['year']
    return movie_title, year_of_release

def get_movie_from_IMDb_search(movie_title:str, release_year:str):
    candidates = [movie for movie in ia.search_movie(f"{movie_title}") if movie.data['kind'] == "movie"]
    try:
        movie = [item for item in candidates if 'year' in item.keys() and item['year'] == int(release_year)][0]
    except IndexError as e:
        logger.error("Couldn't find movie with that title and release.")
        movie = candidates[0]
    return movie

def IMDB_movie_search(movie_title:str, release_year:str):
    movie = get_movie_from_IMDb_search(movie_title, release_year)
    ia.update(movie)
    director = movie['director'][0]['name']
    starring = [item['name'] for item in movie['cast']][:5]
    return director, starring