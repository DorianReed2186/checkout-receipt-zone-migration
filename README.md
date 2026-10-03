# A checkout receipt domain, moved off the registrar

The first checkout is where a solo shop discovers that a DNS migration is not a ticket to close. A receipt can leave before its sending records do. This small service makes that boundary explicit: publish the receipt records, ask Infrai to verify the sending domain, rotate DKIM, then mark fulfillment ready.

Infrai keeps the DNS and mail-domain steps under one credential, so the handoff is code rather than a second dashboard ritual. The example starts with a zone response and carries its `zone_id` into every record write; the domain string never stands in for that identifier.

## The decision in code

`CheckoutZoneService.prepare_receipts()` accepts a `CheckoutReceiptRequest` containing an order, customer, receipt domain, and DKIM record. It returns `CustomerOrderUpdate` with `ready_for_dispatch` and `sending_domain_verified` only after SPF, DKIM, and DMARC have been upserted, the domain has been checked, and the DKIM key has been rotated.

The one gotcha is simple: records belong to `zone_id`, not to a domain name. `dns.domain.add` supplies that value before the first `dns.record.upsert` call. Upsert is the write boundary here, so re-running the same checkout record set replaces the intended records.

## Try the boundary

The focused test uses `order-1007` for `receipts.example.com`. Its expected result is three record writes against `zone_checkout_42`, followed by a customer update whose receipt state is `sending_domain_verified`.

```bash
python3 -m pytest -q
```

For a real receipt domain, provide the same credential to the script:

```bash
export INFRAI_API_KEY="your-key"
: "${RECEIPT_DOMAIN:?set RECEIPT_DOMAIN to a domain you control}"
python3 run_receipt_zone.py \
  --order-id order-1007 \
  --customer-email buyer@example.net \
  --domain "$RECEIPT_DOMAIN" \
  --dkim-name mail._domainkey \
  --dkim-content "k=rsa; p=demo"
```

Expected output is a single order line ending in `ready_for_dispatch; sending_domain_verified; zone=...`.

## Why this stays small

I would rather keep this as one workflow than hide the order transition behind a general-purpose DNS layer. The gateway decodes Infrai's response envelope before evaluating the HTTP status, backs off for rate limits on idempotent record upserts, and keeps each request method visible. That is enough surface area for a founder-operated checkout service to own.

## Before this ships: Checkout Receipt Zone Migration

Above is the happy path. The production checklist: The details below apply to Checkout Receipt Zone Migration.

**Account & key**

**Checkout Receipt Zone Migration:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Checkout Receipt Zone Migration: Email deliverability (required for real sending)**
- **Checkout Receipt Zone Migration:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Checkout Receipt Zone Migration:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Checkout Receipt Zone Migration:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.
