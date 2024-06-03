import logging
import shlex
import shutil
from argparse import ArgumentParser, Namespace
from pathlib import Path
from pprint import pformat
from typing import Dict, List

from src.analyzers.gemAnalyzer import GemAnalyzer
from src.analyzers.perfAnalyzer import PerfAnalyzer
from src.analyzers.sshAnalyzer import SshAnalyzer
from src.helpers.backGroundBuilder import BGBuilder
from src.helpers.builder import Builder
from src.helpers.packer import Packer
from src.protocols.analyzer import Analyzer
from src.protocols.collector import DictSI
from src.protocols.subparser import SubParser


class Analyze:
    def __init__(self) -> None:
        self.analyzer: Analyzer | None = None
        self.packer = Packer()
        self.builder: Builder | None = None
        self.test_dir: Path | None = None
        self.analyze_dir: Path | None = None
        self.settings: Namespace | None = None
        self.logger = logging.getLogger(__name__)

    def configurate(self, settings: Namespace) -> None:
        self.settings = settings
        self.logger.setLevel(self.settings.log_level)
        self.test_dir = Path(settings.test_dir)
        self.analyze_dir = Path(settings.out_dir)
        self.settings.compiler_args = shlex.split(settings.compiler_args)
        self.builder = Builder(self.settings)
        match settings.profiler:
            case "perf":
                self.analyzer = PerfAnalyzer(self.builder, settings)
            case "gem5":
                self.analyzer = GemAnalyzer(self.builder, settings)
            case "ssh":
                self.analyzer = SshAnalyzer(BGBuilder(settings, self.builder), settings)
            case _:
                raise Exception(f'"{settings.profiler}" is unknown profiler')

    def run(self) -> None:
        self.logger.info("Analyze running. Settings:")
        self.logger.info(pformat(vars(self.settings)))
        if self.analyze_dir is None or self.test_dir is None:
            self.logger.warn("analyze_dir or test_dir are partially unknown. Exiting...")
            return
        self.create_empty_dir(self.analyze_dir)
        data = self.analyze(self.test_dir)
        self.fin_analyzer()
        self.pack(self.analyze_dir, data)

    def create_empty_dir(self, dir_path: Path) -> None:
        if dir_path.exists():
            shutil.rmtree(dir_path)
        dir_path.mkdir(parents=True)

    def analyze(self, test_dir: Path) -> Dict[str, DictSI]:
        print(f"[+]: Execute and analyze tests from {test_dir.absolute().as_posix()}")
        if self.analyzer is None:
            self.logger.warn("Analyzer is not provided.")
            return {}
        return self.analyzer.analyze(test_dir)

    def fin_analyzer(self) -> None:
        if self.analyzer is not None:
            self.analyzer.fin()

    def pack(self, analyze_dir: Path, analyzed_data: Dict[str, DictSI]) -> None:
        print(f"[+]: Save analysis' results to {analyze_dir.absolute().as_posix()}")
        self.packer.pack(analyze_dir, analyzed_data)

    def add_parser_arguments(self, subparser: SubParser) -> ArgumentParser:
        analyze_parser: ArgumentParser = subparser.add_parser("analyze")
        analyze_parser.add_argument("--config-file", default=None, help="Path to config file")
        analyze_parser.add_argument("--out-dir", default="analyze", help="Path to output dir")
        analyze_parser.add_argument("--test-dir", default="tests", help="Path to directory with tests")
        analyze_parser.add_argument(
            "--timeout",
            default=10,
            help="Number of seconds after which the test will be stopped",
        )
        analyze_parser.add_argument("--compiler", default="gcc", help="Path to compiler")
        analyze_parser.add_argument("--compiler-args", default="", help="Pass arguments on to the compiler")
        analyze_parser.add_argument(
            "--profiler",
            choices=["perf", "gem5"],
            default="perf",
            help="Type of profiler",
        )
        analyze_parser.add_argument("--gem5-home", default="./", help="Path to home gem5")
        analyze_parser.add_argument("--gem5-bin", default="./", help="Path to execute gem5")
        analyze_parser.add_argument("--target-isa", default="", help="Type of architecture being simulated")
        analyze_parser.add_argument("--sim-script", default="./", help="Path to simulation Script")
        analyze_parser.add_argument(
            "--log-level",
            default="WARNING",
            choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            help="Log level of program",
        )
        self.analyze_parser = analyze_parser
        return analyze_parser

    def parse_args(self, args: List[str]) -> Namespace:
        return self.analyze_parser.parse_known_args(args)[0]
