import logging
import typing

from decouple import config

from github_analysis import connectors, db

logger = logging.getLogger(__name__)

collection = db.collection('repos', indexes=['full_name'])


def fetch_repos(repos: typing.Iterable[str], force: bool = False):
    fetch = connectors.try_all([
        connectors.FileConnector('REPOdata.d/{owner}+{repo}.response'),
        connectors.RequestsConnector('https://api.github.com/repos/{owner}/{repo}',
                                     headers={'Authorization': f'Token {config("GITHUB_AUTH_TOKEN")}'})
    ])

    for repo_name in repos:
        record = collection.find_one({'full_name': repo_name})

        if force or not record:
            owner, repo = repo_name.split('/')
            try:
                response = fetch(owner=owner, repo=repo)
                collection.replace_one({'full_name': response['full_name']}, response, upsert=True)
                logger.info('Fetched data for repo: %s', repo_name)

            except connectors.ResponseNotFoundError:
                logger.warning('Repo not found: %s', repo_name)

        else:
            logger.info('Skipping up-to-date repo: %s', repo_name)
