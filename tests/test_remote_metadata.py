from time import sleep
from datasette.app import Datasette
import pytest

TEST_URL = "https://www.example.com/metadata.yml"


@pytest.fixture
def non_mocked_hosts():
    return ["localhost"]


@pytest.mark.asyncio
async def test_remote_metadata(httpx_mock):
    httpx_mock.add_response(
        url=TEST_URL,
        data=b"title: This is the remote metadata title",
    )
    datasette = Datasette(
        [],
        memory=True,
        metadata={"plugins": {"datasette-remote-metadata": {"url": TEST_URL}}},
    )
    response = await datasette.client.get("/")
    assert response.status_code == 200
    assert ">This is the remote metadata title<" in response.text


@pytest.mark.asyncio
async def test_ttl(httpx_mock):
    httpx_mock.add_response(
        url=TEST_URL,
        data=b"title: Testing TTL",
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
