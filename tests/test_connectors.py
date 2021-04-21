import pathlib

from decouple import config

from github_analysis import connectors

filepath = pathlib.Path('REPOdata.d/jag1g13+pycgtool.response')


def test_file_connector():
    connector = connectors.FileConnector('tests/data/{owner}+{repo}.response')
    content = connector.get(owner='jag1g13', repo='pycgtool')

    assert 'name' in content
    assert content['name'] == 'pycgtool'


def test_requests_connector():
    connector = connectors.RequestsConnector(
        'https://api.github.com/repos/{owner}/{repo}',
        headers={'Authorization': f'Token {config("GITHUB_AUTH_TOKEN")}'})
    content = connector.get(owner='jag1g13', repo='pycgtool')

    assert 'name' in content
    assert content['name'] == 'pycgtool'


def test_all_connectors():
    fetch = connectors.try_all([
        connectors.FileConnector('tests/data/{owner}+{repo}.response'),
        connectors.RequestsConnector('https://api.github.com/repos/{owner}/{repo}',
                                     headers={'Authorization': f'Token {config("GITHUB_AUTH_TOKEN")}'})
    ])

    response = fetch(owner='jag1g13', repo='pycgtool')
    print(response['name'])

    assert 'name' in response
    assert response['name'] == 'pycgtool'

    response = fetch(owner='pedasi', repo='pedasi')
    print(response['name'])
