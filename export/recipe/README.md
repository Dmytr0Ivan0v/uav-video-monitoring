# Weights recipe

The detector is YOLO11s (Ultralytics, AGPL-3.0) fine-tuned on VisDrone2019-DET. The weights are not here; the two files below say how they were made. `make export` writes them from the course repository.

- `train_args.yaml` - Ultralytics arguments of the fine-tune from `yolo11s.pt`. Paths of the training machine are replaced with paths inside the course repository.
- `onnx_export.json` - the ONNX export: command, export parameters, input and output shapes, package versions, sha256 of `ft1.pt` and `ft1.onnx`.

To rebuild: train with `train_args.yaml` on VisDrone2019-DET in the COCO class layout, then export with the command and parameters from `onnx_export.json`. A new training run will not match the sha256 byte for byte; the sha256 identifies the weights all recorded runs used. The VisDrone data is not part of this repository.
