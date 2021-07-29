from setuptools import setup
import os

VERSION = "0.1"


def get_long_description():
    with open(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "README.md"),
        encoding="utf8",
    ) as fp:
        return fp.read()


setup(
    name="datasette-remote-metadata",
    description="Periodically refresh Datasette metadata from a remote URL",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    author="Simon Willison",
    url="https://github.com/simonw/datasette-remote-metadata",
    project_urls={
        "Issues": "https://github.com/simonw/datasette-remote-metadata/issues",
        "CI": "https://github.com/simonw/datasette-remote-metadata/actions",
        "Changelog": "https://github.com/simonw/datasette-remote-metadata/releases",
    },
    license="Apache License, Version 2.0",
    version=VERSION,
    packages=["datasette_remote_metadata"],
    entry_points={"datasette": ["remote_metadata = datasette_remote_metadata"]},
    install_requires=["datasette"],
    extras_require={"test": ["pytest", "pytest-asyncio", "pytest-httpx"]},
    tests_require=["datasette-remote-metadata[test]"],
    python_requires=">=3.6",
)
