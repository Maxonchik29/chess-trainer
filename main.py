import sys


class Tee:
    def __init__(self, *files):
        self.files = files

    def write(self, text):
        for file in self.files:
            file.write(text)
            file.flush()

    def flush(self):
        for file in self.files:
            file.flush()


log_file = open(
    "analysis_log.txt",
    "w",
    encoding="utf-8"
)

sys.stdout = Tee(sys.__stdout__, log_file)


from app.main_window import *
from app.history_window import open_history