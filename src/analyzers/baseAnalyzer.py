import logging
import shutil
from argparse import Namespace
from pathlib import Path
from tempfile import mkdtemp
from typing import Dict

from src.helpers.builder import Builder
from src.protocols.collector import Collector, DictSI
from src.protocols.patcher import Patcher


class BaseAnalyzer:
    def __init__(
        self,
        patcher: Patcher,
        builder: Builder,
        collector: Collector,
        settings: Namespace,
    ):
        self.settings = settings
        self.patcher = patcher
        self.collector = collector
        self.builder = builder

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(self.settings.log_level)

        self.temp_dir: Path = Path(mkdtemp())

    def fin(self) -> None:
        shutil.rmtree(self.temp_dir)

    def analyze(self, test_dir: Path) -> Dict[str, DictSI]:
        src_dir = self.temp_dir.joinpath("src/")
        build_dir = self.temp_dir.joinpath("bins/")

        self.patcher.patch(test_dir, src_dir)
        self.builder.build_dir(src_dir, build_dir)
        res = self.collector.collect(build_dir)
        return res
