SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c

PYTHON ?= python3
VERSION := $(shell cat VERSION)
REPOSITORY_ROOT := ../..

.PHONY: help lint test package clean

help:
	@echo "Targets:"
	@echo "  lint     ShellCheck, bash syntax, and Python compile"
	@echo "  test     unit, integration, and lifecycle conformance tests"
	@echo "  package  independent Llama source artifact"
	@echo "  clean    remove generated artifacts and caches"

lint:
	@command -v shellcheck >/dev/null || { echo 'install shellcheck first' >&2; exit 1; }
	@set -e; \
	while IFS= read -r file; do \
	  echo "shellcheck $$file"; \
	  shellcheck --severity=warning "$$file"; \
	  bash -n "$$file"; \
	done < <(find scripts tests/vm -type f -print | sort)
	@set -e; \
	while IFS= read -r file; do \
	  echo "$(PYTHON) -m py_compile $$file"; \
	  "$(PYTHON)" -m py_compile "$$file"; \
	done < <(find payload tests -name '*.py' -type f -print | sort)
	"$(PYTHON)" -m py_compile payload/bin/llama-manager

test:
	PYTHONPATH=payload/agent "$(PYTHON)" -m unittest discover -s tests/unit -p 'test_*.py'
	PYTHONPATH=payload/agent "$(PYTHON)" -m unittest discover -s tests/integration -p 'test_*.py'
	"$(PYTHON)" -m unittest discover -s "$(REPOSITORY_ROOT)/tests/family" -p 'test_*.py'

package:
	@mkdir -p dist
	@tar --exclude-vcs --exclude='products/llama/dist' \
	     --exclude='__pycache__' --exclude='*.pyc' \
	     -czf "dist/llama-$(VERSION).tar.gz" \
	     -C "$(REPOSITORY_ROOT)" \
	     products/llama family/schemas LICENSE
	@echo "Wrote dist/llama-$(VERSION).tar.gz"

clean:
	rm -rf dist
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
