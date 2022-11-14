"""
Deploy to github, from github Action. This is run after the docs have finished building. All new
documentation branches will be available in build/html/* at this point. We need to copy those
contents to the root of the repo.

This is assumed to be executed from inside the docs/ folder.
"""

import glob
import os
import subprocess
import sys

# branches that should not be rebuilt anymore (all others are considered active)
legacy_branches = ["0.9.5"]
# the branch pointed to by the 'latest' symlink
latest_branch = "0.9.5"


def deploy():

    if subprocess.call(["git", "status", "--untracked=no", "--porcelain"]):
        print(
            "There are uncommitted or untracked changes. Make sure "
            "to commit everything in your current branch first."
        )
        sys.exit(1)

    # get the deployment branch
    os.system("git fetch")
    os.system("git checkout gh-pages")

    for file_path in glob.glob("*"):
        # run from inside the docs/ dir
        # delete old but active doc branches

        _, *filename = file_path.rsplit("/", 1)

        if filename and filename[0] in legacy_branches:
            # skip deleting the legacy brancehs
            continue
        else:
            # we want to delete both active branches and old symlinks
            print("remove file_path:", file_path)
            os.system(f"rm -Rf {file_path}")

    # copy built branches to current dir
    os.system("cp -Rf build/html/* .")
    # symlink to latest and link its index to the root
    os.system(f"ln -s {latest_branch} latest")
    os.system(f"ln -s {latest_branch}/index.html .")

    # docs/build is in .gitignore so will be skipped
    os.system("git add .")
    os.system('git commit -a -m "Updated HTML docs."')
    os.system("git push origin gh-pages")

    # get back to previous branch
    os.system("git checkout .")

    print("Deployed to https:// evennia.github.io/evennia/")


if __name__ == "__main__":
    deploy()
