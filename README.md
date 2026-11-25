# uav-portfolio

Static site about `uav_monitor`, a detection and tracking pipeline for UAV video. The site replays recorded runs; the computations themselves live in a separate course repository (private, available on request).

## Layout

- `export/` - Python: recorded runs -> JSON and media for the site.
- `site/` - Astro + Svelte + TypeScript, static build.
- `deploy/` - Docker image: Node build -> nginx.

## Build

Needs Node 24 (`.nvmrc`), uv, Docker.

```bash
make install   # npm ci + uv sync
make dev       # http://localhost:4321
make test      # pytest, astro check, vitest
make image     # docker image uav-portfolio
```

`make export` reads the course repository from `../cv_course` (see `export/config.yaml`).

## License

AGPL-3.0, see `LICENSE`. The detector is fine-tuned from Ultralytics YOLO11s, which is AGPL-3.0.
