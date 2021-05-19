import itertools
import logging
import typing

import click

from github_analysis import fetch


@click.group()
def cli():
    logging.basicConfig(level=logging.INFO)


@cli.command()
@click.option('-r', '--repo', 'repos', required=False, multiple=True)  # yapf: disable
@click.option('-f', '--file', 'repo_file', required=False, type=click.File('r'))  # yapf: disable
def fetch_all(repos: typing.Iterable[str], repo_file: typing.Optional[click.File]):
    if repo_file is not None:
        # Click has already opened the file for us
        repos = itertools.chain(repos, map(str.strip, repo_file))

    for repo in repos:
        for fetcher in fetch.Fetcher.make_all():
            fetcher(repo)


if __name__ == '__main__':
    cli()
