import click

from github_analysis.fetch import fetch_repos


@click.group()
def cli():
    pass


@cli.command()
@click.argument('repo')
def fetch(repo: str):
    fetch_repos([repo])
