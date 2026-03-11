# Makefile (root)
# Usage: make help

SHELL := /bin/bash

BACKEND_DIR := backend
FRONTEND_DIR := frontend
BACKEND_PORT ?= 8000

.PHONY: help dev-front dev-back dev install install-front install-back \
        fmt lint test clean \

help:
	@echo "Targets:"
	@echo "  make install        Install front+back deps"
	@echo "  make dev-front      Start React dev server"
	@echo "  make dev-back       Start FastAPI (uvicorn --reload)"
	@echo "  make dev            Start both (2 terminals recommended)"
	@echo "  make fmt            Format backend (ruff)"
	@echo "  make lint           Lint backend (ruff)"
	@echo "  make test           Run backend tests (pytest)"
	@echo "  make clean          Remove caches"

install: install-front install-back

install-front:
	cd $(FRONTEND_DIR) && pnpm install

install-back:
	cd $(BACKEND_DIR) && uv sync

dev-front:
	cd $(FRONTEND_DIR) && pnpm dev

dev-back:
	cd $(BACKEND_DIR) && uv run uvicorn app.main:app --reload --port $(BACKEND_PORT)

# Note: make dev launches both but logs will mix.
# For a nicer experience, run `make dev-front` and `make dev-back` in two terminals.
dev:
	@echo "Starting front + back (logs may mix). Prefer 2 terminals."
	@$(MAKE) -j2 dev-front dev-back

# ---- Quality (backend) ----
# Add these deps in backend when you want:
#   uv add -D ruff pytest
fmt:
	cd $(BACKEND_DIR) && uv run ruff format .

lint:
	cd $(BACKEND_DIR) && uv run ruff check .

test:
	cd $(BACKEND_DIR) && uv run pytest -q

clean:
	rm -rf $(BACKEND_DIR)/.pytest_cache $(BACKEND_DIR)/**/__pycache__ \
	       $(FRONTEND_DIR)/node_modules/.cache $(FRONTEND_DIR)/dist