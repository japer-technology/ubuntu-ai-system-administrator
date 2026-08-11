SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c

PYTHON ?= python3
VERSION := $(shell cat VERSION)
REPOSITORY_ROOT := ../..

.PHONY: help lint test package clean

help:
	@echo "Targets:"
	@echo "  lint     ShellCheck, bash syntax, and Python compile"
	@echo "  test     unit, integration, and parity tests"
	@echo "  package  independent Beep source artifact"
	@echo "  clean    remove generated artifacts and caches"

lint:
	@command -v shellcheck >/dev/null || { echo 'install shellcheck first' >&2; exit 1; }
	@set -e; \
	while IFS= read -r file; do \
	  echo "shellcheck $$file"; \
	  shellcheck --severity=warning "$$file"; \
	  bash -n "$$file"; \
	done < <(find scripts payload/bin tests/vm -type f -print | sort)
	@set -e; \
	while IFS= read -r file; do \
	  echo "$(PYTHON) -m py_compile $$file"; \
	  "$(PYTHON)" -m py_compile "$$file"; \
	done < <(find payload tests -name '*.py' -type f -print | sort)

test:
	PYTHONPATH=payload/agent "$(PYTHON)" -m unittest discover -s tests/unit -p 'test_*.py'
	PYTHONPATH=payload/agent "$(PYTHON)" -m unittest discover -s tests/integration -p 'test_*.py'
	PYTHONPATH=payload/agent "$(PYTHON)" -m unittest discover -s tests/parity -p 'test_*.py'

package:
	@mkdir -p dist
	@tar --exclude-vcs --exclude='products/beep/dist' \
	     --exclude='__pycache__' --exclude='*.pyc' \
	     -czf "dist/beep-$(VERSION).tar.gz" \
	     -C "$(REPOSITORY_ROOT)" \
	     products/beep LICENSE
	@echo "Wrote dist/beep-$(VERSION).tar.gz"

clean:
	rm -rf dist
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
