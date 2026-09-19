from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Set

from .config import PREVIEW_CACHE_MAX_AGE_DAYS, PREVIEW_CACHE_MAX_SIZE_MB, PREVIEW_DIR

LOG = logging.getLogger(__name__)

MAX_SIZE_BYTES = PREVIEW_CACHE_MAX_SIZE_MB * 1024 * 1024
MAX_AGE_SECONDS = PREVIEW_CACHE_MAX_AGE_DAYS * 86400

_recently_accessed: Set[str] = set()
_last_eviction_time = 0.0
EVICTION_COOLDOWN_SECONDS = 5.0


def _touch(path: Path) -> None:
    try:
        path.touch()
    except OSError:
        pass


def _mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def _size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def evict_preview_cache() -> tuple[int, int]:
    if not PREVIEW_DIR.exists():
        return 0, 0

    now = time.time()
    global _last_eviction_time
    if now - _last_eviction_time < EVICTION_COOLDOWN_SECONDS:
        return 0, 0

    _last_eviction_time = now

    evicted_count = 0
    evicted_bytes = 0

    try:
        files = list(PREVIEW_DIR.iterdir())
    except OSError:
        return 0, 0

    aged: list[tuple[float, int, Path]] = []
    all_eligible: list[tuple[float, int, Path]] = []
    total_size = 0

    for f in files:
        if f.suffix not in {".html", ".svg"}:
            continue
        try:
            st = f.stat()
        except OSError:
            continue
        total_size += st.st_size
        age = now - st.st_mtime
        if f.name in _recently_accessed:
            _touch(f)
        elif age > MAX_AGE_SECONDS:
            aged.append((st.st_mtime, st.st_size, f))
            all_eligible.append((st.st_mtime, st.st_size, f))
        else:
            all_eligible.append((st.st_mtime, st.st_size, f))

    aged.sort(key=lambda x: x[0])
    all_eligible.sort(key=lambda x: x[0])

    space_to_free = total_size - MAX_SIZE_BYTES
    if space_to_free > 0:
        for mtime, size, path in all_eligible:
            if space_to_free <= 0:
                break
            try:
                path.unlink()
                evicted_count += 1
                evicted_bytes += size
                space_to_free -= size
                LOG.debug("Evicted preview cache file: %s (%d bytes)", path.name, size)
            except OSError:
                pass

    for mtime, size, path in aged:
        if path.exists():
            try:
                path.unlink()
                evicted_count += 1
                evicted_bytes += size
                LOG.debug("Evicted aged preview cache file: %s", path.name)
            except OSError:
                pass

    if evicted_count > 0:
        LOG.info(
            "Preview cache eviction: removed %d files, freed %d bytes",
            evicted_count,
            evicted_bytes,
        )

    return evicted_count, evicted_bytes


def mark_preview_accessed(cache_file: str | Path) -> None:
    _recently_accessed.add(Path(cache_file).name)


def clear_accessed_cache() -> None:
    _recently_accessed.clear()