import abc
import base64
import logging
import pathlib
import typing

import pymongo
import pymongo.collection
from pymongo.errors import DocumentTooLarge

from github_analysis import connectors, db

logger = logging.getLogger(__name__)

FetcherFunc = typing.Callable[[str, bool], connectors.ConnectorResponseType]
TransformerFunc = typing.Callable[[connectors.ConnectorResponseType], connectors.ConnectorResponseType]

PathLike = typing.Union[str, pathlib.Path]


class DataExists(Exception):
    pass


class CouldNotStoreData(Exception):
    pass


def make_fetcher(
    name: str,
    collection: pymongo.collection.Collection,
    connector: connectors.BaseConnector,
    *,
    transformer: TransformerFunc = lambda x: x,
    key_name: str = 'node_id'
) -> FetcherFunc:
    """Build a fetcher function for a specific content type.

    :param name: Name of the fetcher for logging purposes
    :param collection: MongoDB collection to store responses
    :param connector: Data connector with which to fetch the data
    :param transformer: Function applied to the response before saving
    :param key_name: MonogDB field name to use for update query
    """
    status_collection = db.collection('status', indexes=[name])

    def update_mongo(response: connectors.ConnectorResponseType) -> None:
        """Update a record or multiple records for a response in the MongoDB collection."""
        if isinstance(response, dict):
            try:
                collection.replace_one({key_name: response[key_name]}, response, upsert=True)

            except KeyError:
                logger.warning('Response did not contain expected key: %s', key_name)

            except DocumentTooLarge:
                logger.error('Data did not fit within maximum record size')
                raise

        elif isinstance(response, list) and len(response) > 0:
            try:
                collection.bulk_write(
                    [pymongo.ReplaceOne({key_name: item[key_name]}, item, upsert=True) for item in response],
                    ordered=False
                )

            except DocumentTooLarge:
                raise CouldNotStoreData()

    def fetch(repo_name: str, skip_existing: bool = False) -> connectors.ConnectorResponseType:
        """Function to fetch data for a specific repo.

        The content type and connectors used are set by closure.

        :param repo_name: Name of repository to fetch in 'username/reponame' format
        :param skip_existing: Skip if data already exists?
        """
        owner, repo = repo_name.split('/')

        if skip_existing:
            exists = status_collection.count({
                '_repo_name': repo_name,
                name: {
                    '$exists': True
                },
            })

            if exists:
                logger.info('Data exists for repo %s with fetcher %s', repo_name, name)
                raise DataExists()

        try:
            response = connector.get(owner=owner, repo=repo)
            response = transformer(response)

            update_mongo(response)
            status_collection.update_one(
                {'_repo_name': repo_name}, {
                    '$currentDate': {
                        f'{name}.timestamp': {
                            '$type': 'timestamp'
                        },
                    },
                    '$set': {
                        f'{name}.connector': connector.name,
                    }
                },
                upsert=True
            )

            logger.info('Fetcher %s updated %s', name, repo_name)
            return response

        except connectors.ResponseNotFoundError:
            logger.warning('Fetcher %s found no result for %s', name, repo_name)
            raise

        except CouldNotStoreData:
            logger.error(
                'Some data for repo %s could not be stored - it has not been logged as complete', repo
            )
            raise

    return fetch


class Fetcher(abc.ABC):
    """Build fetchers for each content type."""

    connector_class: typing.Type[connectors.BaseConnector]

    fetcher_key_name = {
        'readmes': '_repo_name',
        'events': 'id',
    }

    fetcher_paths: typing.Mapping

    @staticmethod
    def transformer_readmes(
        response: connectors.ConnectorSingleResponseType
    ) -> connectors.ConnectorSingleResponseType:
        try:
            content = base64.b64decode(response['content'])

        except KeyError as exc:
            raise connectors.ResponseNotFoundError from exc

        response['_content_decoded'] = content.decode('utf-8')

        return response

    def __init__(self, connector_root: typing.Optional[PathLike] = None):
        self.connector_root = None

        if connector_root is not None:
            self.connector_root = pathlib.Path(connector_root)

    def get_path(self, path: PathLike) -> str:
        try:
            return str(self.connector_root.joinpath(path))

        except AttributeError:
            return str(path)

    def make(self, fetch_type: str) -> FetcherFunc:
        path = self.fetcher_paths[fetch_type]
        connector = self.connector_class(self.get_path(path))

        collection = db.collection(
            fetch_type, indexes=[self.fetcher_key_name.get(fetch_type, 'node_id')]
        )
        fetcher_kwargs = {}

        try:
            fetcher_kwargs['transformer'] = getattr(self, f'transformer_{fetch_type}')

        except AttributeError:
            pass

        try:
            fetcher_kwargs['key_name'] = self.fetcher_key_name[fetch_type]

        except KeyError:
            pass

        return make_fetcher(fetch_type, collection, connector, **fetcher_kwargs)

    def make_all(self) -> typing.List[FetcherFunc]:
        """Get a list of prepared fetchers for each content type."""
        return [self.make(fetch_type) for fetch_type in self.fetcher_paths]


class GitHubFetcher(Fetcher):
    connector_class = connectors.GitHubConnector

    fetcher_paths = {
        'repos': '/repos/{owner}/{repo}',
        'users': '/users/{owner}',
        'readmes': '/repos/{owner}/{repo}/readme',
        'events': '/repos/{owner}/{repo}/events?per_page=1000',
        'issues': '/repos/{owner}/{repo}/issues?state=all&per_page=1000',
        'comments': '/repos/{owner}/{repo}/issues/comments?per_page=1000',
        'commits': '/repos/{owner}/{repo}/commits?per_page=1000',
    }


class FileFetcher(Fetcher):
    connector_class = connectors.FileConnector

    fetcher_paths = {
        'repos': 'REPOdata.d/{owner}+{repo}.response',
        'users': 'USERdata.d/{owner}+{repo}.response',
        'readmes': 'READMEURLs.d/{owner}+{repo}.response',
        'events': 'EVENTS.d/{owner}+{repo}.responses',
        'issues': 'ISSUES.d/{owner}+{repo}.responses',
        'comments': 'COMMENTS.d/{owner}+{repo}.responses',
        'commits': 'COMMITS.d/{owner}+{repo}.responses',
    }
