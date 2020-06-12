# Makefile to control Evennia documentation building.
# Most common commands are `make help`, `make quick` and `make local`.

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SPHINXMULTIVERSION ?= sphinx-multiversion
SPHINXAPIDOC ?= sphinx-apidoc
SPHINXAPIDOCOPTS = --tocfile evennia-api  --module-first --force
SPHINXAPIDOCENV = members,undoc-members,show-inheritance
SPHINXAPIDOCEXCLUDE = */migrations/*
SOURCEDIR     = source
BUILDDIR      = build
AUTODOCDIR = $(SOURCEDIR)/api

EVDIR ?= $(realpath ../evennia)
EVGAMEDIR ?= $(realpath ../../gamedir)

cblue = $(shell echo "\033[1m\033[34m")
cnorm = $(shell echo "\033[0m")

QUICKFILES=$(SOURCEDIR)/*.md


# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
	@echo "Evennia-specific: "
	@echo "  $(cblue)install$(cnorm)     to get build requirements"
	@echo "  $(cblue)clean$(cnorm)       to remove remnants of a previous build"
	@echo "  $(cblue)local$(cnorm)       to build local html docs of the current branch (no multiversion)."
	@echo "  $(cblue)mv-local$(cnorm)    to build multiversion html docs, without deploying (req. local git commit)"
	@echo "  $(cblue)release$(cnorm)     to build and deploy multiversion docs online (req. commit and github push access)"


.PHONY: help Makefile

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

# Evennia - custom commands

# helper targets

_check-env:
	@EVDIR=$(EVDIR) EVGAMEDIR=$(EVGAMEDIR) bash -e checkenv.sh

_multiversion-check-env:
	@EVDIR=$(EVDIR) EVGAMEDIR=$(EVGAMEDIR) bash -e checkenv.sh multiversion

_clean_api_index:
	rm source/api/*

_autodoc-index:
	@EVDIR=$(EVDIR) EVGAMEDIR=$(EVGAMEDIR) SPHINX_APIDOC_OPTIONS=$(SPHINXAPIDOCENV) $(SPHINXAPIDOC) $(SPHINXAPIDOCOPTS) -o $(SOURCEDIR)/api/ $(EVDIR) $(SPHINXAPIDOCEXCLUDE)

_multiversion-autodoc-index:
	@EVDIR=$(EVDIR) EVGAMEDIR=$(EVGAMEDIR) SPHINX_APIDOC_OPTIONS=$(SPHINXAPIDOCENV) $(SPHINXAPIDOC) $(SPHINXAPIDOCOPTS) -o $(SOURCEDIR)/api/ $(EVDIR) $(SPHINXAPIDOCEXCLUDE)
	git diff-index --quiet HEAD || git commit -a -m "Updated API autodoc index."

_build:
	@EVDIR=$(EVDIR) EVGAMEDIR=$(EVGAMEDIR) $(SPHINXBUILD) $(SPHINXOPTS) "$(SOURCEDIR)" "$(BUILDDIR)/html"

_quick-build:
	@NOAUTODOC=1 EVDIR=$(EVDIR) EVGAMEDIR=$(EVGAMEDIR) $(SPHINXBUILD) $(SPHINXOPTS) "$(SOURCEDIR)" "$(BUILDDIR)/html" $(QUICKFILES)

_multiversion-build:
	@EVDIR=$(EVDIR) EVGAMEDIR=$(EVGAMEDIR) $(SPHINXMULTIVERSION) $(SPHINXOPTS) "$(SOURCEDIR)" "$(BUILDDIR)/html" $(SPHINXOPTS)

_multiversion-deploy:
	@bash -e deploy.sh

# main targets

install:
	@pip install -r requirements.txt

clean:
	@rm -Rf $(BUILDDIR)
	@git clean -f -d docs/
	@echo "Cleaned old build dir and leftover files."

# TODO remove once done with migration
copy:
	@cd pylib && python copy_from_wiki.py && cd ..
	make quick 

quick:
	make _check-env
	make _quick-build $(FILES)
	@echo ""
	@echo "Documentation built (no autodocs). \nTo see result, open evennia/docs/build/html/index.html in a browser."

local:
	make _check-env
	make clean
	make _autodoc-index
	make _build
	@echo ""
	@echo "Documentation built. \nTo see result, open evennia/docs/build/html/index.html in a browser."

mv-local:
	make _multiversion-check-env
	make clean
	make _multiversion-autodoc-index
	make _multiversion-build
	@echo "Documentation built. \nTo see result, open evennia/docs/build/html/versions/<version>/index.html in a browser."

deploy:
	make _multiversion-deploy

# build and prepare the docs for release
release:
	make mv-local
	make _mv-deploy
	@echo ""
	@echo "Deployment complete."
