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
make e2e       # build, then Playwright on the build: pages, console, labs, axe, first-screen budget
make image     # docker image uav-portfolio
```

`make export` reads the course repository from `../cv_course` (see `export/config.yaml`). It needs ffmpeg and the VisDrone2019-MOT-val annotations in the course checkout.

## Data

- `site/public/data/console/` - replay of recorded runs on VisDrone clip 137: boxes per frame, statuses, stage timings, checks of the scenario tables.
- `site/public/data/facts.json` - every number the page texts quote, each with the course file and field it comes from.
- `site/public/data/engineering.json` - engine benchmarks, scenario results and the long stability run.
- `site/public/data/detector.json` and `site/public/models/ft1.onnx` - the browser detector: the ONNX model of the course runs, its thresholds, reference boxes on five clip frames, the robustness curves.
- `site/public/data/navigation.json` and `site/public/media/tum/` - visual odometry runs on TUM RGB-D fr1_xyz: poses after one SE3 alignment, the error at every pose, gray frames the odometry saw.
- `site/public/data/change.json` - change detection on clip 137: PR curve over the thresholds, pair statistics, light normalization, the hand review of false spots. The aligned frames and the mask levels per threshold are VisDrone pixels and are built into `site/public/media/visdrone/change/`.
- `site/src/lib/detector/fixtures/` - cv2 and numpy outputs the browser code is tested against.
- `site/public/data/manifest.json` - sha256 of every exported file and of its sources, commit of the course repository.
- `export/recipe/` - how the detector weights were made.

TUM RGB-D fr1_xyz (J. Sturm et al., "A Benchmark for the Evaluation of RGB-D SLAM Systems", IROS 2012) is CC BY 4.0: its gray thumbnails are in `site/public/media/tum/`.

VisDrone has no license file, so its pixels and labels are not in this repository: `make export` builds the clip, the header clip with boxes drawn in, still frames and ground truth boxes into `site/public/media/visdrone/` and `site/public/data/visdrone/` (git-ignored). Without them the site builds and the console shows no video. The CV PDFs in `site/public/cv/` are kept out of git the same way, because they carry contact details; the page links them only after a click, and `robots.txt` closes `/cv/`. VisDrone: AISKYEYE team, Tianjin University; P. Zhu et al., "Detection and Tracking Meet Drones Challenge", IEEE TPAMI, vol. 44, no. 11, pp. 7380-7399, 2021.

## License

AGPL-3.0, see `LICENSE`. The detector is fine-tuned from Ultralytics YOLO11s, which is AGPL-3.0.
