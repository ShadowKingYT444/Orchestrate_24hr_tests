"""Conservative, dependency-free ZIP validation. Archive contents are never executed."""
from __future__ import annotations

import io
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import struct
import tempfile
import unicodedata
import zipfile
from .fileio import read_bounded

MAX_ZIP_BYTES = 50_000_000
MAX_EXPANDED_BYTES = 200_000_000
MAX_FILES = 5000
MAX_COMPRESSION_RATIO = 200
_CHUNK = 64 * 1024
_ARCHIVE_SUFFIXES = ('.zip', '.tar', '.tgz', '.gz', '.bz2', '.xz', '.7z', '.rar', '.jar', '.war', '.whl', '.egg', '.zst')
_SECRET_NAME = re.compile(r'(^\.env($|\.)|(^|[._-])(credentials?|secrets?|passwords?|tokens?)([._-]|$)|^id_(rsa|dsa|ecdsa|ed25519)($|\.)|\.(pem|key|p12|pfx)$)', re.I)


def _report() -> dict:
    return {'status': 'fail', 'issues': [], 'size_bytes': 0, 'expanded_bytes': 0, 'files': 0}


def _snapshot(path: Path, report: dict) -> bytes:
    # Keep one immutable, bounded snapshot for validation and subsequent extraction.
    try:
        data = read_bounded(path, MAX_ZIP_BYTES)
    except ValueError as exc:
        if 'exceeds' in str(exc):
            raise ValueError('ZIP exceeds compressed size limit') from None
        raise
    report['size_bytes'] = len(data)
    if len(data) > MAX_ZIP_BYTES:
        raise ValueError('ZIP exceeds compressed size limit')
    return data


def _name_issue(info: zipfile.ZipInfo) -> str | None:
    name = info.orig_filename
    if not name or '\x00' in name or '\\' in name or ':' in name:
        return 'Invalid or Windows-style member path'
    if name.startswith('/') or any(ord(c) < 32 or ord(c) == 127 for c in name):
        return 'Absolute or control-character member path'
    parts = name.rstrip('/').split('/')
    if any(p in ('', '.', '..') or p.endswith((' ', '.')) for p in parts):
        return 'Unsafe or ambiguous member path'
    if any(_SECRET_NAME.search(p) or p.casefold() in ('.aws', '.ssh', '.netrc', '.npmrc', '.pypirc') for p in parts):
        return 'Suspicious credential filename'
    if any(re.match(r'^(con|prn|aux|nul|com[1-9]|lpt[1-9])($|\.)', p, re.I) for p in parts):
        return 'Reserved Windows filename'
    if not info.is_dir() and name.lower().endswith(_ARCHIVE_SUFFIXES):
        return 'Nested archive filename'
    return None


def _nested_magic(prefix: bytes) -> bool:
    return (prefix.startswith((b'PK\x03\x04', b'PK\x05\x06', b'PK\x07\x08', b'\x1f\x8b',
                               b'BZh', b'\xfd7zXZ\x00', b'7z\xbc\xaf\x27\x1c', b'Rar!\x1a\x07', b'\x28\xb5\x2f\xfd'))
            or prefix[257:262] == b'ustar')


def _preflight_directory(data: bytes) -> None:
    """Bound central-directory allocation before ZipFile creates member objects."""
    end = data.rfind(b'PK\x05\x06', max(0, len(data) - 65557))
    if end < 0 or end + 22 > len(data):
        raise ValueError('Missing ZIP end record')
    disk, directory_disk, on_disk, total, size, offset, comment = struct.unpack_from('<4H2LH', data, end + 4)
    if end + 22 + comment != len(data):
        raise ValueError('Malformed ZIP end record or trailing data')
    if disk or directory_disk or on_disk != total:
        raise ValueError('Multi-volume ZIP is unsupported')
    if total == 65535 or size == 0xffffffff or offset == 0xffffffff:
        raise ValueError('ZIP64 directory is unsupported')
    if total > MAX_FILES:
        raise ValueError('ZIP exceeds member count limit')
    start = end - size
    if start < 0 or start != offset:
        raise ValueError('Invalid ZIP directory offset')
    count = 0
    cursor = start
    while cursor < end:
        if cursor + 46 > end or data[cursor:cursor + 4] != b'PK\x01\x02':
            raise ValueError('Malformed ZIP directory')
        name, extra, note = struct.unpack_from('<3H', data, cursor + 28)
        cursor += 46 + name + extra + note
        count += 1
        if count > MAX_FILES:
            raise ValueError('ZIP exceeds member count limit')
    if cursor != end or count != total:
        raise ValueError('ZIP directory count or size mismatch')


