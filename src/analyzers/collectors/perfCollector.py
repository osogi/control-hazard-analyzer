import logging
import signal
import subprocess
import sys
import time
from argparse import Namespace
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List

if TYPE_CHECKING:
    from _typeshed import StrOrBytesPath

from src.analyzers.collectors.perfParser import PerfParser, TestRes
from src.protocols.collector import DictSI


class PerfCollector:
    def __init__(self, settings: Namespace):
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(self.settings.log_level)

        set_dict = vars(settings)
        self.max_test_launches = set_dict.get("max_test_launches", -1)
        self.cpu = set_dict.get("cpu", 0)

    def tab_lines(self, lines: str) -> str:
        return "\t" + lines.replace("\n", "\n\t")[:-1]

    def execute_test(self, execute_line: List[str], timeout: float) -> TestRes:
        proc = subprocess.Popen(execute_line, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        is_full = True
        try:
            proc.wait(timeout)
        except subprocess.TimeoutExpired:
            proc.send_signal(signal.SIGINT)
            is_full = False
            if proc.poll() is None:
                pass
            if proc.returncode is not int:  # some bug: if send signal to proc, its ret code will be one
                proc.returncode = 0
            elif proc.returncode == 2:  # if it will be work corectly ret with signint should be 2
                proc.returncode = 0

        if proc.stderr is not None:
            test_errors = proc.stderr.read().decode()
            if len(test_errors) > 0:
                execute_str = " ".join(execute_line)
                print(f"[-]: Some error occurred during launching '{execute_str}':", file=sys.stderr)
                print(self.tab_lines(test_errors), file=sys.stderr, end="")
        if proc.returncode != 0:
            print(
                "[?]: Maybe perf don't have enough capabilities or your CPU don't have special debug counters\n",
                file=sys.stderr,
            )

        res = bytes()
        if proc.stdout is not None:
            res = proc.stdout.read()
        return (res, is_full)

    def get_stat(self, binary: Path, number_executes: int, cpu_core: int) -> List[TestRes]:
        stats: List[TestRes] = []
        execute_line = list(map(str, [binary, cpu_core]))
        execute_string = " ".join(map(str, execute_line))
        self.logger.info(f"[perfProfiler]: Executing: {execute_string}")

        left_time = self.settings.timeout
        timeout = time.time() + self.settings.timeout
        while (left_time > 0) and (number_executes != 0):
            stats.append(self.execute_test(execute_line, left_time))
            left_time = timeout - time.time()
            number_executes -= 1
        return stats

    def get_stats_dir(self, target_dir: Path) -> Dict[str, List[TestRes]]:
        output_dict: Dict[str, List[TestRes]] = {}
        for binary in target_dir.iterdir():
            data = self.get_stat(target_dir.joinpath(binary), self.max_test_launches, self.cpu)
            output_dict[binary.name.split(".")[0]] = data
        return output_dict

    def update_capabilities_dir(self, target_dir: Path) -> None:
        sudo_hint = True
        use_sudo = False
        for binary in target_dir.iterdir():
            suc_launch = False
            used_max_perm = False

            pth = target_dir.joinpath(binary)
            execute_line: List[StrOrBytesPath] = ["setcap", "cap_sys_admin,cap_sys_nice=ep", pth]
            while (not suc_launch) and (not used_max_perm):
                if use_sudo:
                    if sudo_hint:
                        print("[+]: Try using sudo to set capabilities for tests executables")
                        sudo_hint = False
                    execute_line = ["sudo"] + execute_line
                    used_max_perm = True

                proc = subprocess.run(execute_line, stderr=subprocess.PIPE)

                if proc.returncode == 0:
                    suc_launch = True
                else:
                    if used_max_perm:
                        proc_err = proc.stderr.decode()
                        print(f"[-]: Error during seting capability:\n {self.tab_lines(proc_err)}", file=sys.stderr)
                    use_sudo = True

    def collect(self, bin_dir: Path) -> Dict[str, DictSI]:
        self.update_capabilities_dir(bin_dir)
        analyzed = self.get_stats_dir(bin_dir)

        return PerfParser.correct(analyzed)
