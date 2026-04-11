# Release helper

VERSION=$(cat evennia/VERSION.txt)

echo "This will release Evennia $VERSION (based on evennia/VERSION.txt)."
echo "Before continuing:"
echo " 1. Make sure you have Evennia upload credentials for Github (tagging) and PyPi (main package)."
echo " 2. On main branch, update CHANGELOG.md."
echo " 3. Make sure pyproject.toml is set to the same major.minor.patch version as evennia/VERSION.txt ($VERSION)."
echo " 4. If major release:"
echo "    a. Update docs/sources/conf.py, Add '[MAJOR_VERSION].x' to 'legacy_versions' and 'v$VERSION' to 'legacy_branches'."
echo "    b. Update 'SECURITY.md' with latest new version."
echo "    b. Run 'make local' to build docs with Changelog.md updated."
echo "    c. Commit all changes, e.g. as 'Evennia $VERSION major/minor/patch release'."
echo "    d. Check out a new branch v$VERSION."
echo "    e. Push the v$VERSION branch to github."
echo "    f. On the v$VERSION branch, temporarily set 'current_is_legacy=True' in source/conf.py, then (re)build "
echo "       the docs for this release with 'make local' and old-version warning headers. Throw away git changes after."
echo "    g. Rename the created build/html folder to '[MAJOR_VERSION].x'. Manually copy it to the gh-pages branch's build/ folder."
echo "    h. Add the folder, commit and push to the gh-pages branch. Then checkout main branch again."
echo " 5. Run 'make local' in docs/ to update dynamic docs (like Changelog.md) and autodocstrings (may have to run twice)."
echo " 6. Make sure all changes are committed (if not already), e.g. as 'Evennia $VERSION major/minor/patch release' (un-staged files will be wiped)."
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
