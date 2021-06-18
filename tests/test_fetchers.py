import pathlib
import typing
from unittest import mock

from github_analysis import connectors, fetch

data_dir = pathlib.Path(__file__).parent.joinpath('data')


def _test_repo(fetcher: fetch.FetcherFunc, repo_name: str) -> None:
    """Fetch data from a connector and assert correct response."""
    content = fetcher(repo_name)

    assert 'name' in content
    assert content['name'] == repo_name.split('/')[1]

    assert '_repo_name' in content
    assert content['_repo_name'] == repo_name


def test_make_repo_fetcher():
    collection = mock.Mock()
    connector = connectors.FileConnector(str(data_dir.joinpath('{owner}+{repo}.response')))

    fetcher = fetch.make_fetcher('TEST', collection, connector)

    _test_repo(fetcher, 'jag1g13/pycgtool')


def test_make_all_fetchers_github():
    fetchers = fetch.GitHubFetcher().make_all()

    assert isinstance(fetchers, typing.Iterable)

    for fetcher in fetchers:
        assert isinstance(fetcher, typing.Callable)


def test_make_all_fetchers_file():
    fetchers = fetch.FileFetcher(data_dir).make_all()

    assert isinstance(fetchers, typing.Iterable)

    for fetcher in fetchers:
        assert isinstance(fetcher, typing.Callable)


def test_fetch_repos():
    fetcher = fetch.GitHubFetcher().make('repos')

    _test_repo(fetcher, 'jag1g13/pycgtool')


def test_fetch_readmes_github():
    fetcher = fetch.GitHubFetcher().make('readmes')

    repo_name = 'jag1g13/pycgtool'
    content = fetcher(repo_name)

    assert 'name' in content
    assert content['name'] == 'README.md'

    assert '_repo_name' in content
    assert content['_repo_name'] == repo_name


def test_fetch_users_github():
    fetcher = fetch.GitHubFetcher().make('users')

    repo_name = 'jag1g13/pycgtool'
    content = fetcher(repo_name)

    assert 'login' in content
    assert content['login'] == 'jag1g13'


def test_fetch_issues_github():
    fetcher = fetch.GitHubFetcher().make('issues')

    repo_name = 'jag1g13/pycgtool'
    content: typing.Mapping = fetcher(repo_name)

    assert len(content) > 0

    first_entry = content[0]
    assert 'title' in first_entry
    assert 'number' in first_entry


def test_fetch_commits_github():
    fetcher = fetch.GitHubFetcher().make('commits')

    repo_name = 'jag1g13/pycgtool'
    content: typing.Mapping = fetcher(repo_name)

    assert len(content) > 0

    first_entry = content[0]
    assert 'author' in first_entry
    assert 'committer' in first_entry
