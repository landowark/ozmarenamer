import pylast as pyl
import logging
import re
from fuzzywuzzy import process

logger = logging.getLogger(__name__)

def check_artist_with_lastfm(basefile:str, settings:dict, **kwargs):
    try:
        basefile = re.split(r"by", basefile, flags=re.I)[1].strip()
    except IndexError:
        basefile = re.split(r"–|-", basefile, flags=re.I)[0].strip()
    ai = pyl.LastFMNetwork(api_key=settings['lastfmkey'], api_secret=settings['lastfmsec'])
    # searched_artist = pyl.ArtistSearch(artist_name=basefile, network=ai).get_next_page()[0].get_name().split("-")[0].strip()
    searched_artist = [artist.get_name() for artist in pyl.ArtistSearch(artist_name=basefile, network=ai).get_next_page()][0]
    print(searched_artist)
    # searched_artist = process.extractOne(basefile, searched_artists)[0].title()
    searched_artist = re.split("–|-", searched_artist)[0].strip()
    searched_artist = re.sub(f"\(.+\)", "", searched_artist).strip()
    logger.debug(f"Returning {searched_artist} as searched artist.")
    return searched_artist


def check_song_name_with_lastfm(basefile:str, artist_name:str, settings:dict):
    try:
        basefile = re.split(r"by", basefile, flags=re.I)[0].strip()
    except IndexError:
        basefile = re.split(r"–|-", basefile, flags=re.I)[1].strip()
    ai = pyl.LastFMNetwork(api_key=settings['lastfmkey'], api_secret=settings['lastfmsec'])
    # check what kind of artist variable we're being passed.
    track = pyl.TrackSearch(artist_name=artist_name, track_title=basefile, network=ai).get_next_page()[0]
    return track.get_name()

def lastfm_song_details(artist_name:str, song_title:str, settings:dict):
    ai = pyl.LastFMNetwork(api_key=settings['lastfmkey'], api_secret=settings['lastfmsec'])
    # check what kind of artist variable we're being passed.
    track = pyl.TrackSearch(artist_name=artist_name, track_title=song_title, network=ai).get_next_page()[0]
    # writer = details[0].text.strip()
    album = track.get_album().get_name()
    # release_year = details[2].text.strip()
    track_number = [i for i, x in enumerate([track.get_name().lower() for track in track.get_album().get_tracks()]) if x == song_title.lower()][0]
    return album, track_number
