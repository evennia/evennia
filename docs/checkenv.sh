
# check environment

# common checks 

if [ ! -d "$EVDIR" ]; then

  echo "The evennia dir is not found at $EVDIR.";
  exit 1
fi 

if [ ! -d "$EVGAMEDIR" ]; then

    echo "The gamedir is not found at $EVGAMEDIR";
    exit 1
fi 

if [ $# -ne 0 ]

  # a multi-version build
  
  then 

    if [ -n "$(git status --untracked-files=no --porcelain)" ]; then
      echo "There are uncommitted changes. Make sure to commit everything in your current branch before doing a multiversion build."
      exit 1
    fi

fi

