from __future__ import annotations
import shutil
import argparse
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional



@dataclass
class Stats:
    files_copied: int = 0
    dirs_visited: int = 0
    skipped: int = 0
    errors: int = 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Recursively copy files from SRC to DST, sorting them into subfolders by extension."
    )
    parser.add_argument("src", type=Path, help="Source directory")
    parser.add_argument(
        "dst",
        type=Path,
        nargs="?",
        default=Path("dist"),
        help="Destination directory (default: dist)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not copy anything, just show what would be done",
    )
    parser.add_argument(
        "--follow-symlinks",
        action="store_true",
        help="Follow symlinks (by default symlinks are skipped)",
    )
    return parser.parse_args()


def extension_folder(file_path: Path) -> str:
    try:
        ext = file_path.suffix.lower().lstrip(".")
        return ext if ext else "_noext"
    except Exception:
        return "_noext"


def is_under(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except Exception:
        return False


def make_unique_path(dst_dir: Path, filename: str) -> Path:
    try:
        candidate = dst_dir / filename
        if not candidate.exists():
            return candidate

        stem = candidate.stem
        suffix = candidate.suffix
        k = 1
        while True:
            alt = dst_dir / f"{stem} ({k}){suffix}"
            if not alt.exists():
                return alt
            k += 1
    except Exception:
        return dst_dir / filename


# ---------- Головна логіка ----------

def copy_one(file_path: Path, dst_root: Path, *, dry_run: bool) -> Optional[Path]:
    try:
        subfolder = extension_folder(file_path)
        dst_dir = dst_root / subfolder
        if dry_run:
            print(f"[DRY] mkdir -p {dst_dir}")
        else:
            dst_dir.mkdir(parents=True, exist_ok=True)

        dst_path = make_unique_path(dst_dir, file_path.name)
        if dry_run:
            print(f"[DRY] COPY '{file_path}' -> '{dst_path}'")
            return dst_path

        shutil.copy2(file_path, dst_path)
        print(f"[OK ] Copied: '{file_path}' -> '{dst_path}'")
        return dst_path
    except Exception as e:
        print(f"[ERR] Copy failed for '{file_path}': {e}")
        return None


def process_dir(
    current: Path,
    dst_root: Path,
    stats: Stats,
    *,
    dry_run: bool,
    follow_symlinks: bool,
    dst_root_real: Path,
) -> None:
    try:
        stats.dirs_visited += 1

        for entry in current.iterdir():
            try:
                if is_under(entry, dst_root_real):
                    stats.skipped += 1
                    continue

                if entry.is_symlink() and not follow_symlinks:
                    print(f"[SKP] Symlink skipped: '{entry}'")
                    stats.skipped += 1
                    continue

                if entry.is_dir():
                    process_dir(
                        entry,
                        dst_root,
                        stats,
                        dry_run=dry_run,
                        follow_symlinks=follow_symlinks,
                        dst_root_real=dst_root_real,
                    )
                    continue

                if entry.is_file() or entry.is_symlink():
                    dst = copy_one(entry, dst_root, dry_run=dry_run)
                    if dst is not None:
                        stats.files_copied += 1
                    else:
                        stats.errors += 1
                else:
                    stats.skipped += 1
            except PermissionError as e:
                print(f"[PERM] '{entry}': {e}")
                stats.errors += 1
            except Exception as e:
                print(f"[ERR] Unexpected error on '{entry}': {e}")
                stats.errors += 1
    except PermissionError as e:
        print(f"[PERM] '{current}': {e}")
        stats.errors += 1
    except Exception as e:
        print(f"[ERR] Failed to iterate '{current}': {e}")
        stats.errors += 1


def main() -> int:
    try:
        args = parse_args()
        src: Path = args.src
        dst: Path = args.dst
        dry_run: bool = args.dry_run
        follow_symlinks: bool = args.follow_symlinks

        if not src.exists() or not src.is_dir():
            print(f"[ERR] Source '{src}' does not exist or is not a directory")
            return 2

        if dry_run:
            print(f"[DRY] mkdir -p {dst}")
        else:
            dst.mkdir(parents=True, exist_ok=True)

        stats = Stats()
        process_dir(
            current=src,
            dst_root=dst,
            stats=stats,
            dry_run=dry_run,
            follow_symlinks=follow_symlinks,
            dst_root_real=dst.resolve(),
        )

        print("\n===== SUMMARY =====")
        print(f"Source:        {src.resolve()}")
        print(f"Destination:   {dst.resolve()}")
        print(f"Dirs visited:  {stats.dirs_visited}")
        print(f"Files copied:  {stats.files_copied}")
        print(f"Skipped:       {stats.skipped}")
        print(f"Errors:        {stats.errors}")
        print("===================\n")

        return 0
    except Exception as e:
        print(f"[FATAL] {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

