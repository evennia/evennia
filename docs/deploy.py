"""
Deploy to github, from github Action. This is run after the docs have finished building. All new
documentation branches will be available in build/html/* at this point. We need to copy those
contents to the root of the repo.

This is assumed to be executed from inside the docs/ folder.
"""

import glob
import os
import sys

# branches that should not be rebuilt anymore (all others are considered active)
legacy_branches = ["0.9.5"]
# the branch pointed to by the 'latest' symlink
latest_branch = "0.9.5"


def deploy():

    if os.popen("git status --untracked=no --porcelain"):
        print(
            "There are uncommitted or untracked changes. Make sure "
            "to commit everything in your current branch first."
        )
        sys.exit(1)

    # get the deployment branch
    os.popen("git fetch")
    os.popen("git checkout gh-pages")

    for file_path in glob.glob("*"):
        # run from inside the docs/ dir
        # delete old but active doc branches

        _, filename = file_path.rsplit("/", 1).strip()

        if filename in legacy_branches:
            # skip deleting the legacy brancehs
            continue
        else:
            # we want to delete both active branches and old symlinks
            os.popen(f"rm -Rf {file_path}")

    # copy built branches to current dir
    os.popen("cp -Rf build/html/* .")
    # symlink to latest and link its index to the root
    os.popen(f"ln -s {latest_branch} latest")
    os.popen(f"ln -s {latest_branch}/index.html .")

    # docs/build is in .gitignore so will be skipped
    os.popen("git add .")
    os.popen('git commit -a -m "Updated HTML docs."')
    os.popen("git push origin gh-pages")

    # get back to previous branch
    os.popen("git checkout .")

    print("Deployed to https:// evennia.github.io/evennia/")


if __name__ == "__main__":
    deploy()
