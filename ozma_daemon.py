#!/opt/anaconda/envs/writing_scraper/bin/python


'''
The idea for this is to have a file watcher watch the directory set in the settings file. When it comes across a suitable
file it will call ozma.main on that file.
'''

from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
import os
import logging
import time
from ozma import main
from ozma.setup import get_config, get_allowed_extensions

# Logging setup
dirname = os.path.dirname(os.path.dirname(__file__))
logger = logging.getLogger("ozma.watcher")
config = get_config()

def handle_file(event):
    logger.debug("Event triggered for {}".format(event.src_path))
    main(filename=event.src_path)


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    # Create an event handler
    patterns = [f"*.{item}" for item in get_allowed_extensions()]
    ignore_patterns = ""
    ignore_directories = False
    case_sensitive = False

    # Define what to do when some change occurs
    my_event_handler = PatternMatchingEventHandler(patterns, ignore_patterns, ignore_directories, case_sensitive)
    my_event_handler.on_created = handle_file
    my_event_handler.on_modified = handle_file


    # Create an observer
    path = config['watch_dir']
    go_recursively = True

    my_observer = Observer()
    my_observer.schedule(my_event_handler, path, recursive=go_recursively)

    # Start the observer
    my_observer.start()
    logger.info("Ozma watcher has started on {}.".format(path))
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        my_observer.stop()
    my_observer.join()