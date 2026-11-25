IMAGE ?= uav-portfolio

.PHONY: install export dev build test image

install: site/node_modules
	cd export && uv sync

site/node_modules: site/package.json site/package-lock.json
	cd site && npm ci
	touch site/node_modules

export:
	cd export && uv run python -m portfolio_export

dev: site/node_modules
	cd site && npm run dev

build: site/node_modules
	cd site && npm run build

test: site/node_modules
	cd export && uv run pytest
	cd site && npm run check
	cd site && npm test

image:
	docker build -f deploy/Dockerfile -t $(IMAGE) .
