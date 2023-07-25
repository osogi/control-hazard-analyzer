import os
import shutil
import stat
from argparse import ArgumentParser, Namespace


class Aggregator:
    def __init__(self):
        self.settings = {"source_folder": "source", "compiled_folder": "dest", "analyse_folder": "analyse"}
        self.settings = Namespace(**self.settings)
        self.shell_parser = None

    def create_folders(self):
        os.makedirs(self.settings.dest_folder, exist_ok=True)
        os.makedirs(os.path.join(self.settings.dest_folder, self.settings.source_folder), exist_ok=True)
        os.makedirs(os.path.join(self.settings.dest_folder, self.settings.compiled_folder), exist_ok=True)
        os.makedirs(os.path.join(self.settings.dest_folder, self.settings.analyse_folder), exist_ok=True)
        os.chmod(self.settings.dest_folder, stat.S_IWRITE)

    def clean_output_folder(self):
        shutil.rmtree(self.settings.dest_folder)

    def run(self):
        print("Aggregate is running. Settings:")
        print(self.settings)

    def configurate(self, settings: Namespace):
        self.settings = settings

    def add_sub_parser(self, sub_parsers) -> ArgumentParser:
        self.shell_parser: ArgumentParser = sub_parsers.add_parser("aggregate", prog="aggregate")

        self.shell_parser.add_argument("--config_file", default="config.json", help="Path to .cfg file")
        self.shell_parser.add_argument(
            "--section_in_config",
            default="DEFAULT",
            help="Set the custom section in config file (DEFAULT by default)",
        )
        self.shell_parser.add_argument(
            "--dest_folder",
            default="out",
            help="Path to dist folder, if not exit it will be created",
        )
        self.shell_parser.add_argument("--Wz", help="Parse arguments for analyze")
        self.shell_parser.add_argument("--Ws", help="Parse arguments for summarize")
        return self.shell_parser
