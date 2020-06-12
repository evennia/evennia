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

# get the deployment branch
git checkout gh-pages

mv build ..
# the docs/ folder is named the same in both branches so we need to step out of 
# it to not confuse what's what.
cd ..
rm -Rf docs/*
cp -Rf build/html/versions/* docs/
ln -s docs/v1.0-dev latest 
git add docs/*
git commit -a -m "Updated HTML docs"

mv build docs/

echo "Skipping deployment"
# git push origin gh-pages

# get back to previous branch 
git checkout -

echo "Deployed to https://evennia.github.io/evennia-docs."
