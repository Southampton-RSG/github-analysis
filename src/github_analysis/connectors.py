import abc
import datetime
import json
import logging
import time
import typing

from decouple import config
import requests

logger = logging.getLogger(__name__)

JSONType = typing.Union[
    typing.Mapping[str, 'JSONType'],
    typing.List['JSONType'],
    str,
    int,
    float,
    bool,
    None,
]  # yapf: disable

ConnectorSingleResponseType = typing.Dict[str, JSONType]
ConnectorMultipleResponseType = typing.List[typing.Dict[str, JSONType]]

ConnectorResponseType = typing.Union[
    ConnectorSingleResponseType,
    ConnectorMultipleResponseType,
]  # yapf: disable


class ResponseNotFoundError(ValueError):
    pass


def wait_until(end_datetime: datetime.datetime) -> None:
    """Wait until a given time.

    This code was taken with modification from https://stackoverflow.com/posts/54774814/revisions
    under the CC BY-SA 4.0 license.
    """
    while True:
        delta = (end_datetime - datetime.datetime.now()).total_seconds()

        if delta < 0:
            return  # In case end_datetime was in past to begin with

        time.sleep(max(delta / 2, 0.1))

        if delta <= 0.1:
            return


class BaseConnector(abc.ABC):
    @abc.abstractmethod
    def __init__(self, *args, **kwargs):
        pass

    def get(self, **kwargs) -> ConnectorResponseType:
        """Get the JSON representation of a record from a data source.

        Keyword arguments populate the location pattern given when the
        connector was initialised.
        """
        response: ConnectorResponseType = self._get(**kwargs)
        return self._annotate_response(response, '_repo_name', f'{kwargs["owner"]}/{kwargs["repo"]}')

    @abc.abstractmethod
    def _get(self, **kwargs) -> ConnectorResponseType:
        """Get the JSON representation of a record from a data source.

        Keyword arguments populate the location pattern given when the
        connector was initialised.
        """
        raise NotImplementedError

    @classmethod
    def _annotate_response(cls, response: ConnectorResponseType, key: str, value: str) -> ConnectorResponseType:
        """Annotate the response (or responses if a list) with an additional field."""
        # Response will always be either a JSON object...
        if isinstance(response, dict):
            response[key] = value

        # or an array of objects
        elif isinstance(response, list):
            for item in response:
                cls._annotate_response(item, key, value)

        return response


class TryEachConnector(BaseConnector):
    """Connector which tries a number of subconnectors, returning the first result."""
    def __init__(self, *connectors: BaseConnector):
        self._connectors = connectors

    def _get(self, **kwargs) -> ConnectorResponseType:
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


def join_curl_responses(response: str) -> ConnectorResponseType:
    """Join JSON blocks from concatenated cURL responses."""
    # cURL headers are separated from content by a blank line
    # The content starts with a '[' line for list-type responses
    responses = response.split('\n\n[')

    # Discard the first bit - it's just the first cURL header
    responses = responses[1:]

    # Strip the trailing cURL header and close bracket from the end of each block
    responses = [r.rsplit('\n]\nHTTP', maxsplit=1)[0] for r in responses]

    # Concatenate responses
    responses = ','.join(responses)

    # Add opening bracket
    responses = '[' + responses

    return json.loads(responses)


class FileConnector(Connector):
    """Connector to get JSON data from curl responses saved to file."""
    def _get(self, **kwargs) -> ConnectorResponseType:
        location = self._location_pattern.format(**kwargs)
        logger.debug('Trying file connector')

        try:
            with open(location) as fp:
                response = fp.read()

                try:
                    content: ConnectorResponseType = json.loads(response.split('\n\n', maxsplit=1)[1].strip())

                except json.JSONDecodeError:
                    try:
                        content: ConnectorResponseType = join_curl_responses(response)

                    except json.JSONDecodeError as exc:
                        logger.warning('Parsing file failed: %s', location)
                        raise ResponseNotFoundError from exc

                except IndexError as exc:
                    logger.warning('Likely no content in file: %s', location)
                    raise ResponseNotFoundError from exc

                logger.debug('Fetched data from file: %s', location)
                return content

        except FileNotFoundError as exc:
            logger.debug('File connector failed')
            raise ResponseNotFoundError from exc


class RequestsConnector(Connector):
    """Connector to get JSON data from a URL using Requests."""
    def _get_with_ratelimit(self, location: str, *, follow_pagination: bool = True) -> requests.Response:
        r = requests.get(location, **self._kwargs)

        try:
            logger.info('Rate limit remaining: %s', r.headers.get('x-ratelimit-remaining'))

        except KeyError:
            pass

        if not r.ok:
            if r.headers.get('x-ratelimit-remaining', -1) == '0':
                reset_time = datetime.datetime.fromtimestamp(int(r.headers['x-ratelimit-reset']))

                logger.warning('Rate limited - waiting until %s', reset_time)
                wait_until(reset_time)

                return self._get_with_ratelimit(location, follow_pagination=follow_pagination)

            logger.debug('Requests connector failed')
            raise ResponseNotFoundError

        return r

    def _get(self, *, follow_pagination: bool = True, **kwargs) -> ConnectorResponseType:
        location = self._location_pattern.format(**kwargs)
        logger.debug('Trying requests connector')

        r = self._get_with_ratelimit(location, follow_pagination=follow_pagination)
        content: ConnectorResponseType = r.json()

        if follow_pagination and isinstance(content, list):
            while 'next' in r.links:
                r = self._get_with_ratelimit(r.links['next']['url'], follow_pagination=follow_pagination)

                content.extend(r.json())

        logger.debug('Fetched data from URL: %s', location)
        return content


class GitHubConnector(RequestsConnector):
    def __init__(self, location_pattern: str, **kwargs):
        location_pattern = 'https://api.github.com/' + location_pattern.lstrip('/')

        headers = kwargs.get('headers', {})
        headers.update({'Authorization': f'token {config("GITHUB_AUTH_TOKEN")}'})
        kwargs['headers'] = headers

        super().__init__(location_pattern, **kwargs)
