#!/usr/bin/env python3
"""
Download TU datasets via torch_geometric and stage their raw text files into data/<dataset>.
Supports any dataset name accepted by torch_geometric.datasets.TUDataset (e.g., AIDS, IMDB-BINARY, PROTEINS, MUTAG, ENZYMES, NCI1, REDDIT-BINARY, etc.).
This makes the expected TU text layout available for converters and parsers.
"""

import argparse
import shutil
from pathlib import Path
from typing import Iterable, List, Tuple

from torch_geometric.datasets import TUDataset


DEFAULT_DATASETS: List[str] = [
    "AIDS",
    "IMDB-BINARY",
    "PROTEINS",
    "MUTAG",
    "NCI1",
    "ENZYMES",
]


def _collect_raw_files(raw_dir: Path, dataset_name: str) -> Iterable[Path]:
    """Yield raw files that start with the dataset prefix."""
    patterns = [f"{dataset_name}_*", f"{dataset_name}*"]
    seen = set()
    for pattern in patterns:
        for path in sorted(raw_dir.glob(pattern)):
            if path.is_file() and path.name not in seen:
                seen.add(path.name)
                yield path


def stage_dataset(
    dataset_name: str, download_root: Path, target_root: Path, overwrite: bool
) -> Tuple[Path, int, int]:
    """
    Download a TU dataset and copy its raw files into data/<dataset>.
    Returns the target directory along with counts for copied and skipped files.
    """
    dataset = TUDataset(root=str(download_root), name=dataset_name)
    raw_dir = Path(dataset.raw_dir)
    if not raw_dir.exists():
        raise FileNotFoundError(
            f"Raw directory not found for dataset '{dataset_name}' (looked in {raw_dir})"
        )

    target_dir = target_root / dataset_name
    target_dir.mkdir(parents=True, exist_ok=True)

    raw_files = list(_collect_raw_files(raw_dir, dataset_name))
    if not raw_files:
        raise RuntimeError(
            f"No raw files found for dataset '{dataset_name}' in {raw_dir}"
        )

    copied = 0
    skipped = 0
    for src in raw_files:
        dest = target_dir / src.name
        if dest.exists() and not overwrite:
            skipped += 1
            continue
        shutil.copyfile(src, dest)
        copied += 1

    return target_dir, copied, skipped


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download TU datasets and place their raw files into data/<dataset>.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--datasets",
        "-d",
        nargs="+",
        default=DEFAULT_DATASETS,
        help="TUDataset names to download and stage",
    )
    parser.add_argument(
        "--download-root",
        default="data/_tud",
        help="Directory where torch_geometric downloads datasets",
    )
    parser.add_argument(
        "--target-root",
        default="data",
        help="Root directory where staged raw files are written",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing files in target directories",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    download_root = Path(args.download_root).resolve()
    target_root = Path(args.target_root).resolve()

    failures: List[Tuple[str, Exception]] = []
    summaries: List[Tuple[str, Path, int, int]] = []

    for raw_name in args.datasets:
        dataset_name = raw_name.strip()
        if not dataset_name:
            continue
        try:
            target_dir, copied, skipped = stage_dataset(
                dataset_name, download_root, target_root, args.overwrite
            )
            summaries.append((dataset_name, target_dir, copied, skipped))
        except Exception as exc:  # noqa: BLE001
            failures.append((dataset_name, exc))

    for dataset_name, target_dir, copied, skipped in summaries:
        details = []
        if copied:
            details.append(f"copied {copied}")
        if skipped:
            details.append(f"skipped {skipped} (already present)")
        detail_str = f" ({', '.join(details)})" if details else ""
        print(f"{dataset_name}: staged to {target_dir}{detail_str}")

    if failures:
        print("\nThe following datasets failed to stage:")
        for dataset_name, exc in failures:
            print(f" - {dataset_name}: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
