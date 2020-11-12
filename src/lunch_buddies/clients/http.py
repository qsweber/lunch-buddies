import requests

import typing


class HttpClient:
    def get(self, url: str, params: typing.Dict[str, str]) -> typing.Any:
        return requests.get(url, params=params)
