import logging
import re

import yaml
from typing_extensions import override

from twyn.dependency_parser.parsers.abstract_parser import AbstractParser
from twyn.dependency_parser.parsers.constants import DOCKER_COMPOSE_YML

logger = logging.getLogger("twyn")


class DockerComposeParser(AbstractParser):
    """Parser for docker-compose.yml dependencies (service images)."""

    # Pattern for variable substitution in docker-compose
    # Supports ${VAR}, ${VAR:-default}, ${VAR-default}, ${VAR:?error}
    VARIABLE_PATTERN = re.compile(
        r"\$\{(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)(?::-(?P<default>[^}]+))?\}|\$(?P<short_name>[a-zA-Z_][a-zA-Z0-9_]*)"
    )

    def __init__(self, file_path: str = DOCKER_COMPOSE_YML) -> None:
        super().__init__(file_path)

    @override
    def parse(self) -> set[str]:
        """Parse docker-compose.yml and return image names from services.

        Extracts images from service definitions and handles variable substitution.
        """
        with self.file_handler.open("r") as fp:
            try:
                compose_data = yaml.safe_load(fp)
            except yaml.YAMLError as e:
                logger.warning("Failed to parse docker-compose file: %s", e)
                return set()

        if not compose_data:
            return set()

        images: set[str] = set()

        # Handle both docker-compose v2/v3 format (services at root)
        # and older formats
        services = compose_data.get("services", {})
        if not services:
            # Try legacy format where services are at root level
            services = {k: v for k, v in compose_data.items() if isinstance(v, dict) and "image" in v}

        for service_config in services.values():
            if not isinstance(service_config, dict):
                continue

            image = service_config.get("image")
            if image:
                # Resolve any environment variables
                resolved_image = self._resolve_variables(str(image))
                # Extract image name without tag
                image_name = self._extract_image_name(resolved_image)
                if image_name and not self._has_unresolved_variables(image_name):
                    images.add(image_name)

        return images

    def _resolve_variables(self, text: str) -> str:
        """Resolve variable substitutions in text.

        Note: Unlike Dockerfile, docker-compose variables come from the
        environment, so we can only resolve those with default values.
        """

        def replace_var(match: re.Match[str]) -> str:
            default = match.group("default") if match.group("name") else None

            # Without access to actual env vars, return default if available
            if default is not None:
                return default

            # Keep the variable reference if no default
            return match.group(0)

        return self.VARIABLE_PATTERN.sub(replace_var, text)

    def _has_unresolved_variables(self, text: str) -> bool:
        """Check if text still contains unresolved variable references."""
        return bool(self.VARIABLE_PATTERN.search(text))

    def _extract_image_name(self, image_with_tag: str) -> str:
        """Extract image name without tag/version/digest from a Docker image reference.

        Examples:
            ubuntu:20.04 -> ubuntu
            node:16-alpine -> node
            registry.hub.docker.com/library/nginx:latest -> registry.hub.docker.com/library/nginx
            localhost:5000/myapp:v1.0 -> localhost:5000/myapp
            redis:7 -> redis
            nginx@sha256:23q... -> nginx
        """
        # Strip off the digest FIRST
        if "@" in image_with_tag:
            image_with_tag = image_with_tag.split("@")[0]

        # Find the last ':' in the string
        last_colon_idx = image_with_tag.rfind(":")

        if last_colon_idx == -1:
            # No colon found, return as-is
            return image_with_tag

        potential_tag = image_with_tag[last_colon_idx + 1 :]
        name_part = image_with_tag[:last_colon_idx]

        # Check if this looks like a port number (registry:port/path pattern)
        # A port is indicated by the pattern hostname:port/path where:
        # - The part after colon is purely numeric (port)
        # - There's a slash after the port (path to image)
        if potential_tag.isdigit() and "/" in image_with_tag[last_colon_idx + 1 :]:
            # This looks like a registry with port, don't strip it
            return image_with_tag

        # Otherwise, strip the tag
        return name_part
