from transmission_rpc import Client, DEFAULT_PORT
from ..setup import get_config
import logging

configs = get_config()
logger = logging.getLogger("ozma.transmission")
try:
    c = Client(port=DEFAULT_PORT, user=configs['transmission_user'], password=configs['transmission_pass'])
except Exception as e:
    logger.error(e)


def remove_ratioed_torrents():
    logger.debug("Checking torrents.")
    for iii, torrent in enumerate(c.get_torrents()):
        if torrent.ratio >= torrent.seed_ratio_limit:
            logger.debug("Removing torrent: {}".format(torrent._get_name_string().decode('utf-8')))
            # Transmmission uses an index starting at 1 so... iii+1
            c.remove_torrent(iii+1)




