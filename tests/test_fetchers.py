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

    fetcher = fetch.make_fetcher(collection, connector)

    _test_repo(fetcher, 'jag1g13/pycgtool')


def test_make_all_fetchers():
    fetchers = fetch.Fetcher().make_all()

    assert isinstance(fetchers, typing.Iterable)

    for fetcher in fetchers:
        assert isinstance(fetcher, typing.Callable)


def test_fetch_repos():
    fetcher = fetch.Fetcher().make_fetch_repos()

    _test_repo(fetcher, 'jag1g13/pycgtool')


def test_fetch_readmes():
    fetcher = fetch.Fetcher().make_fetch_readmes()

    repo_name = 'jag1g13/pycgtool'
    content = fetcher(repo_name)

    assert 'name' in content
    assert content['name'] == 'README.md'

    assert '_repo_name' in content
    assert content['_repo_name'] == repo_name


def test_fetch_users():
    fetcher = fetch.Fetcher().make_fetch_users()

    repo_name = 'jag1g13/pycgtool'
    content = fetcher(repo_name)

    assert 'login' in content
    assert content['login'] == 'jag1g13'


def test_fetch_issues():
    fetcher = fetch.Fetcher().make_fetch_issues()

    repo_name = 'jag1g13/pycgtool'
    content: typing.Mapping = fetcher(repo_name)

    assert len(content) > 0

    first_entry = content[0]
    assert 'title' in first_entry
    assert 'number' in first_entry


def test_fetch_commits():
    fetcher = fetch.Fetcher().make_fetch_commits()

    repo_name = 'jag1g13/pycgtool'
    content: typing.Mapping = fetcher(repo_name)

    assert len(content) > 0

    first_entry = content[0]
    assert 'author' in first_entry
    assert 'committer' in first_entry
