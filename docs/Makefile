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
	@echo "  install - get build requirements"
	@echo "  clean - remove remnants of a previous build"
	@echo "  local - build local html docs of the current branch (no multiversion)."
	@echo "  mv-local - build full multiversion html docs, without deploying (req. all changes committed to git)"
	@echo "  release  - build and deploy multiversion docs online (req. github push access)"

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

_autodoc-index:
	@EVDIR=$(EVDIR) EVGAMEDIR=$(EVGAMEDIR) sphinx-apidoc -f -o $(SOURCEDIR)/api/ $(EVDIR)

_multiversion-autodoc-index:
	@EVDIR=$(EVDIR) EVGAMEDIR=$(EVGAMEDIR) sphinx-apidoc -f -o $(SOURCEDIR)/api/ $(EVDIR)
	git diff-index --quiet HEAD || git commit -a -m "Updated API autodoc index."

_build:
	@EVDIR=$(EVDIR) EVGAMEDIR=$(EVGAMEDIR) $(SPHINXBUILD) "$(SOURCEDIR)" "$(BUILDDIR)/html"

_multiversion-build:
	@EVDIR=$(EVDIR) EVGAMEDIR=$(EVGAMEDIR) sphinx-multiversion "$(SOURCEDIR)" "$(BUILDDIR)/html"

_multiversion-deploy:
	@bash -e deploy.sh

# main targets 

install:
	@pip install -r requirements.txt

clean:
	@rm -Rf $(BUILDDIR)
	@git clean -f -d docs/
	@echo "Cleaned old build dir and leftover files."

local: 
	make _check-env
	make clean	
	make _autodoc_index
	make _build
	@echo ""
	@echo "Documentation built. \nTo see result, open evennia/docs/build/html/versions/<version>/index.html in a browser."

mv-local:
	make _multiversion-check-env
	make clean
	make _multiversion-autodoc-index
	make _multiversion-build

# build and prepare the docs for release
release:
	make mv-local
	# make _mv-deploy
	@echo ""
	@echo "Deployment complete."
