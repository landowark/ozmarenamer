from ozma.setup import setup_logger, get_config
from ozma.classes.manager import MediaManager
from ozma.tools import update_libraries


logger = setup_logger()

def main(*args):
    config = dict(**get_config(args[0]['config']))
    # merge args into config, overwriting values in config.
    config.update(args[0])
    logger.debug(f"Running main with parameters: {config}")
    manager = MediaManager(config=config)
    for file in manager.mediaobjs:
        logger.debug(manager.settings)
        file.move_file()
    update_libraries()