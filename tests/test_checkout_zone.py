from checkout_zone import CheckoutReceiptRequest, CheckoutZoneService


class Domain:
    def add(self, *, domain: str) -> dict[str, object]:
        assert domain == "receipts.example.com"
        return {"zone_id": "zone_checkout_42"}


class Records:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def upsert(self, **record: object) -> dict[str, object]:
        self.calls.append(record)
        return {"record_id": str(len(self.calls))}


class EmailDomain:
    def __init__(self) -> None:
        self.verified: list[str] = []

    def verify(self, *, domain: str) -> dict[str, object]:
        self.verified.append(domain)
        return {"domain": domain}


class Dns:
    def __init__(self) -> None:
        self.domain = Domain()
        self.record = Records()


class Email:
    def __init__(self) -> None:
        self.domain = EmailDomain()


class FakeGateway:
    def __init__(self) -> None:
        self.dns = Dns()
        self.email = Email()
        self.rotated: list[str] = []

    def rotate_receipt_key(self, domain: str) -> dict[str, object]:
        self.rotated.append(domain)
        return {"domain": domain}


def test_checkout_publishes_zone_records_before_customer_is_ready() -> None:
    gateway = FakeGateway()
    update = CheckoutZoneService(gateway).prepare_receipts(
        CheckoutReceiptRequest(
            order_id="order-1007",
            customer_email="buyer@example.net",
            domain="receipts.example.com",
            dkim_name="mail._domainkey",
            dkim_content="k=rsa; p=demo",
        )
    )

    assert [call["name"] for call in gateway.dns.record.calls] == ["@", "mail._domainkey", "_dmarc"]
    assert {call["zone_id"] for call in gateway.dns.record.calls} == {"zone_checkout_42"}
    assert gateway.email.domain.verified == ["receipts.example.com"]
    assert gateway.rotated == ["receipts.example.com"]
    assert update.receipt_state == "sending_domain_verified"
    assert update.fulfillment_state == "ready_for_dispatch"
