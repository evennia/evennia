# Release helper 

VERSION=$(cat evennia/VERSION.txt)

echo "This will release Evennia $VERSION (based on evennia/VERSION.txt)."
echo "Before continuing:"
echo " 1. Make sure you have Evennia upload credentials for Github (tagging) and PyPi (main package)."
echo " 2. Update CHANGELOG.md."
echo " 3. Make sure pyproject.toml is set to the same version as evennia/VERSION.txt ($VERSION)."
echo " 4. Run 'make local' in docs/ to update dynamic docs (like Changelog.md) and autodocstrings (may have to run twice)."
echo " 5. Make sure all changes are committed, e.g. as 'Evennia $VERSION major/minor/patch release' (un-staged files will be wiped)."
echo " 6. Make sure all unit tests pass!"

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
