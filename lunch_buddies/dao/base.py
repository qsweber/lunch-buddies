from datetime import datetime
from decimal import Decimal
from typing import List, Optional, TypeVar, Generic

from lunch_buddies.clients.dynamo import DynamoClient, DynamoObject, DynamoValue


T = TypeVar("T")


class Dao(Generic[T]):
    def __init__(
        self, dynamo: DynamoClient, table_name: str, unique_key: List[str],
    ) -> None:
        self.dynamo = dynamo
        self.table_name = table_name
        self.unique_key = unique_key

    def _create_internal(self, dynamo_object: DynamoObject) -> None:
        return self.dynamo.create(self.table_name, dynamo_object)

    def create(self, item: T) -> None:
        ready = self.convert_to_dynamo(item)

        return self._create_internal(ready)

    def _read_internal(
        self, key: Optional[str], value: Optional[DynamoValue]
    ) -> Optional[List[DynamoObject]]:
        return self.dynamo.read(self.table_name, key, value)

    def read(self, key: Optional[str], value: Optional[DynamoValue]) -> List[T]:
        raw = self._read_internal(key, value)

        if not raw:
            return []

        return [self.convert_from_dynamo(r) for r in raw]

    def read_one(self, key: Optional[str], value: Optional[DynamoValue]) -> Optional[T]:
        result = self.read(key, value)

        if len(result) == 0:
            return None

        return result[0]

    def read_one_or_die(self, key: Optional[str], value: Optional[DynamoValue]) -> T:
        result = self.read_one(key, value)

        if not result:
            raise Exception("not found")

        return result

    def _convert_datetime_to_dynamo(self, var: datetime) -> DynamoValue:
        return Decimal(var.timestamp())

    def _convert_datetime_from_dynamo(self, var: DynamoValue) -> datetime:
        if not var:
            raise Exception("valid datetime not provided")

        return datetime.fromtimestamp(float(var))

    def convert_to_dynamo(self, var: T) -> DynamoObject:
        raise Exception("abstract")

    def convert_from_dynamo(self, var: DynamoObject) -> T:
        raise Exception("abstract")

    def update(self, original: T, updated: T) -> None:
        original_dyanmo = self.convert_to_dynamo(original)
        updated_dynamo = self.convert_to_dynamo(updated)

        unique_key = {
            unique_key_column: original_dyanmo[unique_key_column]
            for unique_key_column in self.unique_key
        }

        unique_key = {}
        for unique_key_column in self.unique_key:
            if original_dyanmo[unique_key_column] != updated_dynamo[unique_key_column]:
                raise Exception("updated entity must have the same key as the original")

            unique_key[unique_key_column] = original_dyanmo[unique_key_column]

        updated_attributes: List[str] = []
        for key, value in updated_dynamo.items():
            if value != original_dyanmo[key]:
                self.dynamo.update(self.table_name, unique_key, key, value)
                updated_attributes.append(key)

        return
