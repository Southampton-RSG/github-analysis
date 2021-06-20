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


def fetch_for_repos(
    repos: typing.Collection[str], fetcher_factory: fetch.Fetcher, only: typing.Optional[str] = None
) -> None:
    """Apply each fetcher to each repo.

    Run a fetcher on all repos before moving on to the next fetcher.
    """
    if only:
        fetchers = [fetcher_factory.make(only)]

    else:
        fetchers = fetcher_factory.make_all()

    for fetcher in fetchers:
        for repo in repos:
            try:
                fetcher(repo)

            except ResponseNotFoundError:
                pass


@cli.command(name='fetch')
@click.option('-r', '--repo', 'repos', required=False, multiple=True)  # yapf: disable
@click.option('-f', '--file', 'repo_file', required=False, type=click.File('r'))  # yapf: disable
@click.option('--only', required=False, type=click.Choice(fetch.GitHubFetcher.fetcher_paths.keys()))
def fetch_(
    repos: typing.Iterable[str], repo_file: typing.Optional[click.File], only: typing.Optional[str] = None
):
    if repo_file is not None:
        # Click has already opened the file for us
        repos = list(itertools.chain(repos, map(str.strip, repo_file)))

    fetcher_factory = fetch.GitHubFetcher()
    fetch_for_repos(list(repos), fetcher_factory, only)


@cli.command()
@click.option('-r', '--repo', 'repos', required=False, multiple=True)  # yapf: disable
@click.option('-f', '--file', 'repo_file', required=False, type=click.File('r'))  # yapf: disable
@click.option('--import-root', required=True, type=click.Path(dir_okay=True, file_okay=False))
@click.option('--only', required=False, type=click.Choice(fetch.FileFetcher.fetcher_paths.keys()))
def import_existing(
    repos: typing.Iterable[str],
    repo_file: typing.Optional[click.File],
    import_root: PathLike,
    only: typing.Optional[str] = None
):
    if repo_file is not None:
        # Click has already opened the file for us
        repos = list(itertools.chain(repos, map(str.strip, repo_file)))

    fetcher_factory = fetch.FileFetcher(import_root)
    fetch_for_repos(list(repos), fetcher_factory, only)


if __name__ == '__main__':
    cli()
