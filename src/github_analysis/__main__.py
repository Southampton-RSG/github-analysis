import itertools
import logging
import pathlib
import typing

import click

from github_analysis import fetch

logger = logging.getLogger(__name__)

PathLike = typing.Union[str, pathlib.Path]


@click.group()
def cli():
    logging.basicConfig(level=logging.INFO)


@cli.command()
@click.option('-r', '--repo', 'repos', required=False, multiple=True)  # yapf: disable
@click.option('-f', '--file', 'repo_file', required=False, type=click.File('r'))  # yapf: disable
@click.option('--file-connector-location', required=False, type=click.Path(dir_okay=True, file_okay=False))
def fetch_all(
    repos: typing.Iterable[str], repo_file: typing.Optional[click.File],
    file_connector_location: typing.Optional[PathLike]
):
    if repo_file is not None:
        # Click has already opened the file for us
        repos = itertools.chain(repos, map(str.strip, repo_file))

    fetchers = fetch.Fetcher(file_connector_location).make_all()

    for repo in repos:
        for fetcher in fetchers:
            fetcher(repo)

        logger.info('Updated records for repo: %s', repo)


if __name__ == '__main__':
    cli()
