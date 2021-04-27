import base64
import logging
import typing

from github_analysis import connectors, db

logger = logging.getLogger(__name__)


def make_fetcher(collection_name: str,
                 file_connector_path: str,
                 github_connector_path: str,
                 transformer: typing.Callable = lambda x: x):
    collection = db.collection(collection_name)
    connector = connectors.TryEachConnector(connectors.FileConnector(file_connector_path),
                                            connectors.GitHubConnector(github_connector_path))

    def fetch(repo_name: str, force: bool = False) -> None:
        record = collection.find_one({'_repo_name': repo_name})

        if force or not record:
            owner, repo = repo_name.split('/')
            try:
                response = connector.get(owner=owner, repo=repo)
                response = transformer(response)

                collection.replace_one({'_repo_name': response['_repo_name']}, response, upsert=True)
                logger.info('Fetched data for repo: %s', repo_name)

            except connectors.ResponseNotFoundError:
                logger.warning('Repo not found: %s', repo_name)

        else:
            logger.info('Skipping up-to-date repo: %s', repo_name)

    return fetch


def make_fetch_readmes():
    def transformer(response: connectors.JSONType) -> connectors.JSONType:
        content = base64.b64decode(response['content'])
        response['_content_decoded'] = content.decode('utf-8')

        return response

    return make_fetcher('readmes', 'READMEURLs.d/{owner}+{repo}.response', '/repos/{owner}/{repo}/readme',
                        transformer)


def make_fetch_repos():
    return make_fetcher('repos', 'REPOdata.d/{owner}+{repo}.response', '/repos/{owner}/{repo}')


def make_fetch_users():
    return make_fetcher('users', 'USERdata.d/{owner}.response', '/users/{owner}')
