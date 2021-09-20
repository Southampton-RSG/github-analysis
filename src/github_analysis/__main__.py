import itertools
import logging
import pathlib
import typing

import click
from decouple import config

from github_analysis import db, fetch
from github_analysis.connectors import ResponseNotFoundError

logger = logging.getLogger(__name__)

PathLike = typing.Union[str, pathlib.Path]


@click.group()
def cli():
    logging.basicConfig(level=config('LOG_LEVEL', default='INFO'))


def fetch_for_repos(
    repos: typing.Collection[str],
    fetcher_factory: fetch.Fetcher,
    only: typing.Optional[str] = None,
    skip_existing: bool = False
) -> None:
    """Apply each fetcher to each repo.

    Run a fetcher on all repos before moving on to the next fetcher.

    :param repos: List of repositories to fetch
    :param fetcher_factory: Factory for fetchers to run
    :param only: Run only this fetcher
    :param skip_existing: Skip fetches where data already exists
    """
    if only:
        fetchers = [fetcher_factory.make(only)]

    else:
        fetchers = fetcher_factory.make_all()

    for fetcher in fetchers:
        for repo in repos:
            try:
                fetcher(repo, skip_existing)

            except (fetch.CouldNotStoreData, fetch.DataExists, ResponseNotFoundError):
                pass


def label_repo_set(repo: str, set_name: str):
    """Label a repo as belonging to the set."""
    collection = db.collection('status', indexes=['sets'])

    # Add set name to array of sets in status collection
    collection.update_one({
        '_repo_name': repo,
    }, {'$addToSet': {
        'sets': set_name,
    }}, upsert=True)

    # Add set name to array of sets in all other collections
    for collection_name in {
        *fetch.GitHubFetcher.fetcher_paths.keys(),
        *fetch.FileFetcher.fetcher_paths.keys(),
    }:
        logger.info('Labelling collection: %s', collection_name)
        collection = db.collection(collection_name, indexes=['sets'])

        collection.update_many({
            '_repo_name': repo,
        }, {'$addToSet': {
            'sets': set_name,
        }})


def clean_repo_list(repos: typing.Iterable[str], repo_file: typing.Optional[click.File]) -> typing.List[str]:
    """Concatentate repo list with repos from file and tag as belonging to set."""
    if repo_file is not None:
        # Click has already opened the file for us
        repos = itertools.chain(repos, map(str.strip, repo_file))

    return [repo for repo in repos if not repo.startswith('#')]


@cli.command()
@click.option('-r', '--repo', 'repos', required=False, multiple=True)  # yapf: disable
@click.option('-f', '--file', 'repo_file', required=False, type=click.File('r'))  # yapf: disable
@click.option('--set-name', required=True)  # yapf: disable
def name_set(
    repos: typing.Iterable[str],
    repo_file: typing.Optional[click.File],
    set_name: str,
):
    """Tag repos as belonging to a named set."""
    repos = clean_repo_list(repos, repo_file)

    for repo in repos:
        label_repo_set(repo, set_name)


@cli.command(name='fetch')
@click.option('-r', '--repo', 'repos', required=False, multiple=True)  # yapf: disable
@click.option('-f', '--file', 'repo_file', required=False, type=click.File('r'))  # yapf: disable
@click.option('--only', required=False, type=click.Choice(fetch.GitHubFetcher.fetcher_paths.keys()))
@click.option('--skip-existing', default=False, is_flag=True)
def fetch_(
    repos: typing.Iterable[str],
    repo_file: typing.Optional[click.File],
    only: typing.Optional[str] = None,
    skip_existing: bool = False
):
    repos = clean_repo_list(repos, repo_file)

    fetcher_factory = fetch.GitHubFetcher()
    fetch_for_repos(repos, fetcher_factory, only, skip_existing=skip_existing)


@cli.command()
@click.option('-r', '--repo', 'repos', required=False, multiple=True)  # yapf: disable
@click.option('-f', '--file', 'repo_file', required=False, type=click.File('r'))  # yapf: disable
@click.option('--import-root', required=True, type=click.Path(dir_okay=True, file_okay=False))
@click.option('--only', required=False, type=click.Choice(fetch.FileFetcher.fetcher_paths.keys()))
@click.option('--skip-existing', default=False, is_flag=True)
def import_existing(
    repos: typing.Iterable[str],
    repo_file: typing.Optional[click.File],
    import_root: PathLike,
    only: typing.Optional[str] = None,
    skip_existing: bool = False
):
    repos = clean_repo_list(repos, repo_file)

    fetcher_factory = fetch.FileFetcher(import_root)
    fetch_for_repos(repos, fetcher_factory, only, skip_existing=skip_existing)


if __name__ == '__main__':
    cli()
