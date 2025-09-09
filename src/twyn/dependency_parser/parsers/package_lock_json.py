import json
from typing import Any

from twyn.dependency_parser.parsers.abstract_parser import AbstractParser
from twyn.dependency_parser.parsers.constants import PACKAGE_LOCK_JSON


class PackageLockJsonParser(AbstractParser):
    def __init__(self, file_path: str = PACKAGE_LOCK_JSON) -> None:
        super().__init__(file_path)

    def parse(self) -> set[str]:
        """Recursively gets all the packages from a `package-lock.json` file.

        It supports v1, v2 and v3.
        """
        data = json.loads(self.file_handler.read())
        result: set[str] = set()

        # Handle v1 & v2
        if "dependencies" in data:
            self._collect_deps(data["dependencies"], result)

        # Handle v2 & v3
        if "packages" in data:
            for pkg_path, pkg_info in data["packages"].items():
                if pkg_path == "":
                    continue
                name = pkg_info.get("name")
                if not name and pkg_path.startswith("node_modules/"):
                    name = pkg_path.split("node_modules/")[-1]
                if name:
                    result.add(name)

        return result

    def _collect_deps(self, dep_tree: dict[str, Any], collected: set[str]):
        for name, info in dep_tree.items():
            collected.add(name)
            if "dependencies" in info:
                self._collect_deps(info["dependencies"], collected)
            if "requires" in info:
                collected.update(info["requires"].keys() if isinstance(info["requires"], dict) else info["requires"])
