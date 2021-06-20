import subprocess

from github_analysis import __main__ as gha
from github_analysis import fetch


def test_fetch_repo_cli():
    """Check that the main fetch command completes successfully."""
    subprocess.run(['gha', 'fetch', '-r', 'jag1g13/pycgtool'], check=True)


def test_fetch_for_repos():
    """Check that the main fetch command completes successfully."""
    gha.fetch_for_repos(['jag1g13/pycgtool'], fetcher_factory=fetch.GitHubFetcher())
