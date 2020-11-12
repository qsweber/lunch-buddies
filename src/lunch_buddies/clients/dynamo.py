from decimal import Decimal
import os
from typing import cast, Optional, Union, Dict, List

import boto3  # type: ignore
from boto3.dynamodb.conditions import Key  # type: ignore

DynamoValue = Union[str, int, Decimal, None]
DynamoObject = Dict[str, DynamoValue]


class DynamoClient:
    def __init__(self) -> None:
        if os.environ.get("IS_TEST"):
            self.dynamo = None
            return

        self.dynamo = boto3.resource("dynamodb")

    def create(self, table_name: str, data: DynamoObject) -> None:
        if not self.dynamo:
            return

        table = self.dynamo.Table(table_name)
        table.put_item(Item=data)

    def read(
        self, table_name: str, key: Optional[str], value: Optional[DynamoValue]
    ) -> Optional[List[DynamoObject]]:
        if not self.dynamo:
            return None

        table = self.dynamo.Table(table_name)

        if not key:
            return cast(Optional[List[DynamoObject]], table.scan().get("Items"))
        else:
            return cast(
                Optional[List[DynamoObject]],
                table.query(KeyConditionExpression=Key(key).eq(value)).get("Items"),
            )

    def update(
        self, table_name: str, key: DynamoObject, column: str, new_value: DynamoValue
    ) -> None:
        if not self.dynamo:
            return None

        table = self.dynamo.Table(table_name)

        table.update_item(
            Key=key, AttributeUpdates={column: {"Value": new_value, "Action": "PUT"}}
        )
