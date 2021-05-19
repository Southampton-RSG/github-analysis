import base64
import logging
import typing

from github_analysis import connectors, db

logger = logging.getLogger(__name__)

FetcherFunc = typing.Callable[[str], connectors.JSONType]


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

            logger.info('Fetched data for repo: %s', repo_name)
            return response

        except connectors.ResponseNotFoundError:
            logger.warning('Repo not found: %s', repo_name)
            raise

    return fetch


class Fetcher:
    """Static class to hold fetchers for each content type."""
    @classmethod
    def make_all(cls) -> typing.List[FetcherFunc]:
        """Get a list of prepared fetchers for each content type."""
        return [getattr(cls, name)() for name in cls.__dict__ if name.startswith('make_fetch')]

    @staticmethod
    def make_fetch_readmes() -> FetcherFunc:
        def transformer(response: connectors.JSONType, **kwargs) -> connectors.JSONType:
            content = base64.b64decode(response['content'])
            response['_content_decoded'] = content.decode('utf-8')
            response['_repo_name'] = f'{kwargs["owner"]}/{kwargs["repo"]}'

            return response

        collection = db.collection('readmes')

        connector = connectors.TryEachConnector(
            connectors.FileConnector('READMEURLs.d/{owner}+{repo}.response'),
            connectors.GitHubConnector('/repos/{owner}/{repo}/readme')
        )

        return make_fetcher(collection, connector, transformer=transformer, key_name='_repo_name')

    @staticmethod
    def make_fetch_repos() -> FetcherFunc:
        collection = db.collection('repos')

        connector = connectors.TryEachConnector(
            connectors.FileConnector('REPOdata.d/{owner}+{repo}.response'),
            connectors.GitHubConnector('/repos/{owner}/{repo}')
        )

        return make_fetcher(collection, connector)

    @staticmethod
    def make_fetch_users() -> FetcherFunc:
        collection = db.collection('users')

        connector = connectors.TryEachConnector(
            connectors.FileConnector('USERdata.d/{owner}.response'),
            connectors.GitHubConnector('/users/{owner}')
        )

        return make_fetcher(collection, connector)

    @staticmethod
    def make_fetch_issues() -> FetcherFunc:
        collection = db.collection('issues')

        connector = connectors.TryEachConnector(
            connectors.FileConnector('ISSUES.d/{owner}+{repo}.responses'),
            connectors.GitHubConnector('/repos/{owner}/{repo}/issues?state=all&per_page=100')
        )

        return make_fetcher(collection, connector)
