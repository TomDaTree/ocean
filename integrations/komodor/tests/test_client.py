import pytest
from typing import Any
from unittest.mock import AsyncMock, patch, MagicMock

from client import KomodorClient, DEFAULT_PAGE_SIZE
from port_ocean.context.ocean import initialize_port_ocean_context
from port_ocean.exceptions.context import PortOceanContextAlreadyInitializedError

NUM_OF_PAGES = 3
MAX_PAGE_SIZE = 1


@pytest.fixture(autouse=True)
def mock_ocean_context() -> None:
    try:
        mock_ocean_app = MagicMock()
        mock_ocean_app.config.integration.config = {
            "api_key": "test_api_key",
            "api_url": "https://api.komodor.com/api/v2",
        }
        mock_ocean_app.integration_router = MagicMock()
        mock_ocean_app.port_client = MagicMock()
        initialize_port_ocean_context(mock_ocean_app)
    except PortOceanContextAlreadyInitializedError:
        pass


@pytest.fixture
def mock_komodor_client() -> KomodorClient:
    return KomodorClient(
        api_key="test_api_key", api_url="https://api.komodor.com/api/v2"
    )


@pytest.mark.asyncio
async def test_get_all_services(mock_komodor_client: KomodorClient) -> None:
    pages = await generate_service_response(NUM_OF_PAGES)
    page_data = [page["services"] for entry in pages for page in entry["data"]]
    api_response = {
        "data": {"services": page_data},
        "meta": {"page": 0, "page_size": NUM_OF_PAGES},
    }

    with patch.object(
        mock_komodor_client, "_send_request", new_callable=AsyncMock
    ) as mock_request:
        mock_request.side_effect = [api_response]

        services = []
        async for service_batch in mock_komodor_client.get_all_services():
            services.extend(service_batch)

        assert len(services) == NUM_OF_PAGES
        assert services == page_data
        mock_request.assert_called_with(
            f"{mock_komodor_client.api_url}/services/search",
            data={
                "kind": ["Deployment"],
                "pagination": {"pageSize": DEFAULT_PAGE_SIZE, "page": 0},
            },
            method="POST",
        )


@pytest.mark.asyncio
async def test_get_all_services_multiple_pages(
    mock_komodor_client: KomodorClient,
) -> None:
    pages = await generate_service_response(NUM_OF_PAGES)

    with patch.object(
        mock_komodor_client, "_send_request", new_callable=AsyncMock
    ) as mock_request:
        mock_request.side_effect = pages

        services = []
        async for service_batch in mock_komodor_client.get_all_services():
            services.extend(service_batch)

        assert len(services) == NUM_OF_PAGES
        assert services == [
            page["services"] for entry in pages for page in entry["data"]
        ]
        assert mock_request.call_count == 4


async def generate_service_response(num_of_pages: int) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    for page in range(num_of_pages):
        pages.append(
            {
                "data": {"services": [{"id": str(page + 1), "type": "deployment"}]},
                "meta": {"page": page},
            }
        )
        if page < num_of_pages:
            meta_dict: dict[str, Any] = pages[page]["meta"]
            meta_dict.update({"nextPage": page + 1})
    return pages
