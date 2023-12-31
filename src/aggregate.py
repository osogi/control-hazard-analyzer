from pprint import pformat
import logging
import os
import random
import shlex
import shutil
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import List


class Aggregator:
    def __init__(self):
        self.settings = Namespace()
        self.shell_parser = None
        self.logger = logging.getLogger(__name__)

    def clean_output_dir(self):
        shutil.rmtree(self.settings.dest_dir)

    def run(self):
        self.logger.info("Aggregate is running. Settings:")
        self.logger.info(pformat(vars(self.settings)))

        # configure and run generator
        args_generate = shlex.split(self.settings.Wg)
        settings_generate = self.settings.generate.parse_args(args_generate)
        settings_generate.log_level = self.settings.log_level

        self.settings.generate.configurate(settings_generate)
        self.settings.generate.run()

        # configure and run analyzer
        self.output_analyze_dirs: List[str] = []

        for config_file in self.settings.configs:
            full_conf_path: Path = Path(self.settings.path_to_configs).joinpath(config_file)
            if os.access(full_conf_path, mode=os.R_OK):
                args_analyze = shlex.split(self.settings.Wz)
                settings_analyze = self.settings.analyze.parse_args(args_analyze)
                cfg_settings = self.settings.configurator.read_cfg_file(full_conf_path)
                settings_analyze = Namespace(
                    **self.settings.configurator.get_true_settings(
                        self.settings.analyze.analyze_parser,
                        cfg_settings,
                        settings_analyze,
                    )
                )
                sub_dir = f"{settings_analyze.profiler}-{random.getrandbits(16)}"
                if not os.path.isabs(settings_analyze.out_dir):
                    sub_dir = os.path.join(self.settings.dest_dir, sub_dir)
                settings_analyze.out_dir = os.path.join(sub_dir, settings_analyze.out_dir)
                settings_analyze.log_level = self.settings.log_level
                self.settings.analyze.configurate(settings_analyze)
                self.settings.analyze.run()

                self.output_analyze_dirs.append(settings_analyze.out_dir)

        # configure and run summarizer
        args_summarize = shlex.split(self.settings.Ws)
        settings_summarize = self.settings.summarize.parse_args(args_summarize)
        settings_summarize.src_dirs = self.output_analyze_dirs
        settings_summarize.log_level = self.settings.log_level
        settings_summarize.out_dir = os.path.join(self.settings.dest_dir, settings_summarize.out_dir)

        self.settings.summarize.configurate(settings_summarize)
        self.settings.summarize.run()

    def configurate(self, settings: Namespace):
        self.settings = Namespace(**{**vars(settings), **vars(self.settings)})
        self.logger.setLevel(self.settings.log_level)

    def add_sub_parser(self, sub_parsers) -> ArgumentParser:
        self.shell_parser: ArgumentParser = sub_parsers.add_parser("aggregate", prog="aggregate")

        self.shell_parser.add_argument("--config_file", default="config.json", help="Path to .cfg file")
        self.shell_parser.add_argument(
            "--section_in_config",
            default="DEFAULT",
            help="Set the custom section in config file (DEFAULT by default)",
        )
        self.shell_parser.add_argument(
            "--dest_dir",
            default="out",
            help="Path to dist dir, if not exit it will be created",
        )
        self.shell_parser.add_argument("--Wg", default="", help="Pass arguments to generate")
        self.shell_parser.add_argument("--Wz", default="", help="Pass arguments to analyze")
        self.shell_parser.add_argument("--Ws", default="", help="Pass arguments to summarize")
        self.shell_parser.add_argument(
            "--log_level",
            default="WARNING",
            choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            help="Log level of program",
        )
        return self.shell_parser

    def parse_args(self, args: List[str]) -> Namespace:
        return self.shell_parser.parse_known_args(args)[0]
