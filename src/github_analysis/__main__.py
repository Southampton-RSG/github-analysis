import itertools
import logging
import typing

import click

from github_analysis.fetch import fetch_repos


@click.group()
def cli():
    logging.basicConfig(level=logging.INFO)


@cli.command()
@click.option('-r', '--repo', 'repos', required=False, multiple=True)  # yapf: disable
@click.option('-f', '--file', 'repo_file', required=False, type=click.File('r'))  # yapf: disable
def fetch(repos: typing.Iterable[str], repo_file: typing.Optional[click.File]):
    if repo_file is not None:
        repos = itertools.chain(repos, map(str.strip, repo_file))

    fetch_repos(repos)
