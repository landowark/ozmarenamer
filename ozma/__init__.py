from ozma.setup import setup_logger, get_config
from ozma.classes.manager import MediaManager


logger = setup_logger()

def main(*args):
    config = dict(**get_config(args[0]['config']))
    # merge args into config, overwriting values in config.
    config.update(args[0])
    logger.debug(f"Running main with parameters: {config}")
    manager = MediaManager(config=config)
    for file in manager.mediaobjs:
        file.move_file()