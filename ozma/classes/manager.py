import os
import logging
from ozma.tools import extract_files_if_folder
from ozma.classes import MediaObject

logger = logging.getLogger(__name__)

class MediaManager(object):

    def __init__(self, config:dict):
        self.settings = config
        logger.debug(f"Here are the MediaManager settings: {self.__dict__}")
        # Where the origin file is
        self.mediaobjs = []
        self.load_files(config['filename'])

    def load_files(self, filepath):
        if os.path.isdir(filepath):
            logger.debug(f"Filepath {filepath} is a directory, extracting files.")
            file_list = extract_files_if_folder(dir_path=filepath)
            if file_list != []:
                logger.debug("Look out, it's recursion time!")
                # todo I've a bug. The first run through uses the specified config file, but the recursion falls back to
                for file in file_list:
                    self.load_files(filepath=file)
            else:
                logger.error(f"There are no appropriate files in {filepath}")
        else:
            new_medObj = MediaObject(filepath=filepath, config=self.settings)
            self.mediaobjs.append(new_medObj)