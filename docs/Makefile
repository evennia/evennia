# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = source
BUILDDIR      = build

EVDIR ?= $(realpath ../)
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
	make help
	# @$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

# Evennia - custom commands

install:
	@pip install -r requirements.txt

check-env:
	@EVDIR=$(EVDIR) EVGAMEDIR=$(EVGAMEDIR) bash -e checkenv.sh

# build only the api-autodoc index
autodoc-index:
	@sphinx-apidoc -f -o $(SOURCEDIR)/api/ $(EVDIR)

api-build:
	@EVDIR=$(EVDIR) EVGAMEDIR=$(EVGAMEDIR) $(SPHINXBUILD) "$(SOURCEDIR)" "$(BUILDDIR)/html/api"

multiversion-build:
	@EVDIR=$(EVDIR) EVGAMEDIR=$(EVGAMEDIR) sphinx-multiversion "$(SOURCEDIR)" "$(BUILDDIR)/html"

clean:
	@rm -Rf $(BUILDDIR)
	@git clean -f -d
	@echo "Cleaned old build dir and leftover files."

local:
	make check-env
	make autodoc-index
	make multiversion-build

deploy:
	@bash -e deploy.sh

# build and prepare the docs for release
release:
	make check-env
	make clean
	make autodoc-index
	make multiversion-build
	make deploy
	make clean
	@echo ""
	@echo "Deployment complete."
