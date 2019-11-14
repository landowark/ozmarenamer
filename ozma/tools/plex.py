from plexapi.server import PlexServer
from plexapi.video import Episode
from plexapi.exceptions import NotFound
import os
from configparser import ConfigParser, ExtendedInterpolation
import random
import re
import logging
from ozma import config


plex_url = config['plex_url']
plex_token = config['plex_token']
plex = PlexServer(plex_url, plex_token)
tv = plex.library.section("TV Shows")
playlist_name = config['playlist_name']

wanted_shows = config['wanted_shows'].split(",")

this_dir = os.path.abspath(os.path.dirname(__file__))
episode_file = "potential_episodes.txt"

logger = logging.getLogger("ozma.plex_randomizer")


def delete_old_playlist():
    try:
        plex.playlist(playlist_name).delete()
    except NotFound:
        pass


def get_five_random_episodes(episodes:list):
    to_add = []
    for iii in range(5):
        choice = random.choice(episodes)
        episodes.remove(choice)
        to_add.append(choice.rstrip("\n"))
    playlist = [get_episode_by_SXXEXX(item) for item in to_add]
    return playlist, episodes


def create_potential_episodes(filename:str=episode_file):
    episodes = [item for show in [show for show in tv.searchShows() if show.title in wanted_shows] for item in
                show.episodes()]
    episodes = ['{}:{}\n'.format(item.show().title, item.seasonEpisode) for item in episodes]
    write_list_to_file(episodes, filename=filename)


def read_episodes_from_file(filename:str=episode_file) -> list:
    infile = os.path.join(this_dir, filename)
    with open(infile, 'r') as f:
        episodes = f.read().splitlines()
    return episodes


def write_list_to_file(episode_list:list, filename:str=episode_file):
    outfile = os.path.join(this_dir, filename)
    with open(outfile, 'w') as f:
        for item in episode_list:
            f.write(item)


def get_episode_by_SXXEXX(episode:str) -> Episode:
    re_season = re.compile(r"s(\d+)")
    re_episode = re.compile(r"e(\d+)")
    episode = episode.split(":")
    show = tv.search(episode[0])[0]
    season = int(re_season.match(episode[1]).groups()[0])
    episode = int(re_episode.search(episode[1]).groups()[0])
    return show.episode(season=season, episode=episode)


def create_new_playlist(playlist:list):
    plex.createPlaylist(playlist_name, items=playlist)


if __name__ == "__main__":
    delete_old_playlist()
    try:
        episodes = read_episodes_from_file()
    except FileNotFoundError:
        logger.error("Master episode file not found. Creating new one.")
        create_potential_episodes()
        episodes = read_episodes_from_file()
    if len(episodes) < 5:
        logger.error("Master episode file is too short. Creating new one.")
        create_potential_episodes()
        episodes = read_episodes_from_file()
    playlist, episodes = get_five_random_episodes(episodes)
    logger.debug(f"Your playlist is: {playlist}")
    write_list_to_file([item + "\n" for item in episodes])
    create_new_playlist(playlist)