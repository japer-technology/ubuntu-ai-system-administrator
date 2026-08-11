# Makefile for Ubuntu Zombie.

SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c

VERSION := $(shell cat VERSION)
PYTHON ?= python3
FRIEND_ROOT := products/imaginary-friend
FORGEJO_ROOT := products/forgejo
LLAMA_ROOT := products/llama
BEEP_ROOT := products/beep

.PHONY: help lint test verify-bridge-pins install-local verify package deb clean

help:
	@echo "Targets:"
	@echo "  lint           root and product ShellCheck, syntax, and compile"
	@echo "  test           root and product non-root test suites"
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
	$(MAKE) -C $(FRIEND_ROOT) lint PYTHON="$(PYTHON)"
	$(MAKE) -C $(FORGEJO_ROOT) lint PYTHON="$(PYTHON)"
	$(MAKE) -C $(LLAMA_ROOT) lint PYTHON="$(PYTHON)"
	$(MAKE) -C $(BEEP_ROOT) lint PYTHON="$(PYTHON)"

test:
	bash tests/smoke.sh all
	$(MAKE) -C $(FRIEND_ROOT) test PYTHON="$(PYTHON)"
	$(MAKE) -C $(FORGEJO_ROOT) test PYTHON="$(PYTHON)"
	$(MAKE) -C $(LLAMA_ROOT) test PYTHON="$(PYTHON)"
	$(MAKE) -C $(BEEP_ROOT) test PYTHON="$(PYTHON)"

verify-bridge-pins:
	bash scripts/verify-bridge-pins.sh

install-local:
	@if [ "$$(id -u)" -ne 0 ]; then echo 'install-local must be run as root (sudo make install-local)'; exit 1; fi
	./scripts/install.sh install

verify:
	@if [ -x /opt/ai-zombie/bin/verify ]; then /opt/ai-zombie/bin/verify; \
	 else ./scripts/install.sh verify; fi

package:
	@mkdir -p dist
	@tar --exclude-vcs --exclude='dist' --exclude='__pycache__' \
	     --exclude='products/forgejo/dist' \
	     --exclude='products/llama/dist' \
	     -czf dist/ubuntu-zombie-$(VERSION).tar.gz \
	     scripts payload tests products/forgejo products/llama family/schemas \
	     Makefile VERSION \
	     README.md CHANGELOG.md CONTRIBUTING.md CODE_OF_CONDUCT.md \
	     LICENSE .editorconfig \
	     SECURITY.md docs debian
	@echo "Wrote dist/ubuntu-zombie-$(VERSION).tar.gz"

deb:
	@command -v dpkg-deb >/dev/null || { echo 'install dpkg-dev first (sudo apt install dpkg-dev)' >&2; exit 1; }
	bash scripts/build-deb.sh

clean:
	rm -rf dist
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	$(MAKE) -C $(FRIEND_ROOT) clean
	$(MAKE) -C $(FORGEJO_ROOT) clean
	$(MAKE) -C $(LLAMA_ROOT) clean
	$(MAKE) -C $(BEEP_ROOT) clean
