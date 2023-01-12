from ozma.configure import setup_logger, get_config
from ozma.classes.manager import MediaManager
from ozma.tools import update_libraries


logger = setup_logger()

def main(*args):
    config = dict(**get_config(args[0]['config']))
    # merge args into config, overwriting values in config.
    config.update(args[0])
    if "destination_dir" in args[0].keys():
        # Okay, if a destination dir is given in cli args, just use the basefile in schema
        logger.debug("Got destination dir in cli arguments  .")
        config['override_dest'] = True
    manager = MediaManager(config=config)
    logger.debug(f"Running main with parameters: {config}")


    for file in manager.mediaobjs:
        logger.debug(manager.settings)
        file.move_file()
    update_libraries()