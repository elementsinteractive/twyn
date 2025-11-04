import re
from typing import TextIO

import yaml

from twyn.dependency_parser.parsers.abstract_parser import AbstractParser
from twyn.dependency_parser.parsers.constants import YARN_LOCK
from twyn.dependency_parser.parsers.exceptions import InvalidFileFormatError


class YarnLockParser(AbstractParser):
    def __init__(self, file_path: str = YARN_LOCK) -> None:
        super().__init__(file_path)

    def parse(self) -> set[str]:
        """Parse yarn lock file and return package names."""
        with self.file_handler.open() as fp:
            # We want to find out if it's a v1 or v2 file.
            # we will check maximum on the first 20 lines in order to guess
            for _ in range(20):
                line = fp.readline().strip()
                if not line:
                    continue

                if "# yarn lockfile v1" in line:
                    return self._parse_v1(fp)

                if "__metadata:" in line:
                    return self._parse_v2(fp)
        raise InvalidFileFormatError("Unkown file format.")

    def _parse_v1(self, fp: TextIO) -> set[str]:
        """Parse a yarn.lock file (v1) and return all the dependencies in it."""
        # Match the entire line up to the colon (allows multiple quoted keys)
        key_line_re = re.compile(r"^(?P<key>[^ \t].*?):\s*$")
        names = set()

        for line in fp:
            match = key_line_re.match(line)
            if not match:
                continue
            key = match.group("key").strip()

            # Split on commas at the top level (handles multiple quoted keys)
            parts = [p.strip() for p in key.split(",")]

            for part in parts:
                # Remove surrounding quotes if present
                if (part.startswith('"') and part.endswith('"')) or (part.startswith("'") and part.endswith("'")):
                    part = part[1:-1]  # noqa: PLW2901

                # Skip anything without '@' (not a valid package selector)
                if "@" not in part:
                    continue

                # Get everything before the last '@' as the package name
                pkg_name = part.rsplit("@", 1)[0]
                names.add(pkg_name)

        return names

    def _parse_v2(self, fp: TextIO) -> set[str]:
        """Parse Yarn v2 lockfile and return package names."""
        data = yaml.safe_load(fp)

        packages: set[str] = set()
        for key in data:
            if key == "__metadata__":
                continue

            # Yarn v2 keys look like: "react@npm:^17.0.2"
            # extract only the package name before @npm
            if "@npm:" in key:  # noqa: SIM108
                name = key.split("@npm:")[0].strip('"')
            else:
                # fallback: just take part before first @
                name = key.split("@", 1)[0].strip('"')

            packages.add(name)

        return packages
