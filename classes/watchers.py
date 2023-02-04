from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from tools import extensions
from classes.manager import MediaManager
from tools.plex import update_plex_library
from pathlib import Path

import logging
logger = logging.getLogger(f"ozma.{__name__}")

class Handler(PatternMatchingEventHandler):
    def __init__(self, ctx:dict):
        self.ctx = ctx
        # Set the patterns for PatternMatchingEventHandler
        wanted = [f"*{item}" for sublist in [extensions[ext] for ext in extensions] for item in sublist]
        PatternMatchingEventHandler.__init__(self, patterns=wanted,
                                                             ignore_directories=True, 
                                                             case_sensitive=False)
  
    def on_created(self, event):
        logger.debug("Watchdog received created event - % s." % event.src_path)
        # Event is created, you can process it now
        self.ctx['filepaths'] = [Path(event.src_path)]
        manager = MediaManager(**self.ctx)
        for obj in manager.mediaobjs:
            obj.move_file()
        if 'plex' in self.ctx:
            update_plex_library(self.ctx['plex'])

    def on_modified(self, event):
        print("Watchdog received modified event - % s." % event.src_path)
        # Event is modified, you can process it now
    
    # @staticmethod
    # def on_any_event(event):
    #     if event.is_directory:
    #         return None
  
    #     elif event.event_type == 'created':
    #         # Event is created, you can process it now
    #         print("Watchdog received created event - % s." % event.src_path)
    #     elif event.event_type == 'modified':
    #         # Event is modified, you can process it now
    #         print("Watchdog received modified event - % s." % event.src_path)