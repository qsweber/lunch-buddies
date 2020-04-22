import os
from typing import NamedTuple, List, Optional
from decimal import Decimal

import stripe


class Customer(NamedTuple):
    id: str


class LineItem(NamedTuple):
    customer: Customer
    amount: Decimal
    currency: str
    description: str


class StripeClient:
    def __init__(self):
        if os.environ.get('IS_TEST') or not os.environ['STRIPE_API_KEY']:
            self.stripe = None
            return

        self.stripe = stripe
        self.stripe.api_key = os.environ['STRIPE_API_KEY']

    def create_customer(self, name: str, email: str, team_name: str) -> Optional[Customer]:
        if not self.stripe:
            return None

        response = self.stripe.Customer.create(
            name=name,
            email=email,
            description=team_name,
        )

        return Customer(id=response['id'])

    def update_customer(self, customer_id: str, name: str, email: str, team_name: str) -> None:
        if not self.stripe:
            return None

        self.stripe.Customer.modify(customer_id, name=name, email=email, description=team_name)

    def create_invoice(self, line_items: List[LineItem]) -> None:
        if not self.stripe:
            return None

        for line_item in line_items:
            self.stripe.InvoiceItem.create(
                customer=line_item.customer.id,
                amount=line_item.amount,
                currency=line_item.currency,
                description=line_item.description,
            )

        self.stripe.Invoice.create(customer=line_items[0].customer.id, auto_advance=True, collection_method='send_invoice')
