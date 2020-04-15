from datetime import datetime
from typing import List, Optional, TypeVar, Generic

from lunch_buddies.clients.dynamo import DynamoClient, DynamoObject, DynamoValue


T = TypeVar('T')


class Dao(Generic[T]):
    def __init__(
        self,
        dynamo: DynamoClient,
        table_name: str,
    ) -> None:
        self.dynamo = dynamo
        self.table_name = table_name

    def _create_internal(self, dynamo_object: DynamoObject) -> None:
        return self.dynamo.create(self.table_name, dynamo_object)

    def create(self, item: T) -> None:
        ready = self.convert_to_dynamo(item)

        return self._create_internal(ready)

    def _read_internal(self, key: Optional[str], value: Optional[DynamoValue]) -> Optional[List[DynamoObject]]:
        return self.dynamo.read(self.table_name, key, value)

    def read(self, key: Optional[str], value: Optional[DynamoValue]) -> Optional[List[T]]:
        raw = self._read_internal(key, value)

        if not raw:
            return None

        return [
            self.convert_from_dynamo(r)
            for r in raw
        ]

    def read_one_or_die(self, key: Optional[str], value: Optional[DynamoValue]) -> T:
        result = self.read(key, value)

        if not result or len(result) == 0:
            raise Exception('not found')

        return result[0]

    def _convert_datetime_from_dynamo(self, input: DynamoValue) -> datetime:
        return datetime.fromtimestamp(float(input))

    def convert_to_dynamo(self, input: T) -> DynamoObject:
        raise Exception('abstract')

    def convert_from_dynamo(self, input: DynamoObject) -> T:
        raise Exception('abstract')
