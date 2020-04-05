# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = source
BUILDDIR      = build
AUTODOCDIR = $(SOURCEDIR)/api

EVDIR ?= $(realpath ../evennia)
EVGAMEDIR ?= $(realpath ../../gamedir)


# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
	@echo "Evennia-specific: "
	@echo " release  - build and prepare multiversion docs and auto-docs for release."

.PHONY: help Makefile

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

# Evennia - custom commands

install:
	@pip install -r requirements.txt

# build / update only the api-autodoc index
autodoc-index:
	@sphinx-apidoc -f -o $(SOURCEDIR)/api/ $(EVDIR)

api-build:
	@EVDIR=$(EVDIR) EVGAMEDIR=$(EVGAMEDIR) $(SPHINXBUILD) "$(SOURCEDIR)" "$(BUILDDIR)/html/api"

clean:
	@rm -Rf $(BUILDDIR)
	@git clean -f -d docs/
	@echo "Cleaned old build dir and leftover files."


# multiversion release builds

mv-check-env:
	@EVDIR=$(EVDIR) EVGAMEDIR=$(EVGAMEDIR) bash -e checkenv.sh multiversion

# we must commit the index before it's made available to multiversion 
mv-autodoc-index:
	@sphinx-apidoc -f -o $(SOURCEDIR)/api/ $(EVDIR)
	git diff-index --quiet HEAD || git commit -a -m "Updated API autodoc index."

multiversion-build:
	@EVDIR=$(EVDIR) EVGAMEDIR=$(EVGAMEDIR) sphinx-multiversion "$(SOURCEDIR)" "$(BUILDDIR)/html"

mv-deploy:
	@bash -e deploy.sh

mv-local:
	make mv-check-env
	make clean
	make mv-autodoc-index
	make multiversion-build

# build and prepare the docs for release
mv-release:
	make mv-local
	# make mv-deploy
	@echo ""
	@echo "Deployment complete."
