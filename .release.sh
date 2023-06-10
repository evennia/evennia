# Release helper

VERSION=$(cat evennia/VERSION.txt)

echo "This will release Evennia $VERSION (based on evennia/VERSION.txt)."
echo "Before continuing:"
echo " 1. Make sure you have Evennia upload credentials for Github (tagging) and PyPi (main package)."
echo " 2. On main branch, update CHANGELOG.md."
echo " 3. Make sure pyproject.toml is set to the same major.minor.patch version as evennia/VERSION.txt ($VERSION)."
echo " 4. If major release:"
echo "    a. Update docs/conf.py, set release to new major release, e.g. '3.x'. Add the previous latest major.minor.patch "
echo "       release (LATEST_RELEASE) to the list of 'legacy_versions' to show as an old doc version."
echo "    b. Make sure all changes are committed."
echo "    c. Check out a new branch vLATEST_RELEASE and reset it to the commit of the latest major.minor.patch release."
echo "    d. Push the vLATEST_RELEASE BRANCH to github."
echo "    e. On the vLATEST_RELEASE branch, temporarily set 'current_is_legacy=True' in source/conf.py, then (re)build "
echo "       the docs for this release with 'make local' and old-version warning headers. Throw away git changes after."
echo "    f. Rename the created build/html folder to LATEST_RELEASE. Manually copy it to the gh-pages branch's build/ folder."
echo "    g. Add the folder, commit and push to the gh-pages branch. Then checkout main branch again."
echo " 5. Run 'make local' in docs/ to update dynamic docs (like Changelog.md) and autodocstrings (may have to run twice)."
echo " 6. Make sure all changes are committed, e.g. as 'Evennia $VERSION major/minor/patch release' (un-staged files will be wiped)."
echo " 7. Make sure all unit tests pass!"

read -p "Continue? [Y/n]> " yn

case $yn in
    [nN] ) echo "Aborting.";
        exit;;
    * ) echo "Starting release ...";;
esac

# clean and build the pypi distribution
echo "Preparing and Building PyPi package ..."
rm -Rf dist/
git clean -xdf
pip install --upgrade pip
pip install build twine
python -m build --sdist --wheel --outdir dist/ .

echo "Uploading PyPi package (requires PyPi credentials) ..."

python -m twine upload dist/*

# tag the latest git commit
echo "Creating and pushing release tag tag v$VERSION (requires GitHub credentials)..."
git tag -a v$VERSION -m "Evennia release v$VERSION"
git push --tags

echo "... Release complete."
echo ""
echo "Post-release actions:"
echo " 1. Make sure to push all commits."
echo " 2. Update github discussions to report on release."
echo " 2. Make post in discord #announcements channel pointing to discussion post."
echo " 3. Any other announcements as needed."
