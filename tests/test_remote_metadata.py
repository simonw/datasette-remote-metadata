from datasette.app import Datasette
import pytest


@pytest.fixture
def non_mocked_hosts():
    return ["localhost"]


@pytest.mark.asyncio
async def test_remote_metadata(httpx_mock):
    httpx_mock.add_response(
        url="https://www.example.com/metadata.yml",
        data=b"title: This is the remote metadata title",
    )
    datasette = Datasette(
        [],
        memory=True,
        metadata={
            "plugins": {
                "datasette-remote-metadata": {
                    "url": "https://www.example.com/metadata.yml"
                }
            }
        },
    )
    response = await datasette.client.get("/")
    assert response.status_code == 200
    assert ">This is the remote metadata title<" in response.text
