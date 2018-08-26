import datetime
from decimal import Decimal
import json
from typing import TypeVar, Generic, List
from uuid import UUID

from lunch_buddies.clients.dynamodb import DynamodbClient

T = TypeVar('T', bound=tuple)


class Dao(Generic[T]):
    def __init__(self, model_class: T, table_name_root: str, dynamodb_client: DynamodbClient) -> None:
        self.model_class = model_class
        self.table_name = 'lunch_buddies_{}'.format(table_name_root)
        self.dynamodb_client = dynamodb_client

    def _as_dynamo_object_hook(self, field, value):
        return value

    def _as_dynamo_object(self, model_instance):
        object_for_dynamo = {}
        for field, field_type in model_instance._field_types.items():
            value = getattr(model_instance, field)
            if field_type == dict:
                value = json.dumps(value)
            elif field_type == list:
                value = json.dumps(value)
            elif field_type == datetime.datetime:
                value = Decimal(value.timestamp())
            elif field_type == UUID:
                value = str(value)
            elif field_type == str:
                value = value
            elif field_type == int:
                value = value
            else:
                value = self._as_dynamo_object_hook(field, value)

            object_for_dynamo[field] = value

        return object_for_dynamo

    def create(self, model_instance: T):
        object_for_dynamo = self._as_dynamo_object(model_instance)

        self.dynamodb_client.put_item(self.table_name, object_for_dynamo)

        return True

    def _as_model_hook(self, field, value):
        return value

    def _as_model(self, dynamo_object: dict) -> T:
        kwargs = {}
        for field, field_type in self.model_class._field_types.items():
            value = dynamo_object.get(field)
            if value is None:
                value = value
            if field_type == dict:
                value = json.loads(value)
            elif field_type == list:
                value = json.loads(value)
            elif field_type == datetime.datetime:
                value = datetime.datetime.fromtimestamp(float(value))
            elif field_type == UUID:
                value = UUID(value)
            elif field_type == str:
                value = value
            elif field_type == int:
                value = value
            else:
                value = self._as_model_hook(field, value)

            kwargs[field] = value

        return self.model_class(**kwargs)

    def read(self, key: str=None, value: str=None) -> List[T]:
        result = self.dynamodb_client.read_items(self.table_name, key, value)

        return [
            self._as_model(item)
            for item in result
        ]
