# Release helper 

VERSION=$(cat evennia/VERSION.txt)

echo "This will release Evennia $VERSION (based on evennia/VERSION.txt)."
echo "Before continuing:"
echo " 1. Make sure you have Evennia upload credentials."
echo " 2. Determine if CHANGELOG.md should be updated and rebuilt."
echo " 3. Make sure VERSION.txt and pyproject.toml both show version $VERSION."
echo " 4. Make sure all changes are committed (all un-staged files will be wiped)."
echo " 5. Make sure all unit tests pass."

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

echo "Uploading PyPi package (requires credentials) ..."

python -m twine upload dist/*

# tag the latest git commit
echo "Creating and pushing release tag tag v$VERSION ..."
git tag -a v$VERSION -m "Evennia release v$VERSION"
git push --tags

echo "... Release complete." 
echo ""
echo "Post-release actions:" 
echo " 1. Make sure to push all commits."
echo " 2. Update github discussions to report on release."
echo " 2. Make post in discord #announcements channel pointing to discussion post."
echo " 3. Any other announcements as needed."
