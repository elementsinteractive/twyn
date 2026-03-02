try:
    from fastmcp import FastMCP
except ImportError:
    raise SystemExit(
        "Using twyn's MCP requires extra dependencies. Install them with `pip install twyn[mcp]`'"
    ) from None


from twyn.base.constants import PackageEcosystems, SelectorMethod
from twyn.main import check_dependencies
from twyn.trusted_packages.models import TyposquatCheckResults

mcp = FastMCP("Check for possible typos in your dependencies' names.")


@mcp.tool(
    name="twyn",
    title="Check possible typosquats",
    description="Check the possible typosquats of a given dependency or set of dependencies.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "openWorldHint": True,
    },
)
def check_possible_typosquat(
    dependencies: set[str] | None = None,
    package_ecosystem: PackageEcosystems | None = None,
    pypi_source: str | None = None,
    npm_source: str | None = None,
    config_file: str | None = None,
    selector_method: SelectorMethod | None = None,
) -> TyposquatCheckResults:
    """Scan dependencies for typosquats using Twyn."""
    return check_dependencies(
        dependencies=dependencies,
        package_ecosystem=package_ecosystem,
        pypi_source=pypi_source,
        npm_source=npm_source,
        config_file=config_file,
        selector_method=selector_method,
    )


def cli() -> None:
    """Entry point for the MCP tool."""
    mcp.run()


if __name__ == "__main__":
    cli()
