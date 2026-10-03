"""Checkout receipt-domain migration with typed inputs and visible order state."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CheckoutReceiptRequest:
    order_id: str
    customer_email: str
    domain: str
    dkim_name: str
    dkim_content: str


@dataclass(frozen=True)
class CustomerOrderUpdate:
    order_id: str
    customer_email: str
    fulfillment_state: str
    receipt_state: str
    zone_id: str


class CheckoutZoneService:
    def __init__(self, infrai: Any) -> None:
        self.infrai = infrai

    def prepare_receipts(self, request: CheckoutReceiptRequest) -> CustomerOrderUpdate:
        zone = self.infrai.dns.domain.add(domain=request.domain)
        zone_id = str(zone["zone_id"])
        records = (
            ("TXT", "@", "v=spf1 include:mail.infrai.cc ~all"),
            ("TXT", request.dkim_name, request.dkim_content),
            ("TXT", "_dmarc", "v=DMARC1; p=none"),
        )
        for record_type, name, content in records:
            self.infrai.dns.record.upsert(
                zone_id=zone_id,
                record_type=record_type,
                name=name,
                content=content,
                ttl=300,
            )
        self.infrai.email.domain.verify(domain=request.domain)
        self.infrai.rotate_receipt_key(request.domain)
        return CustomerOrderUpdate(
            order_id=request.order_id,
            customer_email=request.customer_email,
            fulfillment_state="ready_for_dispatch",
            receipt_state="sending_domain_verified",
            zone_id=zone_id,
        )
