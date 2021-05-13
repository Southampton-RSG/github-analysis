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
@click.option('--force', is_flag=True, default=False)
def fetch_all(repos: typing.Iterable[str], repo_file: typing.Optional[click.File], force: bool = False):
    if repo_file is not None:
        repos = itertools.chain(repos, map(str.strip, repo_file))

    for repo in repos:
        for fetcher in fetch.Fetcher.all():
            fetcher(repo, force=force)
