from pprint import pprint
import typing

from decouple import config
import requests

from github_analysis import db
collection = db.collection('repos', indexes=['full_name'])


def fetch_repos(repos: typing.Iterable[str]):
    for repo in repos:
        r = requests.get(
            f'https://api.github.com/repos/{repo}',
            headers={'Authorization': f'Token {config("GITHUB_AUTH_TOKEN")}'})
        r.raise_for_status()
        content = r.json()

        result = collection.replace_one({'full_name': repo},
                                        content,
                                        upsert=True)
        pprint(result)
