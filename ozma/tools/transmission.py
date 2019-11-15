from transmission_rpc import Client, DEFAULT_PORT
from ..setup import get_config
import logging
import os

configs = get_config()
logger = logging.getLogger("ozma.transmission")
try:
    c = Client(port=DEFAULT_PORT, user=configs['transmission_user'], password=configs['transmission_pass'])
except Exception as e:
    logger.error(f"Error in getting transmission client: {e}")
try:
    completed_dir = configs['watch_dir']
except Exception as e:
    logger.error(f"Error in finding completed dir in settings: {e}")


def remove_ratioed_torrents():
    logger.debug("Checking torrents.")
    for iii, torrent in enumerate(c.get_torrents()):
        if torrent.ratio >= torrent.seed_ratio_limit:
            logger.debug("Removing torrent: {}".format(torrent._get_name_string().decode('utf-8')))
            # Transmmission uses an index starting at 1 so... iii+1
            c.remove_torrent(iii+1)
            for item in torrent.files():
                if torrent.files()[item]['size'] == torrent.files()[item]['completed'] :
                    # check if file exists
                    file_path = os.path.join(completed_dir, torrent.files()[item]['name'])
                    if os.path.exists(file_path):
                        try:
                            logger.debug(f"Trying to remove {file_path}")
                            os.remove(file_path)
                        except Exception as e:
                            logger.error(f"Couldn't remove file: {file_path} because {e}")
                            continue





