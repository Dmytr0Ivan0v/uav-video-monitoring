"""Hero clip: source video + boxes of one console run -> H.264 clip with the boxes drawn in, poster."""

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

from site_export.media import BITEXACT


def hero_clip(src: Path, out: Path, poster: Path, run: dict, source_size: list[int], size: tuple[int, int],
              fps: int, colors: dict[int, str], crf: int) -> int:
    w, h = size
    k = w / source_size[0]
    tracks = {f['frame']: f['tracks'] for f in run['frames']}
    # the clip starts where the first boxes appear, so the poster and the first frame match
    first = min(f for f, t in tracks.items() if t)
    out.parent.mkdir(parents=True, exist_ok=True)

    decoder = subprocess.Popen(
        ['ffmpeg', '-nostdin', '-v', 'error', '-i', str(src), '-vf', f'scale={w}:{h}',
         '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
        stdout=subprocess.PIPE)
    encoder = subprocess.Popen(
        ['ffmpeg', '-nostdin', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{w}x{h}',
         '-r', str(fps), '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', str(crf), '-pix_fmt', 'yuv420p',
         '-an', '-movflags', '+faststart', *BITEXACT, str(out)],
        stdin=subprocess.PIPE)

    size_bytes = w * h * 3
    boxes: list = []
    frame = 0
    while len(buf := decoder.stdout.read(size_bytes)) == size_bytes:
        # boxes of a processed frame stay on screen until the next processed frame, as in the console
        boxes = tracks.get(frame, boxes)
        if frame >= first:
            img = Image.frombytes('RGB', (w, h), buf)
            draw = ImageDraw.Draw(img)
            for _, cls, _, x1, y1, x2, y2 in boxes:
                draw.rectangle((x1 * k, y1 * k, x2 * k, y2 * k), outline=colors[cls], width=2)
            if frame == first:
                img.save(poster, 'WEBP', quality=70, method=6)
            encoder.stdin.write(img.tobytes())
        frame += 1
    encoder.stdin.close()
    if decoder.wait() != 0 or encoder.wait() != 0:
        raise RuntimeError(f'ffmpeg failed on {src} -> {out}')
    return first
