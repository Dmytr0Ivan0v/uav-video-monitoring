IMAGE ?= uav-video-monitoring

.PHONY: install export dev build test e2e image

install: site/node_modules
	cd export && uv sync

site/node_modules: site/package.json site/package-lock.json
	cd site && npm ci
	touch site/node_modules

export:
	cd export && uv run python -m site_export

dev: site/node_modules
	cd site && npm run dev

build: site/node_modules
	cd site && npm run build

test: site/node_modules
	cd export && uv run pytest
	cd site && npm run check
	cd site && npm test

# end-to-end checks of the production build in a browser; the detector check needs the VisDrone media of make export
e2e: site/node_modules
	cd site && npm run build && npm run e2e

image:
	docker build -f deploy/Dockerfile -t $(IMAGE) .
