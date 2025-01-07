import os


class ETDHandler:
    def __init__(self):
        self.base_dir = os.path.join(os.path.expanduser("~"), ".etd")
        self.ensure_directory()

    def ensure_directory(self):
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)

    def get_path(self, filename):
        return os.path.join(self.base_dir, filename)
