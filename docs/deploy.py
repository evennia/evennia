"""
Deploy to github, from github Action. This is run after the docs have finished building. All new
documentation branches will be available in build/html/* at this point. We need to copy those
contents to the root of the repo.

This can be tested with `make release` or `make deploy` and require git push rights to
the evennia repo. Use DISABLE_GIT_PUSH for local testing - git-pushing from local can cause
clashes upstream.

We will look in source/conf.py for the `.latest_version` string and `.legacy_versions` list,
this allows us to skip deleting legacy docs (which may be ever harder to build) while correctly
symlinking to the current 'latest' documentation.

This is assumed to be executed from inside the docs/ folder.

"""

import glob
import importlib
import os
import subprocess
import sys

# set for local testing
DISABLE_GIT_PUSH = False


def deploy():
    """Perform the deploy of the built Evennia documentation to the gh-pages branch."""

    conf_file = importlib.machinery.SourceFileLoader("conf", "source/conf.py").load_module()

    latest_version = conf_file.latest_version
    legacy_versions = conf_file.legacy_versions

    if subprocess.call(["git", "status", "--untracked=no", "--porcelain"]):
        print(
            "There are uncommitted or untracked changes. Make sure "
            "to commit everything in your current branch first."
        )
        sys.exit(1)

    # get the deployment branch
    os.system("git fetch")
    os.system("git checkout gh-pages")

    os.system("pwd")
    os.system("ls")

    names_to_skip = legacy_versions + ["build"]

    for file_path in glob.glob("*"):
        # run from inside the docs/ dir
        # delete old but active doc branches

        if file_path in names_to_skip:
            # skip deleting the legacy brancehs
            continue
        else:
            # we want to delete both active branches and old symlinks
            os.system(f"rm -Rf {file_path}")
            print(f"removed file_path: {file_path}")

    # copy built branches to current dir
    os.system("ls")

    os.system("cp -Rf build/html/* .")

    os.system("ls")

    # symlink to latest and link its index to the root
    os.system(f"ln -s {latest_version} latest")
    os.system(f"ln -s {latest_version}/index.html .")

    os.system("ls")

    if not DISABLE_GIT_PUSH:
        print("committing and pushing docs ...")
        os.system("git add .")  # docs/build is in .gitignore so will be skipped
        os.system('git commit -a -m "Updated HTML docs."')
        os.system("git push origin gh-pages")
    else:
        print("Skipped git push.")

    print("Deployed to https:// evennia.github.io/evennia/")


if __name__ == "__main__":
    deploy()
