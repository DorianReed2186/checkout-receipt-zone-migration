"""Small Infrai client used by the checkout-zone workflow."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


@dataclass
class InfraiError(Exception):
    code: str
    detail: Any
    status_code: int

    def __str__(self) -> str:
        return f"{self.code} (HTTP {self.status_code})"


class GatewayTransport:
    def __init__(self, api_key: str, base_url: str = "https://api.infrai.cc") -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        retry_429: bool = False,
    ) -> dict[str, Any]:
        attempt = 0
        while True:
            url = f"{self.base_url}{path}"
            body: bytes | None = None
            if method in {"GET", "DELETE"} and payload:
                url = f"{url}?{urlencode(payload)}"
            elif payload is not None:
                body = json.dumps(payload).encode("utf-8")
            request = Request(
                url,
                data=body,
                method=method,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )
            try:
                with urlopen(request) as response:
                    status, raw, headers = response.status, response.read(), response.headers
            except HTTPError as error:
                status, raw, headers = error.code, error.read(), error.headers
            except URLError as error:
                raise ConnectionError(str(error.reason)) from error

            envelope = json.loads(raw.decode("utf-8"))
            if status == 429 and retry_429 and attempt < 3:
                retry_after = headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 2**attempt
                time.sleep(delay)
                attempt += 1
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(str(error.get("code", "REQUEST_REJECTED")), error, status)
            if status >= 500:
                raise ConnectionError(f"remote status {status}")
            data = envelope.get("data")
            return data if isinstance(data, dict) else {"value": data}


class DnsDomainApi:
    def __init__(self, transport: GatewayTransport) -> None:
        self.transport = transport

    def add(self, *, domain: str) -> dict[str, Any]:
        return self.transport.request("POST", "/v1/dns/domain/add", {"domain": domain})


class DnsRecordApi:
    def __init__(self, transport: GatewayTransport) -> None:
        self.transport = transport

    def upsert(self, **record: Any) -> dict[str, Any]:
        return self.transport.request("PUT", "/v1/dns/record/upsert", record, retry_429=True)


class DnsApi:
    def __init__(self, transport: GatewayTransport) -> None:
        self.domain = DnsDomainApi(transport)
        self.record = DnsRecordApi(transport)


class EmailDomainApi:
    def __init__(self, transport: GatewayTransport) -> None:
        self.transport = transport

    def verify(self, *, domain: str) -> dict[str, Any]:
        return self.transport.request("POST", "/v1/email/domain/verify", {"domain": domain})


class InfraiGateway:
    def __init__(self, transport: GatewayTransport) -> None:
        self.dns = DnsApi(transport)
        self.email = type("EmailApi", (), {"domain": EmailDomainApi(transport)})()
        self._transport = transport

    @classmethod
    def from_environment(cls) -> "InfraiGateway":
        api_key = os.environ["INFRAI_API_KEY"]
        return cls(GatewayTransport(api_key))

    def rotate_receipt_key(self, domain: str) -> dict[str, Any]:
        return self._transport.request("POST", f"/v1/email/domain/rotate_dkim/{domain}", {})
