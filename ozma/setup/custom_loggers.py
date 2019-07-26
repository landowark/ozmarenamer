import os
import stat
from logging import handlers

class GroupWriteRotatingFileHandler(handlers.RotatingFileHandler):

    def doRollover(self):
        """
        Override base class method to make the new log file group writable.
        """
        # Rotate the file first.
        handlers.RotatingFileHandler.doRollover(self)

        # Add group write to the current permissions.
        currMode = os.stat(self.baseFilename).st_mode
        os.chmod(self.baseFilename, currMode | stat.S_IWGRP)


class GroupWriteRotatingFileHandler(handlers.RotatingFileHandler):
    def _open(self):
        prevumask=os.umask(0o002)
        #os.fdopen(os.open('/path/to/file', os.O_WRONLY, 0600))
        rtv=handlers.RotatingFileHandler._open(self)
        os.umask(prevumask)
        return rtv