import asyncio
from datasette import hookimpl
from datasette.utils import parse_metadata
import httpx
import time
from functools import wraps
import random


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
        async with httpx.AsyncClient() as client:
            response = await client.get(
                fetch_url,
                headers=dict(headers, **{"Cache-Control": "no-cache"}),
            )
            response.raise_for_status()
        metadata = parse_metadata(response.content)
        await apply_metadata(datasette, metadata)
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
        await datasette.refresh_schemas()
        await update_remote_with_time_limit(datasette)

    return inner


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


# Imitating https://github.com/simonw/datasette/blob/f6bd2bf8/datasette/app.py#L446-L472
async def apply_metadata(datasette, metadata_dict):
    for key in metadata_dict or {}:
        if key == "databases":
            continue
        await datasette.set_instance_metadata(key, metadata_dict[key])

    # database-level
    for dbname, db in metadata_dict.get("databases", {}).items():
        for key, value in db.items():
            if key == "tables":
                continue
            await datasette.set_database_metadata(dbname, key, value)

        # table-level
        for tablename, table in db.get("tables", {}).items():
            for key, value in table.items():
                if key == "columns":
                    continue
                await datasette.set_resource_metadata(dbname, tablename, key, value)

            # column-level
            for columnname, column_description in table.get("columns", {}).items():
                await datasette.set_column_metadata(
                    dbname, tablename, columnname, "description", column_description
                )
