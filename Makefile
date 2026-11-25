IMAGE ?= uav-video-monitoring
COMPOSE = docker compose -f deploy/docker-compose.prod.yml

.PHONY: install export dev build test e2e image prod media

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

# on the server, in the checkout: build the image and (re)start the container on 127.0.0.1:8020
prod:
	$(COMPOSE) up -d --build

# from the machine that ran make export: copy the git-ignored VisDrone media and CV into the server checkout
media:
	@test -n "$(DEST)" || { echo 'usage: make media DEST=user@host:/path/to/checkout'; exit 1; }
	rsync -avR --delete site/public/media/visdrone/ site/public/data/visdrone/ site/public/cv/ $(DEST)/
