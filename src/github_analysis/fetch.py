import base64
import logging
import typing

from github_analysis import connectors, db

logger = logging.getLogger(__name__)

FetcherFunc = typing.Callable[[str, bool], None]


def make_fetcher(collection_name: str,
                 file_connector_path: str,
                 github_connector_path: str,
                 transformer: typing.Callable = lambda x: x) -> FetcherFunc:
    """Build a fetcher function for a specific content type.

    :param collection_name: Name of MongoDB collection to store responses
    :param file_connector_path: Template path to pre-scraped response for FileCollector
    :param github_connector_path: Template URL for GitHub API endpoint to query
    :param transformer: Function applied to the response before saving
    """
    collection = db.collection(collection_name)
    connector = connectors.TryEachConnector(connectors.FileConnector(file_connector_path),
                                            connectors.GitHubConnector(github_connector_path))

    def fetch(repo_name: str, force: bool = False) -> None:
        """Function to fetch data for a specific repo.

        The content type and connectors used are set by closure.

        :param repo_name: Name of repository to fetch in 'username/reponame' format
        :param force: Fetch data even if it already exists in MongoDB table?
        """
        record = collection.find_one({'_repo_name': repo_name})

        if force or not record:
            owner, repo = repo_name.split('/')
            try:
                response = connector.get(owner=owner, repo=repo)
                response = transformer(response)

                collection.replace_one({'_repo_name': response['_repo_name']}, response, upsert=True)
                logger.info('Fetched %s for repo: %s', collection_name, repo_name)

            except connectors.ResponseNotFoundError:
                logger.warning('Repo not found: %s', repo_name)

        else:
            logger.info('Skipping up-to-date repo: %s', repo_name)

    return fetch


class Fetcher:
    """Static class to hold fetchers for each content type."""
    @classmethod
    def all(cls) -> typing.List[FetcherFunc]:
        """Get a list of prepared fetchers for each content type."""
        return [getattr(cls, name)() for name in cls.__dict__ if name.startswith('make_fetch')]

    @staticmethod
    def make_fetch_readmes() -> FetcherFunc:
        def transformer(response: connectors.JSONType) -> connectors.JSONType:
            content = base64.b64decode(response['content'])
            response['_content_decoded'] = content.decode('utf-8')

            return response

        return make_fetcher('readmes', 'READMEURLs.d/{owner}+{repo}.response', '/repos/{owner}/{repo}/readme',
                            transformer)

    @staticmethod
    def make_fetch_repos() -> FetcherFunc:
        return make_fetcher('repos', 'REPOdata.d/{owner}+{repo}.response', '/repos/{owner}/{repo}')

    @staticmethod
    def make_fetch_users() -> FetcherFunc:
        return make_fetcher('users', 'USERdata.d/{owner}.response', '/users/{owner}')
