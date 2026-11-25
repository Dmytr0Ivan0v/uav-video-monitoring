// File names under public/data/console, as export/config.yaml lists them.
export const STREAMS = ['nominal', 'drop_every', 'freeze', 'freeze_nocheck'] as const;
export const ENGINES = ['pytorch_cpu', 'onnx_cpu', 'pytorch_t4', 'tensorrt_t4'] as const;

export type RunId = (typeof STREAMS)[number] | (typeof ENGINES)[number];
