from time import sleep
from datasette.app import Datasette
import httpx
import pytest

TEST_URL = "https://www.example.com/metadata.yml"


@pytest.fixture
def non_mocked_hosts():
    return ["localhost"]


@pytest.mark.asyncio
async def test_remote_metadata(httpx_mock):
    httpx_mock.add_response(
        url=TEST_URL,
        text="title: This is the remote metadata title",
    )
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
async def test_ttl(httpx_mock):
    httpx_mock.add_response(
        url=TEST_URL,
        text="title: Testing TTL",
    )
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
    assert len(httpx_mock.get_requests()) == 1
    # Now wait a second and try again
    sleep(1)
    await datasette.client.get("/")
    assert len(httpx_mock.get_requests()) == 2


@pytest.mark.asyncio
async def test_headers(httpx_mock):
    httpx_mock.add_response(
        url=TEST_URL,
        text="title: Testing TTL",
    )
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
    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    assert requests[0].headers["authorization"] == "Bearer X"


@pytest.mark.asyncio
@pytest.mark.parametrize("already_has_querystring", (True, False))
async def test_cachebust(httpx_mock, already_has_querystring):
    url = TEST_URL
    if already_has_querystring:
        url += "?foo=bar"
    httpx_mock.add_response(text="title: Testing TTL", method="GET")
    datasette = Datasette(
        [],
        memory=True,
        metadata={
            "plugins": {"datasette-remote-metadata": {"url": url, "cachebust": True}}
        },
    )
    await datasette.invoke_startup()
    requests = httpx_mock.get_requests()
    url = str(requests[0].url)
    if already_has_querystring:
        assert "?foo=bar&0." in url
    else:
        assert "?0." in url


@pytest.mark.asyncio
async def test_fails_if_error_on_startup(httpx_mock):
    httpx_mock.add_response(status_code=404)
    datasette = Datasette(
        [],
        memory=True,
        metadata={"plugins": {"datasette-remote-metadata": {"url": TEST_URL}}},
    )
    with pytest.raises(httpx.HTTPStatusError):
        await datasette.invoke_startup()
