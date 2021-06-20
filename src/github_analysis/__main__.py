import itertools
import logging
import pathlib
import typing

import click
from decouple import config

from github_analysis import fetch
from github_analysis.connectors import ResponseNotFoundError

logger = logging.getLogger(__name__)

PathLike = typing.Union[str, pathlib.Path]


@click.group()
def cli():
    logging.basicConfig(level=config('LOG_LEVEL', default='INFO'))


def fetch_for_repos(repos: typing.Collection[str], fetchers: typing.Collection[fetch.FetcherFunc]) -> None:
    """Apply each fetcher to each repo.

    Run a fetcher on all repos before moving on to the next fetcher.
    """
    for fetcher in fetchers:
        for repo in repos:
            try:
                fetcher(repo)

            except ResponseNotFoundError:
                pass


@cli.command()
@click.option('-r', '--repo', 'repos', required=False, multiple=True)  # yapf: disable
@click.option('-f', '--file', 'repo_file', required=False, type=click.File('r'))  # yapf: disable
def fetch_all(repos: typing.Iterable[str], repo_file: typing.Optional[click.File]):
    if repo_file is not None:
        # Click has already opened the file for us
        repos = list(itertools.chain(repos, map(str.strip, repo_file)))

    fetchers = fetch.GitHubFetcher().make_all()
    fetch_for_repos(repos, fetchers)


@cli.command()
@click.option('-r', '--repo', 'repos', required=False, multiple=True)  # yapf: disable
@click.option('-f', '--file', 'repo_file', required=False, type=click.File('r'))  # yapf: disable
@click.option('--import-root', required=True, type=click.Path(dir_okay=True, file_okay=False))
def import_existing(
    repos: typing.Iterable[str], repo_file: typing.Optional[click.File], import_root: PathLike
):
    if repo_file is not None:
        # Click has already opened the file for us
        repos = list(itertools.chain(repos, map(str.strip, repo_file)))

    fetchers = fetch.FileFetcher(import_root).make_all()
    fetch_for_repos(repos, fetchers)


if __name__ == '__main__':
    cli()
