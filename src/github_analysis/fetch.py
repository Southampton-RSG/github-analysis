import base64
import logging
import pathlib
import typing

from github_analysis import connectors, db

logger = logging.getLogger(__name__)

FetcherFunc = typing.Callable[[str], connectors.JSONType]
PathLike = typing.Union[str, pathlib.Path]


def make_fetcher(
    collection,
    connector,
    *,
    transformer: typing.Callable = lambda x, **kwargs: x,
    key_name: str = 'node_id'
) -> FetcherFunc:
    """Build a fetcher function for a specific content type.

    :param collection: MongoDB collection to store responses
    :param connector: Data connector with which to fetch the data
    :param transformer: Function applied to the response before saving
    :param key_name: MonogDB field name to use for update query
    """
    def update_mongo(response: connectors.JSONType):
        """Update a record or multiple records for a response in the MongoDB collection."""
        if isinstance(response, list):
            for item in response:
                collection.replace_one({key_name: item[key_name]}, item, upsert=True)

        else:
            collection.replace_one({key_name: response[key_name]}, response, upsert=True)

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

            return response

        except connectors.ResponseNotFoundError:
            logger.warning('Repo not found: %s', repo_name)
            raise

    return fetch


class Fetcher:
    """Build fetchers for each content type."""
    def __init__(self, file_connector_location: typing.Optional[PathLike] = None):
        if file_connector_location is None:
            file_connector_location = pathlib.Path.cwd()

        self.file_connector_location = pathlib.Path(file_connector_location)

    def make_all(self) -> typing.List[FetcherFunc]:
        """Get a list of prepared fetchers for each content type.

        Any attribute of this class beginning with 'make_fetch' will be used to build a fetcher.
        """
        return [getattr(self, name)() for name in type(self).__dict__ if name.startswith('make_fetch')]

    def make_fetch_readmes(self) -> FetcherFunc:
        def transformer(response: connectors.JSONType, **kwargs) -> connectors.JSONType:
            content = base64.b64decode(response['content'])
            response['_content_decoded'] = content.decode('utf-8')
            response['_repo_name'] = f'{kwargs["owner"]}/{kwargs["repo"]}'

            return response

        collection = db.collection('readmes')

        file_connector_path = str(self.file_connector_location.joinpath('READMEURLs.d/{owner}+{repo}.response'))
        connector = connectors.TryEachConnector(
            connectors.FileConnector(file_connector_path),
            connectors.GitHubConnector('/repos/{owner}/{repo}/readme')
        )

        return make_fetcher(collection, connector, transformer=transformer, key_name='_repo_name')

    def make_fetch_repos(self) -> FetcherFunc:
        collection = db.collection('repos')

        file_connector_path = str(self.file_connector_location.joinpath('REPOdata.d/{owner}+{repo}.response'))
        connector = connectors.TryEachConnector(
            connectors.FileConnector(file_connector_path),
            connectors.GitHubConnector('/repos/{owner}/{repo}')
        )

        return make_fetcher(collection, connector)

    def make_fetch_users(self) -> FetcherFunc:
        collection = db.collection('users')

        file_connector_path = str(self.file_connector_location.joinpath('USERdata.d/{owner}+{repo}.response'))
        connector = connectors.TryEachConnector(
            connectors.FileConnector(file_connector_path),
            connectors.GitHubConnector('/users/{owner}')
        )

        return make_fetcher(collection, connector)

    def make_fetch_issues(self) -> FetcherFunc:
        collection = db.collection('issues')

        file_connector_path = str(self.file_connector_location.joinpath('ISSUES.d/{owner}+{repo}.responses'))
        connector = connectors.TryEachConnector(
            connectors.FileConnector(file_connector_path),
            connectors.GitHubConnector('/repos/{owner}/{repo}/issues?state=all&per_page=100')
        )

        return make_fetcher(collection, connector)

    def make_fetch_commits(self) -> FetcherFunc:
        collection = db.collection('commits')

        file_connector_path = str(self.file_connector_location.joinpath('COMMITS.d/{owner}+{repo}.responses'))
        connector = connectors.TryEachConnector(
            connectors.FileConnector(file_connector_path),
            connectors.GitHubConnector('/repos/{owner}/{repo}/commits?per_page=100')
        )

        return make_fetcher(collection, connector)
