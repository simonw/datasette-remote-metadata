# datasette-remote-metadata

[![PyPI](https://img.shields.io/pypi/v/datasette-remote-metadata.svg)](https://pypi.org/project/datasette-remote-metadata/)
[![Changelog](https://img.shields.io/github/v/release/simonw/datasette-remote-metadata?include_prereleases&label=changelog)](https://github.com/simonw/datasette-remote-metadata/releases)
[![Tests](https://github.com/simonw/datasette-remote-metadata/workflows/Test/badge.svg)](https://github.com/simonw/datasette-remote-metadata/actions?query=workflow%3ATest)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/simonw/datasette-remote-metadata/blob/main/LICENSE)

Periodically refresh Datasette metadata from a remote URL

## Installation

Install this plugin in the same environment as Datasette.

    $ datasette install datasette-remote-metadata

## Usage

Add the following to your `metadata.json`:

```json
{
    "plugins": {
        "datasette-remote-metadata": {
            "url": "https://example.com/remote-metadata.yml"
        }
    }
}
```
The plugin will fetch the specified metadata  from that URL at startup and combine it with any existing metadata. You can use a URL to either a JSON file or a YAML file.

It will periodically refresh that metadata - by default every 30 seconds, unless you specify an alternative `"ttl"` value in the plugin configuration.

## Development

To set up this plugin locally, first checkout the code. Then create a new virtual environment:

    cd datasette-remote-metadata
    python3 -mvenv venv
    source venv/bin/activate

Or if you are using `pipenv`:

    pipenv shell

Now install the dependencies and test dependencies:

    pip install -e '.[test]'

To run the tests:

    pytest
