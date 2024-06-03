from pathlib import Path
from typing import Dict, Protocol

from src.protocols.collector import DictSI


class Analyzer(Protocol):
    def analyze(self, test_dir: Path) -> Dict[str, DictSI]: ...

    def fin(self) -> None: ...