def _validate(data: bytes, report: dict) -> None:
    issues = report['issues']
    _preflight_directory(data)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = archive.infolist()
        report['files'] = len(entries)
        report['expanded_bytes'] = sum(i.file_size for i in entries)
        if len(entries) > MAX_FILES:
            raise ValueError('ZIP exceeds member count limit')
        if report['expanded_bytes'] > MAX_EXPANDED_BYTES:
            raise ValueError('ZIP exceeds expanded size limit')
        names = {}
        for info in entries:
            issue = _name_issue(info)
            if issue:
                issues.append(f'{issue}: {info.orig_filename!r}')
            key = unicodedata.normalize('NFC', info.filename.rstrip('/')).casefold()
            if key in names:
                issues.append(f'Duplicate or case-colliding member: {info.filename!r}')
            names[key] = info.is_dir()
            mode = info.external_attr >> 16
            kind = stat.S_IFMT(mode)
            if kind not in (0, stat.S_IFREG, stat.S_IFDIR):
                issues.append(f'Symlink or special member: {info.filename!r}')
            if (kind == stat.S_IFDIR and not info.is_dir()) or (info.is_dir() and info.file_size):
                issues.append(f'Invalid directory member: {info.filename!r}')
            if info.flag_bits & 1:
                issues.append(f'Encrypted member: {info.filename!r}')
            if info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                issues.append(f'Unsupported compression: {info.filename!r}')
            if info.file_size > MAX_COMPRESSION_RATIO * max(1, info.compress_size):
                issues.append(f'Compression ratio exceeds limit: {info.filename!r}')
        for key in names:
            for parent in PurePosixPath(key).parents:
                if str(parent) in names and not names[str(parent)]:
                    issues.append(f'File/directory path collision: {key!r}')
        # Case-ambiguous implicit directories also collide on many target filesystems.
        spellings = {}
        for info in entries:
            parts = info.filename.rstrip('/').split('/')
            for n in range(1, len(parts) + 1):
                spelling = '/'.join(parts[:n])
                key = unicodedata.normalize('NFC', spelling).casefold()
                if key in spellings and spellings[key] != spelling:
                    issues.append(f'Ambiguous path spelling: {spelling!r}')
                spellings[key] = spelling
        if issues:
            return
        actual_total = 0
        for info in entries:
            count = 0
            prefix = b''
            with archive.open(info) as source:
                while True:
                    block = source.read(min(_CHUNK, MAX_EXPANDED_BYTES - actual_total + 1))
                    if not block:
                        break
                    count += len(block)
                    actual_total += len(block)
                    prefix = (prefix + block)[:512] if len(prefix) < 512 else prefix
                    if actual_total > MAX_EXPANDED_BYTES or count > info.file_size:
                        raise ValueError('Actual expanded data exceeds size limit')
            if count != info.file_size:
                raise ValueError('Member expanded size mismatch')
            if _nested_magic(prefix):
                issues.append(f'Nested archive content: {info.filename!r}')
        report['expanded_bytes'] = actual_total
    if not issues:
        report['status'] = 'pass'


def _inspect(path: Path) -> tuple[dict, bytes | None]:
    report = _report()
    data = None
    try:
        data = _snapshot(path, report)
        _validate(data, report)
    except (OSError, ValueError, zipfile.BadZipFile, NotImplementedError, RuntimeError, EOFError) as exc:
        report['issues'].append(f'Archive validation failed: {exc}')
    except Exception as exc:
        # Decompressor-specific errors are invalid input too; never partially trust it.
        report['issues'].append(f'Archive validation failed ({type(exc).__name__}): {exc}')
    return report, data


def inspect_archive(path: Path) -> dict:
    """Validate metadata, paths, bounded decompression, and CRC of every ZIP member."""
    return _inspect(path)[0]


def inspect_submission_archive(path: Path) -> dict:
    """Add conservative source-upload hygiene to generic ZIP safety checks.

Directory-name exclusions are local policy, not proof that all provided datasets,
artifacts or embedded credentials have been found.
"""
    report, data = _inspect(path)
    if report['status'] != 'pass':
        return report
    excluded = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', '.pytest_cache',
                '.mypy_cache', 'build', 'dist', 'dataset', 'datasets'}
    with zipfile.ZipFile(io.BytesIO(data)) as source:
        files = [entry.filename for entry in source.infolist() if not entry.is_dir()]
    if not any(re.fullmatch(r'readme(?:\.(?:md|txt|rst))?', PurePosixPath(name).name, re.I) for name in files):
        report['issues'].append('Source submission needs a README file')
    for name in files:
        if any(part.casefold() in excluded for part in PurePosixPath(name).parts[:-1]) or name.lower().endswith(('.pyc', '.pyo')):
            report['issues'].append(f'Locally excluded dataset/dependency/build path: {name!r}')
    report['status'] = 'fail' if report['issues'] else 'pass'
    return report


def safe_extract(path: Path, destination: Path) -> dict:
    """Validate first, extract privately, then rename into a new destination.

    The destination parent must be trusted (not writable by untrusted processes).
    Refuses existing destinations, including broken symlinks. Failure cleans up
    temporary output. No permissions or links from the archive are restored.
    """
    destination = Path(destination)
    if os.path.lexists(destination):
        raise ValueError('Extraction destination already exists')
    report, data = _inspect(path)
    if report['status'] != 'pass':
        raise ValueError('; '.join(report['issues']))
    if not destination.parent.is_dir():
        raise ValueError('Extraction destination parent must already exist')
    temporary = Path(tempfile.mkdtemp(prefix='.zip-extract-', dir=destination.parent))
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for info in archive.infolist():
                target = temporary.joinpath(*PurePosixPath(info.filename).parts)
                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(info) as source, target.open('xb') as output:
                        shutil.copyfileobj(source, output, length=_CHUNK)
        if os.path.lexists(destination):
            raise ValueError('Extraction destination already exists')
        os.rename(temporary, destination)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return report
