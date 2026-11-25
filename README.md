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

`make export` reads the course repository from `../cv_course` (see `export/config.yaml`). It needs ffmpeg and the VisDrone2019-MOT-val annotations in the course checkout.

## Data

- `site/public/data/console/` - replay of recorded runs on VisDrone clip 137: boxes per frame, statuses, stage timings, checks of the scenario tables.
- `site/public/data/facts.json` - headline numbers, each with the results file and check it comes from.
- `site/public/data/manifest.json` - sha256 of every exported file and of its sources, commit of the course repository.
- `export/recipe/` - how the detector weights were made.

VisDrone has no license file, so its pixels and labels are not in this repository: `make export` builds the clip, still frames and ground truth boxes into `site/public/media/visdrone/` and `site/public/data/visdrone/` (git-ignored). Without them the site builds and the console shows no video. VisDrone: AISKYEYE team, Tianjin University; P. Zhu et al., "Detection and Tracking Meet Drones Challenge", IEEE TPAMI, vol. 44, no. 11, pp. 7380-7399, 2021.

## License

AGPL-3.0, see `LICENSE`. The detector is fine-tuned from Ultralytics YOLO11s, which is AGPL-3.0.
