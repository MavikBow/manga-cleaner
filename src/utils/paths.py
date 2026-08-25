import os
import sys

#/////////////////////////////////#
#      FILESYSTEM ARCHITECT       #
#/////////////////////////////////#

class Paths:
    if getattr(sys, 'frozen', False):
        BASE_DIR = os.path.dirname(sys.executable)
        BUNDLE_DIR = sys._MEIPASS # Points specifically to the _internal folder
    else:
        BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        BUNDLE_DIR = BASE_DIR

    MODELS = os.path.join(BASE_DIR, "models")
    LOGS = os.path.join(BASE_DIR, "logs")
    CACHE = os.path.join(BASE_DIR, "cache")
    PROCESSED = os.path.join(BASE_DIR, "processed")

    @staticmethod
    def initialize():
        for p in [Paths.MODELS, Paths.LOGS, Paths.CACHE, Paths.PROCESSED]:
            if not os.path.exists(p):
                os.makedirs(p)

    @staticmethod
    def get_model(name):
        return os.path.join(Paths.MODELS, name)
