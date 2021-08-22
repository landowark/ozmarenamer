from plexapi.server import PlexServer
import logging
from fuzzywuzzy import process

logger = logging.getLogger("ozma.plex_randomizer")


def get_all_series_names(plex_url:str, plex_token:str) -> list:
    plex = PlexServer(plex_url, plex_token)
    tv = plex.library.section("TV")
    results = [series.title for series in tv.searchShows()]
    logger.debug(f"Results: {results}")
    return results


def enforce_series_with_plex(series_name:str, plex_config:dict):
    plex_series = get_all_series_names(plex_config['plex_url'], plex_config['plex_token'])
    best_match = process.extract(series_name, plex_series)[0]
    if best_match[1] > 90:
        return best_match[0]
    else:
        logger.debug(f"Didn't  get a very good match for {series_name}, just using the original.")
        return series_name