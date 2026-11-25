"""Command line interface: python -m portfolio_export [--config config.yaml]."""

import argparse
from pathlib import Path

from portfolio_export.config import load_config


def main() -> None:
    parser = argparse.ArgumentParser(prog='portfolio_export')
    parser.add_argument('--config', type=Path, default=Path('config.yaml'))
    args = parser.parse_args()

    cfg = load_config(args.config)
    print(f'course: {cfg.course}')
    print(f'data:   {cfg.data_dir}')
    print(f'media:  {cfg.media_dir}')
