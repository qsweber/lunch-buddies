import os
from datetime import datetime, timedelta
from typing import NamedTuple, List, Optional

import stripe


class Customer(NamedTuple):
    id: str


class Invoice(NamedTuple):
    id: str
    created_at: datetime


class LineItem(NamedTuple):
    amount: float
    description: str


class StripeClient:
    def __init__(self):
        if os.environ.get("IS_TEST") or "STRIPE_API_KEY" not in os.environ:
            self.stripe = None
            return

        self.stripe = stripe
        self.stripe.api_key = os.environ["STRIPE_API_KEY"]

    def create_customer(
        self, name: str, email: str, team_name: str
    ) -> Optional[Customer]:
        if not self.stripe:
            return None

        response = self.stripe.Customer.create(
            name=name, email=email, description=team_name,
        )

        return Customer(id=response["id"])

    def update_customer(
        self, customer_id: str, name: str, email: str, team_name: str
    ) -> None:
        if not self.stripe:
            return None

        self.stripe.Customer.modify(
            customer_id, name=name, email=email, description=team_name
        )

    def latest_invoice_for_customer(self, customer_id: str) -> Optional[Invoice]:
        invoices = self.stripe.Invoice.list(customer=customer_id, limit=1)

        if len(invoices["data"]) == 0:
            return None

        return Invoice(
            id=invoices["data"][0]["id"],
            created_at=datetime.fromtimestamp(invoices["data"][0]["created"]),
        )

    def create_invoice(
        self, customer: Customer, line_items: List[LineItem]
    ) -> Optional[Invoice]:
        if not self.stripe:
            return None

        for line_item in line_items:
            self.stripe.InvoiceItem.create(
                customer=customer.id,
                amount=line_item.amount,
                currency="USD",
                description=line_item.description,
            )

        result = self.stripe.Invoice.create(
            customer=customer.id,
            auto_advance=True,
            collection_method="send_invoice",
            due_date=round((datetime.now() + timedelta(days=30)).timestamp()),
            description="memo",
        )

        return Invoice(
            id=result["data"]["id"],
            created_at=datetime.fromtimestamp(result["data"]["created"]),
        )
