from __future__ import annotations
from argparse import Namespace
import logging
from pathlib import Path
from typing import Dict

from src.analyzers.backGroundBuildAnalyzer import BGBuildAnalyzer
from src.analyzers.collectors.sshCollector import SshCollector
from src.helpers.backGroundBuilder import BGBuilder
from src.analyzers.patchers.perfPatcher import PerfPatcher
from src.protocols.analyzer import Analyzer


class SshAnalyzer:
    def __init__(self, builder: BGBuilder, settings: Namespace):
        self.settings = settings
        self.builder: BGBuilder = builder
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(self.settings.log_level)

        self.collector: SshCollector = SshCollector(settings)
        self.base: Analyzer = BGBuildAnalyzer(PerfPatcher(settings), self.builder, self.collector, settings)

    def analyze(self, test_dir: Path) -> Dict[str, Dict]:
        return self.base.analyze(test_dir)

    def fin(self) -> None:
        self.collector.fin()
        return self.base.fin()
