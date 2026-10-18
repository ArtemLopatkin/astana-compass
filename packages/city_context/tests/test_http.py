"""Offline I/O boundary tests, with no requests to hosted providers."""
import asyncio
from datetime import timezone

import httpx
import pytest

from astana_city_context.common import JsonHTTP, ProviderError, parse_instant


@pytest.mark.parametrize("value", ["2026-10-19", "2026-10-19T12:00:00", "tomorrow", "2026-02-30T12:00:00Z", "2026-10-19T25:00:00Z", "2026-10-19 12:00:00Z", "2026-10-19T12:00:00+05:99", "2026-10-19T12:00:00+00:60", "2026-10-19T12:00:00-24:00"])
def test_invalid_instant(value):
    with pytest.raises(ProviderError, match="invalid_request"):
        parse_instant(value)


def test_instant_is_converted_not_relabelled():
    value = parse_instant("2026-10-19T12:00:00+05:00")
    assert value.hour == 7 and value.tzinfo == timezone.utc


@pytest.mark.parametrize("status,expected,calls", [(500, "provider_unavailable", 2), (503, "provider_unavailable", 2), (429, "rate_limited", 1), (401, "provider_unavailable", 1), (302, "provider_unavailable", 1)])
def test_provider_failure_sanitized_bounded_and_no_redirect(status, expected, calls):
    async def run():
        seen = []

        def respond(request):
            seen.append(request)
            return httpx.Response(status, text="secret provider body", headers={"Location": "https://other.invalid/"})

        client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
        http = JsonHTTP(client=client)
        try:
            with pytest.raises(ProviderError) as failure:
                await http.request("GET", "https://weather.invalid/", headers={"Authorization": "backend-secret"})
            assert str(failure.value) == expected
            assert "secret" not in str(failure.value)
            assert len(seen) == calls
        finally:
            await http.aclose()
            assert client.is_closed
    asyncio.run(run())


def test_retry_transient_failure_and_decode_valid_json():
    async def run():
        count = 0

        def respond(request):
            nonlocal count
            count += 1
            if count == 1:
                raise httpx.ReadTimeout("private coordinates and token", request=request)
            return httpx.Response(200, json={"ok": True})

        http = JsonHTTP(client=httpx.AsyncClient(transport=httpx.MockTransport(respond)))
        try:
            assert await http.request("POST", "https://routing.invalid/", json={"coordinates": []}) == {"ok": True}
            assert count == 2
        finally:
            await http.aclose()
    asyncio.run(run())


@pytest.mark.parametrize("body", [b"[]", b"null", b"bad json", b'{"x":NaN}', b'{"x":Infinity}', b'{"huge": "' + b"x" * 1024 + b'"}'])
def test_invalid_or_oversized_payload(body):
    async def run():
        http = JsonHTTP(max_bytes=100, client=httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200, content=body))))
        try:
            with pytest.raises(ProviderError, match="invalid_provider_response"):
                await http.request("GET", "https://provider.invalid/")
        finally:
            await http.aclose()
    asyncio.run(run())


def test_cancelling_close_keeps_transport_shutdown_alive_and_reawaitable():
    async def run():
        started, release = asyncio.Event(), asyncio.Event()

        class Transport(httpx.AsyncBaseTransport):
            finished = False
            close_calls = 0

            async def aclose(self):
                self.close_calls += 1
                started.set()
                await release.wait()
                self.finished = True

        transport = Transport()
        http = JsonHTTP(client=httpx.AsyncClient(transport=transport))
        closing = asyncio.create_task(http.aclose())
        await started.wait()
        closing.cancel()
        with pytest.raises(asyncio.CancelledError):
            await closing
        release.set()
        await http.aclose()
        assert transport.finished and transport.close_calls == 1
    asyncio.run(run())


def test_total_timeout_includes_provider_wait_and_cancellation_propagates():
    async def run():
        async def respond(_):
            await asyncio.sleep(1)
            return httpx.Response(200, json={})

        http = JsonHTTP(timeout_seconds=0.02, client=httpx.AsyncClient(transport=httpx.MockTransport(respond)))
        try:
            with pytest.raises(ProviderError) as failure:
                await http.request("GET", "https://provider.invalid/")
            assert failure.value.retryable
            task = asyncio.create_task(http.request("GET", "https://provider.invalid/"))
            await asyncio.sleep(0)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        finally:
            await http.aclose()
    asyncio.run(run())


def test_close_is_idempotent_and_requests_after_close_fail():
    async def run():
        http = JsonHTTP()
        await http.aclose()
        await http.aclose()
        with pytest.raises(ProviderError, match="provider_unavailable"):
            await http.request("GET", "https://provider.invalid/")
    asyncio.run(run())
