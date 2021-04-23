import abc
import json
import logging
import typing

import requests

logger = logging.getLogger(__name__)

JSONType = typing.Dict[str, typing.Any]


class ResponseNotFoundError(ValueError):
    pass


class BaseConnector(abc.ABC):
    @abc.abstractmethod
    def get(self, **kwargs) -> JSONType:
        """Get the JSON representation of a record from a data source.

        Keyword arguments populate the location pattern given when the
        connector was initialised.
        """
        raise NotImplementedError


class TryEachConnector(BaseConnector):
    """Connector which tries a number of subconnectors, returning the first result."""
    def __init__(self, *connectors: BaseConnector):
        self._connectors = connectors

    def get(self, **kwargs) -> JSONType:
        for connector in self._connectors:
            try:
                return connector.get(**kwargs)

            except ResponseNotFoundError:
                pass

        raise ResponseNotFoundError


class Connector(BaseConnector):
    def __init__(self, location_pattern: str, **kwargs):
        self._location_pattern = location_pattern
        self._kwargs = kwargs


class FileConnector(Connector):
    """Connector to get JSON data from curl responses saved to file."""
    def get(self, **kwargs) -> JSONType:
        location = self._location_pattern.format(**kwargs)
        try:
            with open(location) as fp:
                response = fp.read()
                content = response.split('\n\n')[1]
                content = json.loads(content)
                content['_repo_name'] = f'{kwargs["owner"]}/{kwargs["repo"]}'
                return content

        except FileNotFoundError as exc:
            raise ResponseNotFoundError from exc


class RequestsConnector(Connector):
    """Connector to get JSON data from a URL using Requests."""
    def get(self, **kwargs) -> JSONType:
        location = self._location_pattern.format(**kwargs)
        r = requests.get(location, **self._kwargs)

        if not r.ok:
            raise ResponseNotFoundError

        content = r.json()
        content['_repo_name'] = f'{kwargs["owner"]}/{kwargs["repo"]}'
        return content
