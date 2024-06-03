import logging
from argparse import Namespace
from pathlib import Path
from typing import Dict

from src.analyzers.baseAnalyzer import BaseAnalyzer
from src.analyzers.collectors.gemCollector import GemCollector
from src.analyzers.patchers.gemPatcher import GemPatcher
from src.helpers.builder import Builder
from src.protocols.analyzer import Analyzer
from src.protocols.collector import DictSI


class GemAnalyzer:
    def __init__(self, builder: Builder, settings: Namespace):
        self.settings = settings
        self.builder: Builder = builder
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(self.settings.log_level)

        self.gem5_home = Path(self.settings.__dict__.get("gem5_home", ""))
        self.target_isa = self.settings.__dict__.get("target_isa", "").lower()

        self.build_additional_flags = [
            f"-I{self.gem5_home.joinpath('include')}",
            f"-I{self.gem5_home.joinpath('util/m5/src')}",
            "-fPIE",
            f"-Wl,-L{self.gem5_home}/util/m5/build/{self.target_isa}/out",
            "-Wl,-lm5",
            "--static",
        ]

        if self.target_isa == "":
            raise Exception("No target isa provided")

        self.builder.set_default_additional_flags(self.build_additional_flags)

        self.base: Analyzer = BaseAnalyzer(GemPatcher(settings), self.builder, GemCollector(settings), settings)

    def analyze(self, test_dir: Path) -> Dict[str, DictSI]:
        return self.base.analyze(test_dir)

    def fin(self) -> None:
        return self.base.fin()
