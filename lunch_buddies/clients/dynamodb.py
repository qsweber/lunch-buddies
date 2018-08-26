from typing import List

import boto3
from boto3.dynamodb.conditions import Key


class DynamodbClient(object):
    def put_item(self, table_name: str, row: dict) -> None:
        dynamodb = boto3.resource('dynamodb')
        dynamo_table = dynamodb.Table(table_name)
        dynamo_table.put_item(Item=row)

    def read_items(self, table_name: str, key: str=None, value: str=None) -> List[dict]:
        dynamodb = boto3.resource('dynamodb')
        dynamo_table = dynamodb.Table(table_name)

        if not key:
            return dynamo_table.scan().get('Items')
        else:
            return dynamo_table.query(KeyConditionExpression=Key(key).eq(value)).get('Items')
