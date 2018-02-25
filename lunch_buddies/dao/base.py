import datetime
from decimal import Decimal
import json
from uuid import UUID

import boto3
from boto3.dynamodb.conditions import Key


class Dao(object):
    def __init__(self, model_class):
        self.model_class = model_class

    def _get_dynamo_table_name(self):
        return 'lunch_buddies_{}'.format(self.model_class.__name__)

    def _get_dynamo_table(self):
        dynamodb = boto3.resource('dynamodb')
        return dynamodb.Table(self._get_dynamo_table_name())

    def _create_internal(self, object_for_dynamo):
        dynamo_table = self._get_dynamo_table()
        return dynamo_table.put_item(Item=object_for_dynamo)

    def create(self, model_instance):
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

            object_for_dynamo[field] = value

        self._create_internal(object_for_dynamo)

        return True

    def _as_model(self, model_class, dynamo_object):
        kwargs = {}
        for field, field_type in model_class._field_types.items():
            value = dynamo_object[field]
            if field_type == dict:
                value = json.loads(value)
            elif field_type == list:
                value = json.loads(value)
            elif field_type == datetime.datetime:
                value = datetime.datetime.fromtimestamp(float(value))
            elif field_type == UUID:
                value = UUID(value)
            kwargs[field] = value

        return model_class(**kwargs)

    def _read_internal(self, key, value):
        dynamo_table = self._get_dynamo_table()
        if not key:
            return dynamo_table.query().get('Items')
        else:
            return dynamo_table.query(KeyConditionExpression=Key(key).eq(value)).get('Items')

    def read(self, key=None, value=None):
        result = self._read_internal(key, value)

        return [
            self._as_model(self.model_class, item)
            for item in result
        ]
