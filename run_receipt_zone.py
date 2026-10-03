"""Run the checkout receipt-domain workflow with a real Infrai credential."""
from __future__ import annotations

import argparse

from checkout_zone import CheckoutReceiptRequest, CheckoutZoneService
from infrai_gateway import InfraiGateway


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare a receipt domain after checkout.")
    parser.add_argument("--order-id", required=True)
    parser.add_argument("--customer-email", required=True)
    parser.add_argument("--domain", required=True)
    parser.add_argument("--dkim-name", required=True)
    parser.add_argument("--dkim-content", required=True)
    args = parser.parse_args()
    update = CheckoutZoneService(InfraiGateway.from_environment()).prepare_receipts(
        CheckoutReceiptRequest(
            order_id=args.order_id,
            customer_email=args.customer_email,
            domain=args.domain,
            dkim_name=args.dkim_name,
            dkim_content=args.dkim_content,
        )
    )
    print(f"{update.order_id}: {update.fulfillment_state}; {update.receipt_state}; zone={update.zone_id}")


if __name__ == "__main__":
    main()
