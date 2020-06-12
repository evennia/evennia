# 
# deploy to github 
# 
# This copies the recently built files from build/html into the github-gh branch. Note that 
# it's important that build/ must not be committed to git!
# 

if [ -n "$(git status --untracked-files=no --porcelain)" ]; then
  echo "There are uncommitted changes. Make sure to commit everything in your current branch first."
  exit 1
fi

git checkout gh-pages

mv build ..
cd ..
rm -Rf docs/*
cp -Rf build/html/* docs/
git add docs/*
rm -Rf build

git commit -a -m "Updated HTML docs"
echo "Skipping deployment"
# git push origin gh-pages

# get back to previous branch

 git checkout -

echo "Deployed to https://evennia.github.io/evennia-docs."
