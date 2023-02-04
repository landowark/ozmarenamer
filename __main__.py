import time
import click
import logging
from pathlib import Path
from typing import List
from configure import setup_logger, get_config, set_logger_verbosity
from classes.manager import MediaManager
from classes.watchers import Handler
from watchdog.observers import Observer
from tools.plex import update_plex_library

logger = setup_logger()

# logger = logging.getLogger("ozma")


@click.group("cli")
@click.option('--config', "-c", default="", type=str, help="Path to the config.yml file.")
@click.option('--verbose', "-v", count=True)
@click.pass_context
def cli(ctx, config: str, verbose):
    """Main click command

    Args:
        ctx: context object from click
        config (str): configuration path (for overwrite)
        verbose (bool): set log level to verbose

    Returns:
        args: all configuration arguments.
    """
    print(f"Verbosity set to : {verbose}")
    if verbose:
        set_logger_verbosity(verbosity=verbose)
    # logger.debug(get_config(settings_path=config))
        print(f"Logging level set to: {logger.getEffectiveLevel()}")
    ctx.obj = {**get_config(settings_path=config), **ctx.__dict__['params']}


@cli.command("rename")
@click.argument('filepaths', type=click.Path(exists=True), nargs=-1)
@click.option("--move", "-m", is_flag=True, help="Move instead of copy.")
@click.option("--mutate", is_flag=True, help="Mutate file metadata.")
@click.option("--dry-run", is_flag=True, help="Print new file names only.")
@click.option("--override-directory", "-o", type=click.Path(exists=True), help="")
@click.pass_context
def rename(ctx, filepaths: List[Path], move: bool, mutate: bool, dry_run: bool, override_directory: str):
    ctx.obj['filepaths'] = [Path(filepath) for filepath in filepaths]
    ctx.obj['dry_run'] = dry_run
    ctx.obj['move'] = move
    ctx.obj['mutate'] = mutate
    if override_directory != None:
        ctx.obj['destination_dir'] = override_directory
    logger.debug(f"The input files are {ctx.obj['filepaths']}")
    manager = MediaManager(**ctx.obj)
    # logger.debug(f"Manager: {handler.__dict__}")
    for obj in manager.mediaobjs:
        obj.move_file()
    if 'plex' in ctx:
        update_plex_library(ctx['plex'])

    # rename(context=ctx.obj)


@cli.command("daemon")
@click.argument('directory', type=click.Path(exists=True))
@click.option("--move", "-m", is_flag=True, help="Move instead of copy.")
@click.option("--mutate", is_flag=True, help="Mutate file metadata.")
@click.pass_context
def daemon(ctx, directory, move: bool, mutate: bool):
    ctx.obj['move'] = move
    ctx.obj['mutate'] = mutate
    handler = Handler(ctx=ctx.obj)
    handler.on_create = watchdog_bridger
    observer = Observer()
    observer.schedule(handler, directory, recursive=True)
    observer.start()
    try:
      while True:
        time.sleep(1)
    except KeyboardInterrupt:
      observer.stop()
      observer.join()
    

@cli.command("test")
@click.pass_context
def test(ctx):
    print(ctx.obj)


def watchdog_bridger(event:str):
    logger.debug(event)


def rename(context: dict):
    # Set kwargs to key:value pairs in context
    manager = MediaManager(**context)
    # logger.debug(f"Manager: {handler.__dict__}")
    for obj in manager.mediaobjs:
        obj.move_file()




if __name__ == "__main__":
    cli()
