from datetime import datetime
from decimal import Decimal
import json
from typing import List, Optional
from uuid import UUID

import boto3
from boto3.dynamodb.conditions import Key


class Dao(object):
    def __init__(self, model_class) -> None:
        self.model_class = model_class

        self.to_dynamo = {
            dict: json.dumps,
            list: json.dumps,
            datetime: lambda v: Decimal(v.timestamp()),
            UUID: str,
            str: str,
            int: int,
            List[str]: json.dumps,
            bool: int,
            Optional[str]: lambda v: '0' if not v else str(v)
        }

        self.from_dynamo = {
            dict: json.loads,
            list: json.loads,
            datetime: lambda v: datetime.fromtimestamp(float(v)),
            UUID: UUID,
            str: str,
            int: int,
            List[str]: json.loads,
            bool: bool,
            Optional[str]: lambda v: None if v == '0' else str(v)
        }

    def _get_dynamo_table_name(self) -> str:
        return 'lunch_buddies_{}'.format(self.model_class.__name__)

    def _get_dynamo_table(self):
        dynamodb = boto3.resource('dynamodb')
        return dynamodb.Table(self._get_dynamo_table_name())

    def _create_internal(self, object_for_dynamo):
        dynamo_table = self._get_dynamo_table()
        return dynamo_table.put_item(Item=object_for_dynamo)

    def _to_dynamo_object(self, model_instance):
        return {
            field: self.to_dynamo[field_type](getattr(model_instance, field))
            for field, field_type in model_instance._field_types.items()
        }

    def _from_dynamo_object(self, dynamo_object):
        return self.model_class(**{
            field: self.from_dynamo[field_type](dynamo_object.get(field)) if dynamo_object.get(field) else None
            for field, field_type in self.model_class._field_types.items()
        })

    def create(self, model_instance):
        object_for_dynamo = self._to_dynamo_object(model_instance)

        self._create_internal(object_for_dynamo)

        return True

    def _read_internal(self, key, value):
        dynamo_table = self._get_dynamo_table()
        if not key:
            return dynamo_table.scan().get('Items')
        else:
            field_type = self.model_class._field_types[key]
            value_dynamo = self.to_dynamo[field_type](value)
            return dynamo_table.query(KeyConditionExpression=Key(key).eq(value_dynamo)).get('Items')

    def read(self, key=None, value=None):
        result = self._read_internal(key, value)

        return [
            self._from_dynamo_object(item)
            for item in result
        ]
