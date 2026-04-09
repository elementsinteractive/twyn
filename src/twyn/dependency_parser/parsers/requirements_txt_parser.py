"""Parser for requirements.txt dependencies."""

import re
from pathlib import Path

from typing_extensions import override

from twyn.dependency_parser.parsers.abstract_parser import AbstractParser
from twyn.dependency_parser.parsers.constants import REQUIREMENTS_TXT


class RequirementsTxtParser(AbstractParser):
    """Parser for requirements.txt dependencies."""

    SPEC_PATTERN = re.compile(
        r"""
        ^\s*
        (?P<name>[A-Za-z0-9_.-]+)       # package name
        (?:\[[^\]]+\])?                 # optional extras [a,b]
        \s*
        (?:==|>=|<=|~=|!=|>|<)?.*       # optional version specifier
        (?:\s*;\s*.+)?                  # optional environment marker
        """,
        re.VERBOSE,
    )
    """Regular expression pattern for parsing requirement specifications."""

    def __init__(self, file_path: str = REQUIREMENTS_TXT) -> None:
        super().__init__(file_path)

    @override
    def parse(self) -> set[str]:
        """Return a set of package names.

        It will recursively resolve other files included with -r.
        """
        return self._parse_internal(self.file_path, seen_files=set())

    def _parse_internal(self, source: str | Path, seen_files: set[Path]) -> set[str]:
        """Parse requirements file and handle includes recursively."""
        packages: set[str] = set()
        base_dir = Path(source).parent if isinstance(source, Path) else Path(".")

        with self.file_handler.open("r") as fp:
            for raw_line in fp:
                line = raw_line.strip()

                if not self._is_valid_line(line):
                    continue

                if line.startswith("-r "):
                    ref = line[3:].strip()
                    ref_path = (base_dir / ref).resolve()
                    if ref_path not in seen_files:
                        seen_files.add(ref_path)
                        packages.update(self._parse_internal(ref_path, seen_files))
                    continue

                if line.startswith("-e "):
                    egg_match = re.search(r"#egg=([A-Za-z0-9_.-]+)", line)
                    if egg_match:
                        packages.add(egg_match.group(1))
                    continue

                if "://" in line and "#egg=" in line:
                    egg_match = re.search(r"#egg=([A-Za-z0-9_.-]+)", line)
                    if egg_match:
                        packages.add(egg_match.group(1))
                    continue
                match = self.SPEC_PATTERN.match(line)
                if match:
                    packages.add(match.group("name"))

        return packages

    @staticmethod
    def _is_valid_line(line: str) -> bool:
        """Check if line is valid for parsing."""
        return (
            bool(line)
            and not line.startswith("#")
            and not line.startswith("--")
            and not line.startswith("-c")
            and not line.startswith("-f")
        )
