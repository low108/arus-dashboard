import httpx
import pytest
from app.providers.openrouter import OpenRouterClient, ProviderError


@pytest.mark.asyncio
async def test_valid_openrouter_structured_output(valid_extraction):
    async def handler(request):
        return httpx.Response(200, json={"choices": [{"message": {"content": valid_extraction.model_dump_json()}}]})
    result = await OpenRouterClient(api_key="test-only", transport=httpx.MockTransport(handler)).extract([(1, "synthetic")])
    assert result.institution == "Meridian Bank"


@pytest.mark.asyncio
async def test_malformed_openrouter_json_is_rejected():
    async def handler(request): return httpx.Response(200, json={"choices": [{"message": {"content": "not-json"}}]})
    with pytest.raises(ProviderError, match="MalformedProviderOutput"):
        await OpenRouterClient(api_key="test-only", transport=httpx.MockTransport(handler)).extract([(1, "synthetic")])


@pytest.mark.asyncio
async def test_timeout_has_bounded_retries():
    calls = 0
    async def handler(request):
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("timeout", request=request)
    with pytest.raises(ProviderError):
        await OpenRouterClient(api_key="test-only", retries=2, transport=httpx.MockTransport(handler)).extract([(1, "synthetic")])
    assert calls == 3


@pytest.mark.asyncio
async def test_real_verification_shape_uses_minimal_request():
    async def handler(request):
        assert b"Connectivity check" in request.content
        assert b"statement" not in request.content.lower()
        return httpx.Response(200, headers={"x-request-id": "safe-request-id"}, json={"choices": [{"message": {"content": '{"status":"ok"}'}}]})
    result = await OpenRouterClient(api_key="test-only", transport=httpx.MockTransport(handler)).verify()
    assert result.status == "ok" and result.request_id == "safe-request-id"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_openrouter_connectivity_when_configured():
    client = OpenRouterClient()
    status = await client.health()
    if status.status == "not_configured": pytest.skip("OPENROUTER_API_KEY is not configured")
    assert status.provider == "OpenRouter"
