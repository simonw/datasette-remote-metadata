import asyncio
import json
from datasette import hookimpl
from datasette.utils import parse_metadata
import httpx2
import time
from functools import wraps
import random


def is_datasette_1(datasette):
    # Datasette 1.0 replaced the get_metadata() plugin hook with methods
    # that write metadata to the internal database
    return hasattr(datasette, "set_instance_metadata")


async def update_remote_with_time_limit(datasette, timelimit=None):
    # Update datasette._remote_metadata from URL - returns when done OR
    # when it hits time limit. If the time limit is hit it will still
    # perform the update once the request has completed
    config = datasette.plugin_config("datasette-remote-metadata") or {}
    url = config.get("url")
    if not url:
        return
    headers = config.get("headers") or {}
    cachebust = bool(config.get("cachebust"))

    async def update_remote():
        fetch_url = url
        if cachebust:
            fetch_url += "&" if "?" in url else "?"
            fetch_url += str(random.random())
        async with httpx2.AsyncClient() as client:
            response = await client.get(
                fetch_url,
                headers=dict(headers, **{"Cache-Control": "no-cache"}),
            )
            response.raise_for_status()
        metadata = parse_metadata(response.content)
        if is_datasette_1(datasette):
            await apply_metadata(datasette, metadata)
        else:
            datasette._remote_metadata = metadata
        datasette._remote_metadata_last_updated = time.monotonic()

    if timelimit is not None:
        try:
            await asyncio.wait_for(asyncio.shield(update_remote()), timeout=timelimit)
        except asyncio.exceptions.TimeoutError:
            pass
    else:
        await update_remote()


@hookimpl
def startup(datasette):
    async def inner():
        if is_datasette_1(datasette):
            # Ensure internal metadata tables exist before writing to them
            await datasette.refresh_schemas()
        await update_remote_with_time_limit(datasette)

    return inner


# Only called by Datasette 0.x - ignored by 1.0
@hookimpl
def get_metadata(datasette):
    return getattr(datasette, "_remote_metadata", None) or {}


@hookimpl
def asgi_wrapper(datasette):
    # Refresh stale (over X seconds old) remote metadata on every request
    config = datasette.plugin_config("datasette-remote-metadata") or {}
    ttl = config.get("ttl") or 30

    def wrap_with_refresh(app):
        @wraps(app)
        async def add_refresh(scope, recieve, send):
            last_update = getattr(datasette, "_remote_metadata_last_updated", None)
            if last_update is None or (time.monotonic() - last_update) > ttl:
                await update_remote_with_time_limit(datasette, timelimit=0.2)
            await app(scope, recieve, send)

        return add_refresh

    return wrap_with_refresh


def _to_string(value):
    # Matches Datasette's own encoding of non-string metadata values
    return value if isinstance(value, str) else json.dumps(value, default=str)


async def apply_metadata(datasette, metadata_dict):
    # Datasette 1.0+ only - imitates Datasette.apply_metadata_json()
    for key in metadata_dict or {}:
        if key == "databases":
            continue
        await datasette.set_instance_metadata(
            key, _to_string(metadata_dict[key])
        )

    # database-level
    for dbname, db in (metadata_dict.get("databases") or {}).items():
        for key, value in db.items():
            if key in ("tables", "queries"):
                continue
            await datasette.set_database_metadata(dbname, key, _to_string(value))

        # table-level
        for tablename, table in (db.get("tables") or {}).items():
            for key, value in table.items():
                if key == "columns":
                    continue
                await datasette.set_resource_metadata(
                    dbname, tablename, key, _to_string(value)
                )

            # column-level
            for columnname, column_description in (table.get("columns") or {}).items():
                await datasette.set_column_metadata(
                    dbname, tablename, columnname, "description", column_description
                )
