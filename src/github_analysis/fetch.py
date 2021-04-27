import base64
import logging

from decouple import config

from github_analysis import connectors, db

logger = logging.getLogger(__name__)


def make_fetcher(collection, connector: connectors.BaseConnector, transformer=lambda x: x):
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
    collection = db.collection('readmes')

    connector = connectors.TryEachConnector(
        connectors.FileConnector('READMEURLs.d/{owner}+{repo}.response'),
        connectors.RequestsConnector('https://api.github.com/repos/{owner}/{repo}/readme',
                                     headers={'Authorization': f'Token {config("GITHUB_AUTH_TOKEN")}'}))

    def transformer(response: connectors.JSONType) -> connectors.JSONType:
        content = base64.b64decode(response['content'])
        response['_content_decoded'] = content.decode('utf-8')

        return response

    return make_fetcher(collection, connector, transformer)


def make_fetch_repos():
    collection = db.collection('repos')

    connector = connectors.TryEachConnector(
        connectors.FileConnector('REPOdata.d/{owner}+{repo}.response'),
        connectors.RequestsConnector('https://api.github.com/repos/{owner}/{repo}',
                                     headers={'Authorization': f'Token {config("GITHUB_AUTH_TOKEN")}'}))

    return make_fetcher(collection, connector)


def make_fetch_users():
    collection = db.collection('users')

    connector = connectors.TryEachConnector(
        connectors.FileConnector('USERdata./{owner}.response'),
        connectors.RequestsConnector('https://api.github.com/users/{owner}',
                                     headers={'Authorization': f'Token {config("GITHUB_AUTH_TOKEN")}'}))

    return make_fetcher(collection, connector)
