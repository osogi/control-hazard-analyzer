import os.path
from pathlib import Path
import subprocess
from tempfile import mkdtemp
import glob
from typing import Dict
from builders.builder import Builder


class PerfData:
    def __init__(self, data_dict: Dict[str, str]):
        self.branches = int(data_dict["branches"])
        self.missed_branches = int(data_dict["mised"])
        self.cache_bpu = int(data_dict["cache_BPU"])

    def __str__(self) -> str:
        return f"PerfData(branches: {self.branches}, missed: {self.missed_branches}, cache_bpu {self.cache_bpu})"


class PerfProfiler:
    empty_test_name = "empty.c"

    def __init__(self, builder: Builder):
        self.builder: Builder = builder
        self.temp_dir: Path = Path(mkdtemp())
        self.template_path = Path("profilers/attachments/perfTemplate.c")
        self.empty_test_path = Path("profilers/attachments/empty.c")

    def patch_test(self, src_test: Path, dest_test: Path) -> bool:
        if os.path.isfile(src_test):
            with open(dest_test, "wt") as writter:
                writter.write(f'#include "{src_test.absolute()}"\n')
                writter.write(f'#include "{self.template_path.absolute()}"\n')
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

    def get_stat(self, binary: Path) -> PerfData:
        execute_line = ["sudo", binary]
        proc = subprocess.run(
            execute_line,
            stdout=subprocess.PIPE,
            check=True,
        )
        output = proc.stdout.decode()
        data = PerfData(self.output_to_dict(output))
        return data

    def get_stats_dir(self, dir: Path) -> Dict[str, PerfData]:
        data_dict: Dict[str, PerfData] = {}
        for binary in os.listdir(dir):
            data = self.get_stat(dir.joinpath(binary))
            data_dict[binary] = data
        return data_dict

    def profile(self, test_dir: Path, analyze_dir: Path) -> bool:
        src_dir = self.temp_dir.joinpath("src/")
        build_dir = self.temp_dir.joinpath("bins/")

        self.patch_tests_in_dir(test_dir, src_dir)
        self.add_empty_patched_test(src_dir.joinpath(self.empty_test_name))
        self.builder.build(src_dir, build_dir)
        analized = self.get_stats_dir(build_dir)
        for key in analized:
            print(f"{key}: {analized[key]}")
        return True
