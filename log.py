# Imports
import logging
from datetime import datetime


def get_today():
    return datetime.now().strftime("[%d/%m/%Y-%H:%M:%S]")

class Logger:
    def __init__(self, ltype, filename):
        # 0 = Client
        # 1 = Server
        self.type = 0 if ltype else 1
        self.headerFormat = get_today() + "-Client> " if ltype else get_today() + "-Server> "
        logging.basicConfig(level=logging.WARNING, filename=filename, filemode='w', format=self.headerFormat + '%(message)s')

    def log_this(self, message):
        print(self.headerFormat + message)
        logging.warning(message)
