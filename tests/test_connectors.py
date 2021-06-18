import pathlib

from decouple import config

from github_analysis import connectors

data_dir = pathlib.Path(__file__).parent.joinpath('data')


def _test_repo(connector: connectors.BaseConnector, owner: str, repo: str) -> None:
    """Fetch data from a connector and assert correct response."""
    content = connector.get(owner=owner, repo=repo)

    assert 'name' in content
    assert content['name'] == repo

    assert '_repo_name' in content
    assert content['_repo_name'] == f'{owner}/{repo}'


def test_file_connector():
    connector = connectors.FileConnector('tests/data/{owner}+{repo}.response')

    _test_repo(connector, 'jag1g13', 'pycgtool')


def test_requests_connector():
    connector = connectors.RequestsConnector(
        'https://api.github.com/repos/{owner}/{repo}',
        headers={'Authorization': f'Token {config("GITHUB_AUTH_TOKEN")}'}
    )

    _test_repo(connector, 'jag1g13', 'pycgtool')


def test_all_connectors():
    connector = connectors.TryEachConnector(
        connectors.FileConnector('tests/data/{owner}+{repo}.response'),
        connectors.RequestsConnector(
            'https://api.github.com/repos/{owner}/{repo}',
            headers={'Authorization': f'Token {config("GITHUB_AUTH_TOKEN")}'}
        )
    )

    # Uses FileConnector
    _test_repo(connector, 'jag1g13', 'pycgtool')

    # Uses RequestsConnector
    _test_repo(connector, 'pedasi', 'PEDASI')


def test_join_curl_responses():
    with open(data_dir.joinpath('COMMITS.d', 'jag1g13+pycgtool.responses')) as fp:
        # Test that it doesn't throw a JSONDecodeError
        response = connectors.join_curl_responses(fp.read())

    assert isinstance(response, list)
