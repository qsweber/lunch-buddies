import requests


class HttpClient:
    def get(self, url: str, params: dict, **kwargs):
        return requests.get(url, params=params, **kwargs)
