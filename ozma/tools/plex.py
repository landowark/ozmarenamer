from plexapi.server import PlexServer
import logging

logger = logging.getLogger("ozma.plex_randomizer")


def get_all_series_names(plex_url:str, plex_token:str) -> list:
    plex = PlexServer(plex_url, plex_token)
    tv = plex.library.section("TV")
    results = [series.title for series in tv.searchShows()]
    logger.debug(f"Results: {results}")
    return results