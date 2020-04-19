import os
from typing import NamedTuple, List
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
        if os.environ.get('IS_TEST'):
            self.stripe = None
            return

        self.stripe = stripe
        self.stripe.api_key = 'TODO'  # get this from env

    def create_customer(self, name: str, email: str, team_name: str) -> Customer:
        response = self.stripe.Customer.create(
            name=name,
            email=email,
            description=team_name,
        )

        return Customer(id=response['id'])

    def update_customer(self, customer_id: str, name: str, email: str, team_name: str) -> None:
        self.stripe.Customer.modify(customer_id, name=name, email=email, description=team_name)

    def create_invoice(self, line_items: List[LineItem]) -> None:
        for line_item in line_items:
            self.stripe.InvoiceItem.create(
                customer=line_item.customer.id,
                amount=line_item.amount,
                currency=line_item.currency,
                description=line_item.description,
            )

        self.stripe.Invoice.create(customer=line_items[0].customer.id, auto_advance=True, collection_method='send_invoice')
