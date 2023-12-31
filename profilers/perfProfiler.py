from __future__ import annotations
from argparse import Namespace

import glob
import logging
import shutil
import signal
import subprocess
from pathlib import Path
import sys
from tempfile import mkdtemp
import time
from typing import Dict, List

from src.builder import Builder


class PerfData:
    def __init__(self, data_dict: Dict[str, str] = {}, is_full: bool = True):
        self.branches = int(data_dict.get("branches", -1))
        self.missed_branches = int(data_dict.get("missed_branches", -1))
        self.cache_bpu = int(data_dict.get("cache_BPU", -1))
        self.ticks = int(data_dict.get("cpu_clock", -1))
        self.instructions = int(data_dict.get("instructions", -1))
        self.is_full = is_full

    def to_dict(self) -> Dict:
        data_dict: Dict = {}
        data_dict["branchPred.lookups"] = self.branches
        data_dict["branchPred.condIncorrect"] = self.missed_branches
        data_dict["branchPred.BTBUpdates"] = self.cache_bpu
        data_dict["simTicks"] = self.ticks
        data_dict["instructions"] = self.instructions
        data_dict["isFull"] = self.is_full
        return data_dict

    def __sub__(self, other) -> PerfData:
        if isinstance(other, PerfData):
            res: PerfData = PerfData()
            res.branches = self.branches - other.branches
            res.missed_branches = self.missed_branches - other.missed_branches
            res.cache_bpu = self.cache_bpu - other.cache_bpu
            res.ticks = self.ticks - other.ticks
            res.instructions = self.instructions - other.instructions
            res.is_full = self.is_full
            return res
        else:
            raise TypeError

    def __str__(self) -> str:
        return str(self.to_dict())

    def max(self, const: int):
        self.branches = max(self.branches, const)
        self.missed_branches = max(self.missed_branches, const)
        self.cache_bpu = max(self.cache_bpu, const)
        self.ticks = max(self.ticks, const)
        self.instructions = max(self.instructions, const)


