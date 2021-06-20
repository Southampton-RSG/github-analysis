import abc
import base64
import logging
import pathlib
import typing

from github_analysis import connectors, db

logger = logging.getLogger(__name__)

FetcherFunc = typing.Callable[[str], connectors.JSONType]
PathLike = typing.Union[str, pathlib.Path]


def make_fetcher(
    name: str,
    collection,
    connector,
    *,
    transformer: typing.Callable = lambda x, **kwargs: x,
    key_name: str = 'node_id'
) -> FetcherFunc:
    """Build a fetcher function for a specific content type.

    :param name: Name of the fetcher for logging purposes
    :param collection: MongoDB collection to store responses
    :param connector: Data connector with which to fetch the data
    :param transformer: Function applied to the response before saving
    :param key_name: MonogDB field name to use for update query
    """
    def update_mongo(response: connectors.JSONType) -> None:
        """Update a record or multiple records for a response in the MongoDB collection."""
        if isinstance(response, list):
            for r in response:
                update_mongo(r)

        else:
            try:
                collection.replace_one({key_name: response[key_name]}, response, upsert=True)

            except KeyError:
                logger.warning('Response did not contain expected key: %s', key_name)

    def fetch(repo_name: str) -> connectors.JSONType:
        """Function to fetch data for a specific repo.

        The content type and connectors used are set by closure.

        :param repo_name: Name of repository to fetch in 'username/reponame' format
        """
        owner, repo = repo_name.split('/')
        try:
            response = connector.get(owner=owner, repo=repo)
            response = transformer(response, owner=owner, repo=repo)

            update_mongo(response)

            logger.info('Fetcher %s updated %s', name, repo_name)
            return response

        except connectors.ResponseNotFoundError:
            logger.warning('Fetcher %s found no result for %s', name, repo_name)
            raise

    return fetch


class Fetcher(abc.ABC):
    """Build fetchers for each content type."""

    connector_class: typing.Type[connectors.BaseConnector]

    fetcher_key_name = {
        'readmes': '_repo_name',
    }

    fetcher_paths: typing.Mapping

    @staticmethod
    def transformer_readmes(response: connectors.JSONType, **kwargs) -> connectors.JSONType:
        content = base64.b64decode(response['content'])
        response['_content_decoded'] = content.decode('utf-8')
        response['_repo_name'] = f'{kwargs["owner"]}/{kwargs["repo"]}'

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

        collection = db.collection(fetch_type)
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
        'issues': '/repos/{owner}/{repo}/issues?state=all&per_page=1000',
        'commits': '/repos/{owner}/{repo}/commits?per_page=1000',
    }


class FileFetcher(Fetcher):
    connector_class = connectors.FileConnector

    fetcher_paths = {
        'repos': 'REPOdata.d/{owner}+{repo}.response',
        'users': 'USERdata.d/{owner}+{repo}.response',
        'readmes': 'READMEURLs.d/{owner}+{repo}.response',
        'issues': 'ISSUES.d/{owner}+{repo}.responses',
        'commits': 'COMMITS.d/{owner}+{repo}.responses',
    }
