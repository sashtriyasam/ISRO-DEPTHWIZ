"""Package import smoke test."""

import depthwizard
from depthwizard.version import __version__


def test_package_imports() -> None:
    assert depthwizard.__version__ == __version__


def test_version_is_semver_like() -> None:
    parts = __version__.split(".")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)
