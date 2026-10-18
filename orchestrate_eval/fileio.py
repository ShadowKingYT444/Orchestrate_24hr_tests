"""Bounded regular-file snapshots for local evaluation inputs.

These guards reduce accidental resource misuse; they do not secure a mutable,
hostile filesystem or replace an OS sandbox.
"""
import hashlib
import os
from pathlib import Path
import stat

MAX_FILE = 5_000_000


def read_bounded(path, limit=MAX_FILE):
    path = Path(path)
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
        raise ValueError(f"Symlink input refused: {path.name}")
    # NONBLOCK prevents a FIFO from hanging before the regular-file check.
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise ValueError(f"Input must be a regular file: {path.name}")
        if info.st_size > limit:
            raise ValueError(f"Input exceeds {limit} bytes: {path.name}")
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError(f"Input exceeds {limit} bytes: {path.name}")
    return data


def digest_file(path, limit=MAX_FILE):
    return hashlib.sha256(read_bounded(path, limit)).hexdigest()
