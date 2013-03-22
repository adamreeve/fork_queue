#!/usr/bin/env python
"""
Use the GitHub API to find all branches in forks of a
repository then check whether they have been
merged into a branch in a local git repository.
"""

from argparse import ArgumentParser
from collections import namedtuple
from git import Repo, BadObject
import requests


API_URL = 'https://api.github.com'


Repository = namedtuple('Repository', ('owner', 'name'))
Branch = namedtuple('Branch', ('name', 'commit'))


def main(repository, integration_branch):
    all_unmerged = set()
    local_repo = Repo('.')

    for fork in get_forks(repository):
        unmerged_branches = [
            branch for branch in get_branches(fork)
            if (not branch_is_merged(branch, local_repo, integration_branch))
               and (branch.commit not in all_unmerged)]

        all_unmerged.update(b.commit for b in unmerged_branches)

        if unmerged_branches:
            print("%s/%s:" % (fork.owner, fork.name))
            for branch in unmerged_branches:
                print("  %s" % branch.name)


def get_forks(repository):
    """
    Get repositories forked from the given repository
    """

    # todo: allow for > 100 forks using pagination
    # there's a 60 requests per hour limit anyways though
    # so not much point
    request = '%s/repos/%s/%s/forks?per_page=100' % (
            API_URL, repository.owner, repository.name)
    for repo in requests.get(request).json():
        yield Repository(repo['owner']['login'], repo['name'])


def get_branches(repository):
    """
    Get all branches in a repository
    """

    request = '%s/repos/%s/%s/branches?per_page=100' % (
            API_URL, repository.owner, repository.name)
    for branch in requests.get(request).json():
        yield Branch(branch['name'], branch['commit']['sha'])


def branch_is_merged(branch, local_repo, integration_branch):
    """
    Return whether the branch from a fork has been merged
    into the local integration branch.
    """

    try:
        branch_commit = local_repo.commit(branch.commit)
    except BadObject:
        # Commit doesn't exist in this repo, can't be merged
        return False

    # Walk down integration branch,
    # checking if commit exists anywhere
    integration_branch = local_repo.commit(integration_branch)
    for commit in integration_branch.iter_parents():
        if commit == branch_commit:
            return True
    return False


if __name__ == '__main__':
    parser = ArgumentParser(
            description="List branches in GitHub forks "
            "that have not been merged into the given local branch.")
    parser.add_argument('owner',
            help="Owner of repository on GitHub")
    parser.add_argument('repository',
            help="Name of repository on GitHub")
    parser.add_argument('integration_branch',
            help="Local git ref used to check whether commits have been merged")

    args = parser.parse_args()

    main(Repository(args.owner, args.repository), args.integration_branch)
