
# check environment


# if [ -n "$(git status --untracked-files=no --porcelain)" ]; then
#   echo "There are uncommitted changes. Make sure to commit everything in your current branch first."
#   exit 1
# fi

if [ ! -d "$EVDIR" ]; then

  echo "The evennia dir is not found at $EVDIR.";
  exit 1
else
  echo "Evennia dir correctly set to $EVDIR.";
fi 

if [ ! -d "$EVGAMEDIR" ]; then

    echo "The gamedir is not found at $EVGAMEDIR";
    exit 1
else
  echo "Evennia game dir correctly set to $EVGAMEDIR.";
fi 
