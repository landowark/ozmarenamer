import os
import logging
from tools import extract_files_if_folder
from classes.media import MediaObject
from pathlib import Path
from time import sleep

logger = logging.getLogger(f"ozma.{__name__}")

class MediaManager(object):

    def __init__(self, **kwargs):
        for kwarg in kwargs:
            setattr(self, kwarg, kwargs[kwarg])
        logger.debug(f"Here are the MediaManager settings: {self.__dict__}")
        # Where the origin file is
        self.mediaobjs = []
        self.load_files()


    def load_files(self, file:Path|None=None):
        if file is None:
            for iii, filepath in enumerate(self.filepaths):
                if filepath.is_dir():
                    logger.debug(f"Filepath {filepath} is a directory, extracting files.")
                    file_list = extract_files_if_folder(dir_path=filepath)
                    if file_list != []:
                        logger.debug("Look out, it's recursion time!")
                        # todo I've a bug. The first run through uses the specified config file, but the recursion falls back to
                        for file in file_list:
                            self.load_files(file=file)
                    else:
                        logger.error(f"There are no appropriate files in {filepath}")
                else:
                    new_medObj = MediaObject(filepath=filepath, **self.__dict__)
                    self.mediaobjs.append(new_medObj)
        else:
            new_medObj = MediaObject(filepath=file, **self.__dict__)
            self.mediaobjs.append(new_medObj)
