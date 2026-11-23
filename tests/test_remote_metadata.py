from time import sleep
from datasette.app import Datasette
import httpx2
import pytest

TEST_URL = "https://www.example.com/metadata.yml"


@pytest.mark.asyncio
async def test_remote_metadata(httpx2_mock):
    httpx2_mock.get(TEST_URL).respond(text="title: This is the remote metadata title")
    datasette = Datasette(
        [],
        memory=True,
        metadata={"plugins": {"datasette-remote-metadata": {"url": TEST_URL}}},
    )
    await datasette.invoke_startup()
    response = await datasette.client.get("/")
    assert response.status_code == 200
    assert ">This is the remote metadata title<" in response.text


@pytest.mark.asyncio
async def test_ttl(httpx2_mock):
    route = httpx2_mock.get(TEST_URL).respond(text="title: Testing TTL")
    datasette = Datasette(
        [],
        memory=True,
        metadata={
            "plugins": {
                "datasette-remote-metadata": {
                    "url": TEST_URL,
                    "ttl": 1,
                }
            }
        },
    )
    await datasette.invoke_startup()
    # More requests shouldn't trigger a metadata fetch
    for _ in range(3):
        await datasette.client.get("/")
    assert route.call_count == 1
    # Now wait a second and try again
    sleep(1)
    await datasette.client.get("/")
    assert route.call_count == 2


@pytest.mark.asyncio
async def test_headers(httpx2_mock):
    route = httpx2_mock.get(TEST_URL).respond(text="title: Testing TTL")
    datasette = Datasette(
        [],
        memory=True,
        metadata={
            "plugins": {
                "datasette-remote-metadata": {
                    "url": TEST_URL,
                    "headers": {"Authorization": "Bearer X"},
                }
            }
        },
    )
    await datasette.invoke_startup()
    assert route.call_count == 1
    assert route.calls.last.request.headers["authorization"] == "Bearer X"


@pytest.mark.asyncio
@pytest.mark.parametrize("already_has_querystring", (True, False))
async def test_cachebust(httpx2_mock, already_has_querystring):
    url = TEST_URL
    if already_has_querystring:
        url += "?foo=bar"
    route = httpx2_mock.get().respond(text="title: Testing TTL")
    datasette = Datasette(
        [],
        memory=True,
        metadata={
            "plugins": {"datasette-remote-metadata": {"url": url, "cachebust": True}}
        },
    )
    await datasette.invoke_startup()
    url = str(route.calls[0].request.url)
    if already_has_querystring:
        assert "?foo=bar&0." in url
    else:
        assert "?0." in url


@pytest.mark.asyncio
async def test_fails_if_error_on_startup(httpx2_mock):
    httpx2_mock.get(TEST_URL).respond(status_code=404)
    datasette = Datasette(
        [],
        memory=True,
        metadata={"plugins": {"datasette-remote-metadata": {"url": TEST_URL}}},
    )
    with pytest.raises(httpx2.HTTPStatusError):
        await datasette.invoke_startup()


@pytest.mark.asyncio
async def test_table_and_column_metadata(httpx2_mock):
    httpx2_mock.get(TEST_URL).respond(
        text="""
databases:
  data:
    description: Remote database description
    tables:
      dogs:
        description: Remote table description
        columns:
          name: Remote column description
"""
    )
    datasette = Datasette(
        [],
        memory=True,
        metadata={"plugins": {"datasette-remote-metadata": {"url": TEST_URL}}},
    )
    db = datasette.add_memory_database("data")
    await db.execute_write("create table if not exists dogs (name text)")
    await datasette.invoke_startup()
    db_html = (await datasette.client.get("/data")).text
    assert "Remote database description" in db_html
    table_html = (await datasette.client.get("/data/dogs")).text
    assert "Remote table description" in table_html
    assert "Remote column description" in table_html


@pytest.mark.asyncio
async def test_refresh_picks_up_changes(httpx2_mock):
    httpx2_mock.get(TEST_URL).respond(text="title: First title")
    datasette = Datasette(
        [],
        memory=True,
        metadata={
            "plugins": {"datasette-remote-metadata": {"url": TEST_URL, "ttl": 1}}
        },
    )
    await datasette.invoke_startup()
    assert ">First title<" in (await datasette.client.get("/")).text
    httpx2_mock.reset()
    httpx2_mock.get(TEST_URL).respond(text="title: Second title")
    sleep(1.1)
    await datasette.client.get("/")  # Triggers the refresh
    assert ">Second title<" in (await datasette.client.get("/")).text


@pytest.mark.asyncio
async def test_non_string_values(httpx2_mock):
    httpx2_mock.get(TEST_URL).respond(
        text="""
title: Non-string values
databases:
  data:
    tables:
      dogs:
        sortable_columns: [name]
    queries:
      q: select 1
"""
    )
    datasette = Datasette(
        [],
        memory=True,
        metadata={"plugins": {"datasette-remote-metadata": {"url": TEST_URL}}},
    )
    db = datasette.add_memory_database("data")
    await db.execute_write("create table if not exists dogs (name text)")
    await datasette.invoke_startup()
    response = await datasette.client.get("/data/dogs")
    assert response.status_code == 200