class PerfProfiler:
    def __init__(self, builder: Builder, settings: Namespace):
        self.settings = settings
        self.max_test_launches = settings.__dict__.get("max_test_launches", -1)
        self.builder: Builder = builder
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(self.settings.log_level)
        self.temp_dir: Path = Path(mkdtemp())
        self.template_path = Path("profilers/attachments/perfTemplate.c")
        self.empty_test_path = Path("profilers/attachments/empty.c")

    def __del__(self):
        shutil.rmtree(self.temp_dir)

    def patch_test(self, src_test: Path, dest_test: Path) -> bool:
        dest_test.parent.mkdir(parents=True, exist_ok=True)
        if src_test.is_file():
            with open(dest_test, "wt") as writter:
                writter.write(f'#include "{self.template_path.absolute()}"\n')
                writter.write(f'#include "{src_test.absolute()}"\n')
                return True
        return False

    def add_empty_patched_test(self, destination_file: Path):
        destination_file.parent.mkdir(parents=True, exist_ok=True)
        self.patch_test(self.empty_test_path, destination_file)

    def patch_tests_in_dir(self, src_dir: Path, dst_dir: Path):
        dst_dir.mkdir(parents=True, exist_ok=True)
        for src_test in glob.glob(str(src_dir) + "/*.c"):
            src_test = Path(src_test)
            self.patch_test(src_test, dst_dir.joinpath(src_test.name))

    def output_to_dict(self, output: str) -> Dict[str, str]:
        data_dict: Dict[str, str] = {}
        for line in output.split("\n"):
            splitted = line.split(":")
            if len(splitted) >= 2:
                name, val = splitted[0], splitted[1]
                data_dict.update({name.strip(): val.strip()})
        return data_dict

    def tab_lines(self, lines: str):
        return "\t" + lines.replace("\n", "\n\t")[:-1]

    def execute_test(self, execute_line: List[str], timeout: float) -> PerfData:
        proc = subprocess.Popen(execute_line, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        is_full = True
        try:
            proc.wait(timeout)
        except subprocess.TimeoutExpired:
            proc.send_signal(signal.SIGINT)
            is_full = False
            if proc.poll is None:
                pass
            if proc.returncode is not int:  # some bug: if send signal to proc, it ret code will be one
                proc.returncode = 0

        if proc.stdout is not None:
            output = proc.stdout.read().decode()
            data = PerfData(self.output_to_dict(output), is_full)
        else:
            data = PerfData()

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
        return data

    def get_stat(self, binary: Path, number_executes: int, cpu_core: int = 0) -> List[PerfData]:
        stats: List[PerfData] = []
        execute_line = list(map(str, [binary, cpu_core]))
        execute_string = " ".join(map(str, execute_line))
        self.logger.info(f"[perfProfiler]: Executing: {execute_string}")

        left_time = self.builder.settings.timeout
        timeout = time.time() + self.builder.settings.timeout
        while (left_time > 0) and (number_executes != 0):
            stats.append(self.execute_test(execute_line, left_time))
            left_time = timeout - time.time()
            number_executes -= 1
        return stats

    def get_stats_dir(self, target_dir: Path) -> Dict[str, List[PerfData]]:
        data_dict: Dict[str, List[PerfData]] = {}
        for binary in target_dir.iterdir():
            data = self.get_stat(target_dir.joinpath(binary), self.max_test_launches)
            data_dict[binary.name.split(".")[0]] = data
        return data_dict

    def update_capabilities_dir(self, target_dir: Path):
        sudo_hint = True
        use_sudo = False
        for binary in target_dir.iterdir():
            suc_launch = False
            used_max_perm = False

            pth = target_dir.joinpath(binary)
            execute_line = ["setcap", "cap_sys_admin,cap_sys_nice=ep", pth]
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

    def _get_meddian(self, stats: List[PerfData]) -> PerfData | None:
        def missed_pct(dt: PerfData) -> float:
            if dt.branches == 0:
                dt.branches = 1
            return dt.missed_branches / dt.branches

        stats.sort(key=missed_pct)
        if len(stats) > 0:
            return stats[(len(stats) // 2)]
        return None

    def get_meddian(self, stats: List[PerfData]) -> PerfData | None:
        stats = stats.copy()
        average = self._get_meddian(stats)
        full_stats: List[PerfData] = []
        for stat in stats:
            if stat.is_full:
                full_stats.append(stat)
        full_average = self._get_meddian(full_stats)
        if full_average is not None:
            average = full_average

        return average

    def correct(self, analyzed: Dict[str, List[PerfData]]) -> Dict[str, Dict]:
        key_empty_test = self.empty_test_path.name.split(".")[0]
        analyzed_buf = {key: self.get_meddian(stats) for key, stats in analyzed.items()}
        analyzed_average: Dict[str, PerfData] = {}
        for key, val in analyzed_buf.items():
            if val is not None:
                analyzed_average[key] = val
            else:
                print(f"[-]: Error: can't get average result of '{key}' test", file=sys.stderr)

        analyzed_average[key_empty_test].max(0)
        corrected: Dict[str, Dict] = {}
        for key in analyzed_average:
            if key != key_empty_test:
                analyzed_average[key] = analyzed_average[key] - analyzed_average[key_empty_test]
                corrected.update({key: analyzed_average[key].to_dict()})
        return corrected

    def profile(self, test_dir: Path) -> Dict[str, Dict]:
        src_dir = self.temp_dir.joinpath("src/")
        build_dir = self.temp_dir.joinpath("bins/")

        self.patch_tests_in_dir(test_dir, src_dir)
        self.add_empty_patched_test(src_dir.joinpath(self.empty_test_path.name))
        self.builder.build(src_dir, build_dir)
        self.update_capabilities_dir(build_dir)
        analyzed = self.get_stats_dir(build_dir)

        return self.correct(analyzed)
