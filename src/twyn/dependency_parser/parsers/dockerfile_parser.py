import logging
import re

from typing_extensions import override

from twyn.dependency_parser.parsers.abstract_parser import AbstractParser
from twyn.dependency_parser.parsers.constants import DOCKERFILE

logger = logging.getLogger("twyn")


class DockerfileParser(AbstractParser):
    """Parser for Dockerfile dependencies (FROM instructions)."""

    # Pattern for variable substitution in Dockerfile
    VARIABLE_PATTERN = re.compile(
        r"\$\{(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)(?::-(?P<default>[^}$]+))?\}|\$(?P<short_name>[a-zA-Z_][a-zA-Z0-9_]*)"
    )

    def __init__(self, file_path: str = DOCKERFILE) -> None:
        super().__init__(file_path)

    @override
    def parse(self) -> set[str]:
        """Parse Dockerfile and return base image names from FROM instructions.

        Handles variable substitution and excludes stage names from previous FROM instructions.
        """
        with self.file_handler.open("r") as fp:
            lines = fp.readlines()

        # Handle line continuations (\)
        raw_instructions = self._handle_line_continuations(lines)

        # Parse instructions and resolve variables
        return self._extract_base_images(raw_instructions)

    def _handle_line_continuations(self, lines: list[str]) -> list[str]:
        """Handle Dockerfile line continuations with backslash."""
        raw_instructions = []
        buffer = ""

        for line in lines:
            line = line.strip()  # noqa: PLW2901
            if not line or line.startswith("#"):
                continue

            if line.endswith("\\"):
                buffer += line[:-1] + " "
            else:
                buffer += line
                raw_instructions.append(buffer)
                buffer = ""

        return raw_instructions

    def _extract_base_images(self, instructions: list[str]) -> set[str]:
        """Extract base images from Dockerfile instructions."""
        env: dict[str, str] = {}
        images: set[str] = set()
        stages: set[str] = set()

        for instruction in instructions:
            parts = instruction.split(None, 1)
            if len(parts) < 2:
                continue

            cmd = parts[0].upper()
            args = parts[1]

            if cmd in ("ARG", "ENV"):
                self._parse_variable_assignment(args, env)
            elif cmd == "FROM":
                self._parse_from_instruction(args, env, images, stages)
        return images

    def _parse_variable_assignment(self, args: str, env: dict[str, str]) -> None:
        """Parse ARG or ENV instruction and update environment variables."""
        if "=" in args:
            # Handle KEY=VALUE pairs
            for part in args.split():
                if "=" in part:
                    key, val = part.split("=", 1)
                    env[key] = self._resolve_variables(val.strip("\"'"), env)
        else:
            # Handle KEY VALUE pairs (space-separated)
            parts = args.split(None, 1)
            if parts:
                key = parts[0]
                val = parts[1] if len(parts) > 1 else ""
                env[key] = self._resolve_variables(val.strip("\"'"), env)

    def _parse_from_instruction(self, args: str, env: dict[str, str], images: set[str], stages: set[str]) -> None:
        """Parse FROM instruction and extract base image."""
        # Strip flags like --platform=...
        clean_args = re.sub(r"--\S+", "", args).strip().split()
        if not clean_args:
            return

        image_name = clean_args[0]
        resolved_image = self._resolve_variables(image_name, env)

        if resolved_image not in stages:
            image_name_only = self._extract_image_name(resolved_image)

            # Ignore the special 'scratch' no-op image
            if image_name_only.lower() != "scratch":
                images.add(image_name_only)

        for i, part in enumerate(clean_args):
            if part.lower() == "as" and i + 1 < len(clean_args):
                stages.add(clean_args[i + 1])

    def _extract_image_name(self, image_with_tag: str) -> str:
        """Extract image name without tag/version/digest from a Docker image reference.

        Examples:
            ubuntu:20.04 -> ubuntu
            node:16-alpine -> node
            registry.hub.docker.com/library/nginx:latest -> registry.hub.docker.com/library/nginx
            localhost:5000/myapp:v1.0 -> localhost:5000/myapp
            nginx@sha256:23q... -> nginx
        """
        # Strip off the digest FIRST
        if "@" in image_with_tag:
            image_with_tag = image_with_tag.split("@", maxsplit=1)[0]

        # Find the last ':' in the string
        last_colon_idx = image_with_tag.rfind(":")

        if last_colon_idx == -1:
            # No colon found, return as-is
            return image_with_tag

        potential_tag = image_with_tag[last_colon_idx + 1 :]
        name_part = image_with_tag[:last_colon_idx]

        if (
            potential_tag.isdigit() and "/" not in potential_tag and "/" not in name_part.split("/")[-1]
            if name_part
            else True
        ):
            # This looks like a registry with port, don't strip it
            return image_with_tag

        # Otherwise, strip the tag
        return name_part

    def _resolve_variables(self, text: str, env: dict[str, str]) -> str:
        """Resolve variable substitutions in text using environment variables."""

        def replace(match: re.Match[str]) -> str:
            name = match.group("name") or match.group("short_name")
            default = match.group("default")
            return env.get(name, default if default is not None else match.group(0))

        result = text
        iterations = 0
        max_iterations = 20  # Circuit breaker for recursive variables like PATH=$PATH

        while iterations < max_iterations:
            new_result = self.VARIABLE_PATTERN.sub(replace, result)
            if new_result == result:
                break
            result = new_result
            iterations += 1

        return result
