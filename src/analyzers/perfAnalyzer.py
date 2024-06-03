from __future__ import annotations

import logging
from argparse import Namespace
from pathlib import Path
from typing import Dict

from src.analyzers.baseAnalyzer import BaseAnalyzer
from src.analyzers.collectors.perfCollector import PerfCollector
from src.analyzers.patchers.perfPatcher import PerfPatcher
from src.helpers.builder import Builder
from src.protocols.analyzer import Analyzer
from src.protocols.collector import DictSI


class PerfAnalyzer:
    def __init__(self, builder: Builder, settings: Namespace):
        self.settings = settings
        self.builder: Builder = builder
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(self.settings.log_level)

        self.base: Analyzer = BaseAnalyzer(PerfPatcher(settings), self.builder, PerfCollector(settings), settings)

    def analyze(self, test_dir: Path) -> Dict[str, DictSI]:
        return self.base.analyze(test_dir)

    def fin(self) -> None:
        return self.base.fin()
