"""Clip media for the console: source mp4 -> H.264 for the browser, still frames (ffmpeg)."""

import subprocess
from pathlib import Path

# no encoder version or creation time in the output: a rerun gives the same bytes
BITEXACT = ['-fflags', '+bitexact', '-flags:v', '+bitexact', '-map_metadata', '-1']


def frame_count(video: Path) -> int:
    out = subprocess.run(
        ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_frames',
         '-show_entries', 'stream=nb_read_frames', '-of', 'csv=p=0', str(video)],
        check=True, capture_output=True, text=True)
    return int(out.stdout)


def encode_clip(src: Path, out: Path, size: tuple[int, int], crf: int, gop: int) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', str(src),
         '-vf', f'scale={size[0]}:{size[1]}', '-c:v', 'libx264', '-preset', 'slow', '-crf', str(crf),
         '-g', str(gop), '-pix_fmt', 'yuv420p', '-an', '-movflags', '+faststart', *BITEXACT, str(out)],
        check=True)


def still(src: Path, out: Path, frame: int, size: tuple[int, int]) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', str(src),
         # select by decoded index, not by time: -ss can land on a neighbouring frame
         '-vf', f'select=eq(n\\,{frame}),scale={size[0]}:{size[1]}', '-frames:v', '1', '-q:v', '3',
         *BITEXACT, str(out)],
        check=True)
