import abc
import json
import logging
import typing

import requests

logger = logging.getLogger(__name__)

JSONType = typing.Dict[str, typing.Any]


class ResponseNotFoundError(ValueError):
    pass


def try_all(connectors, connector_method: str = 'get'):
    def inner(**kwargs) -> JSONType:
        for connector in connectors:
            try:
                return getattr(connector, connector_method)(**kwargs)

            except ResponseNotFoundError:
                pass

        raise ResponseNotFoundError

    return inner


class Connector(abc.ABC):
    def __init__(self, location_pattern: str, **kwargs):
        self._location_pattern = location_pattern
        self._kwargs = kwargs

    @abc.abstractmethod
    def get(self, **kwargs) -> JSONType:
        """Get the JSON representation of a record from a data source.

        Keyword arguments populate the location pattern given when the
        connector was initialised.
        """
        raise NotImplementedError


class FileConnector(Connector):
    """Connector to get JSON data from curl responses saved to file."""
    def get(self, **kwargs) -> JSONType:
        location = self._location_pattern.format(**kwargs)
        try:
            with open(location) as fp:
                response = fp.read()
                content = response.split('\n\n')[1]
                return json.loads(content)

        except FileNotFoundError as exc:
            raise ResponseNotFoundError from exc


class RequestsConnector(Connector):
    """Connector to get JSON data from a URL using Requests."""
    def get(self, **kwargs) -> JSONType:
        location = self._location_pattern.format(**kwargs)
        r = requests.get(location, **self._kwargs)

        if not r.ok:
            raise ResponseNotFoundError

        return r.json()
