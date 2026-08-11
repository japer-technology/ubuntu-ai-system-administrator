# Makefile for Ubuntu AI System Administrator.

SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c

VERSION := $(shell cat VERSION)

.PHONY: help lint test verify-bridge-pins install-local verify package deb clean

help:
	@echo "Targets:"
	@echo "  lint           ShellCheck, syntax, and Python compile"
	@echo "  test           Ubuntu AI System Administrator non-root test suite"
	@echo "  verify-bridge-pins  checksum pinned Node bridge inputs"
	@echo "  install-local  sudo ./scripts/install.sh install (RUN ON A VM)"
	@echo "  verify         sudo ./scripts/install.sh verify"
	@echo "  package        tar a release bundle into dist/"
	@echo "  deb            build a .deb package into dist/"
	@echo "  clean          remove dist/ and python caches"

lint:
	@command -v shellcheck >/dev/null || { echo 'install shellcheck first' >&2; exit 1; }
	@set -e; \
	for f in $$(git ls-files | grep -E '\.(sh|bash)$$' || true) \
	         $$(git ls-files payload/bin); do \
	    head -n1 "$$f" | grep -q '^#!.*bash' || continue; \
	    echo "shellcheck $$f"; \
	    shellcheck --severity=warning "$$f"; \
	done
	bash tests/smoke.sh syntax
	bash tests/smoke.sh python

test:
	bash tests/smoke.sh all

verify-bridge-pins:
	bash scripts/verify-bridge-pins.sh

install-local:
	@if [ "$$(id -u)" -ne 0 ]; then echo 'install-local must be run as root (sudo make install-local)'; exit 1; fi
	./scripts/install.sh install

verify:
	@if [ -x /opt/ai-system-administrator/bin/verify ]; then /opt/ai-system-administrator/bin/verify; \
	 else ./scripts/install.sh verify; fi

package:
	@mkdir -p dist
	@tar --exclude-vcs --exclude='dist' --exclude='__pycache__' \
	     -czf dist/ubuntu-ai-system-administrator-$(VERSION).tar.gz \
	     scripts payload tests \
	     Makefile VERSION \
	     README.md CHANGELOG.md CONTRIBUTING.md CODE_OF_CONDUCT.md \
	     LICENSE .editorconfig \
	     SECURITY.md docs debian
	@echo "Wrote dist/ubuntu-ai-system-administrator-$(VERSION).tar.gz"

deb:
	@command -v dpkg-deb >/dev/null || { echo 'install dpkg-dev first (sudo apt install dpkg-dev)' >&2; exit 1; }
	bash scripts/build-deb.sh

clean:
	rm -rf dist
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
