"""Descriptor-relative workspace operations that never follow links."""

from __future__ import annotations

import ctypes
import errno
import hashlib
import os
import stat
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterator

from .errors import ConflictError, NotFoundError, ValidationError

MAX_FILE_BYTES = 1_048_576
_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
_CLOEXEC = getattr(os, "O_CLOEXEC", 0)
_DIRECTORY = getattr(os, "O_DIRECTORY", 0)
_RENAME_NOREPLACE = 1
_LIBC = ctypes.CDLL(None, use_errno=True)
_RENAMEAT2 = getattr(_LIBC, "renameat2", None)
if _RENAMEAT2 is not None:
    _RENAMEAT2.argtypes = (
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    )
    _RENAMEAT2.restype = ctypes.c_int
_FORBIDDEN_ROOTS = (
    Path("/boot"),
    Path("/dev"),
    Path("/etc"),
    Path("/home"),
    Path("/opt"),
    Path("/proc"),
    Path("/root"),
    Path("/run"),
    Path("/sys"),
    Path("/usr"),
    Path("/var"),
)
@dataclass(frozen=True)
class WorkspaceRoot:
    workspace_id: str
    path: Path
    device: int
    inode: int
    group: int | None = None

    @classmethod
    def from_record(
        cls, record: dict[str, Any], *, group: int | None = None
    ) -> "WorkspaceRoot":
        return cls(
            workspace_id=str(record["id"]),
            path=Path(str(record["canonical_root"])),
            device=int(record["root_device"]),
            inode=int(record["root_inode"]),
            group=group,
        )


def _contains(parent: Path, child: Path) -> bool:
    return child == parent or parent in child.parents


def validate_nominated_root(path: Path, *, allow_default: bool = False) -> os.stat_result:
    """Validate one explicit root without changing its existing tree."""
    if not path.is_absolute():
        raise ValidationError("Workspace roots must be absolute.")
    if any(ord(character) < 32 for character in str(path)):
        raise ValidationError("Workspace roots must not contain control characters.")
    try:
        original = path.lstat()
        canonical = path.resolve(strict=True)
    except OSError as exc:
        raise ValidationError("Workspace root does not exist.") from exc
    if stat.S_ISLNK(original.st_mode) or canonical != path:
        raise ValidationError("Workspace root must be canonical and not a symlink.")
    if not stat.S_ISDIR(original.st_mode):
        raise ValidationError("Workspace root must be a directory.")
    if path.is_mount():
        raise ValidationError("A mount point cannot be nominated as a workspace.")
    default = Path("/srv/imaginary-friend/workspace")
    if not (allow_default and path == default):
        if path == Path("/"):
            raise ValidationError("Workspace root overlaps a protected host tree.")
        for forbidden in _FORBIDDEN_ROOTS:
            if _contains(forbidden, path) or _contains(path, forbidden):
                raise ValidationError("Workspace root overlaps a protected host tree.")
    return original


def normalize_relative_path(value: str, *, allow_root: bool = False) -> tuple[str, ...]:
    """Return canonical components for an API-supplied relative path."""
    if not isinstance(value, str):
        raise ValidationError("Workspace paths must be text.")
    if "\x00" in value or any(character in "\r\n" for character in value):
        raise ValidationError("Workspace path contains an invalid character.")
    if value in {"", "."} and allow_root:
        return ()
    if not value or value.startswith("/") or value.endswith("/"):
        raise ValidationError("Workspace path must be a non-empty relative path.")
    raw_parts = value.split("/")
    if any(part in {"", ".", ".."} for part in raw_parts):
        raise ValidationError("Workspace traversal is not allowed.")
    parsed = PurePosixPath(value)
    if parsed.is_absolute() or tuple(parsed.parts) != tuple(raw_parts):
        raise ValidationError("Workspace path is not canonical.")
    return tuple(raw_parts)


def canonical_relative(parts: tuple[str, ...]) -> str:
    return "." if not parts else "/".join(parts)


def _mount_points() -> set[Path]:
    points: set[Path] = set()
    try:
        lines = Path("/proc/self/mountinfo").read_text(
            encoding="utf-8", errors="replace"
        ).splitlines()
    except OSError:
        return points
    for line in lines:
        fields = line.split()
        if len(fields) < 6:
            continue
        value = fields[4]
        for escaped, replacement in (
            ("\\040", " "),
            ("\\011", "\t"),
            ("\\012", "\n"),
            ("\\134", "\\"),
        ):
            value = value.replace(escaped, replacement)
        points.add(Path(value))
    return points


def _ensure_regular(details: os.stat_result, *, root_device: int) -> None:
    if not stat.S_ISREG(details.st_mode):
        raise ValidationError("Workspace operation requires a regular file.")
    if details.st_dev != root_device:
        raise ValidationError("Workspace operation crossed a device boundary.")
    if details.st_nlink != 1:
        raise ValidationError("Hard-linked files are not accepted.")


def _digest_fd(fd: int) -> str:
    digest = hashlib.sha256()
    os.lseek(fd, 0, os.SEEK_SET)
    while True:
        chunk = os.read(fd, 64 * 1024)
        if not chunk:
            break
        digest.update(chunk)
    os.lseek(fd, 0, os.SEEK_SET)
    return f"sha256:{digest.hexdigest()}"


def _rename_noreplace(
    source_parent: int,
    source: str,
    destination_parent: int,
    destination: str,
) -> None:
    """Atomically move one path without replacing a concurrent destination."""
    if _RENAMEAT2 is None:
        raise ValidationError("Atomic no-replace workspace moves are unavailable.")
    result = _RENAMEAT2(
        source_parent,
        os.fsencode(source),
        destination_parent,
        os.fsencode(destination),
        _RENAME_NOREPLACE,
    )
    if result == 0:
        return
    error = ctypes.get_errno()
    if error in {errno.EEXIST, errno.ENOTEMPTY}:
        raise ConflictError("Workspace destination already exists.")
    if error == errno.ENOENT:
        raise NotFoundError("Workspace source does not exist.")
    raise ValidationError("Workspace path could not be moved safely.")


class Workspace:
    """Operate beneath one validated, already-open nominated root."""

    def __init__(self, root: WorkspaceRoot) -> None:
        self.root = root

    @contextmanager
    def _root_fd(self) -> Iterator[int]:
        try:
            fd = os.open(
                self.root.path,
                os.O_RDONLY | _DIRECTORY | _NOFOLLOW | _CLOEXEC,
            )
        except OSError as exc:
            raise ValidationError("Workspace root cannot be opened safely.") from exc
        try:
            details = os.fstat(fd)
            if (
                not stat.S_ISDIR(details.st_mode)
                or details.st_dev != self.root.device
                or details.st_ino != self.root.inode
                or (
                    self.root.group is not None
                    and details.st_gid != self.root.group
                )
                or stat.S_IMODE(details.st_mode) & 0o070 != 0o070
                or not details.st_mode & stat.S_ISGID
            ):
                raise ValidationError(
                    "Workspace root changed after it was nominated."
                )
            yield fd
        finally:
            os.close(fd)

    @contextmanager
    def _directory_fd(
        self, root_fd: int, parts: tuple[str, ...]
    ) -> Iterator[int]:
        current = os.dup(root_fd)
        mount_points = _mount_points()
        try:
            traversed: list[str] = []
            for component in parts:
                traversed.append(component)
                visible_path = self.root.path.joinpath(*traversed)
                if visible_path in mount_points:
                    raise ValidationError(
                        "Workspace operation crossed a mount boundary."
                    )
                try:
                    next_fd = os.open(
                        component,
                        os.O_RDONLY | _DIRECTORY | _NOFOLLOW | _CLOEXEC,
                        dir_fd=current,
                    )
                except FileNotFoundError as exc:
                    raise NotFoundError("Workspace directory does not exist.") from exc
                except OSError as exc:
                    raise ValidationError(
                        "Workspace directory cannot be opened safely."
                    ) from exc
                details = os.fstat(next_fd)
                if (
                    not stat.S_ISDIR(details.st_mode)
                    or details.st_dev != self.root.device
                ):
                    os.close(next_fd)
                    raise ValidationError(
                        "Workspace operation crossed a device boundary."
                    )
                os.close(current)
                current = next_fd
            yield current
        finally:
            os.close(current)

    @staticmethod
    def _require_shared_parent(root_fd: int, parent_fd: int) -> None:
        root = os.fstat(root_fd)
        parent = os.fstat(parent_fd)
        if (
            parent.st_gid != root.st_gid
            or stat.S_IMODE(parent.st_mode) & 0o070 != 0o070
            or not parent.st_mode & stat.S_ISGID
        ):
            raise ValidationError(
                "Workspace parent must preserve friend-share group inheritance."
            )

    def list(self, relative_path: str = ".") -> dict[str, Any]:
        parts = normalize_relative_path(relative_path, allow_root=True)
        with self._root_fd() as root_fd, self._directory_fd(root_fd, parts) as fd:
            entries: list[dict[str, Any]] = []
            for name in sorted(os.listdir(fd)):
                try:
                    details = os.stat(name, dir_fd=fd, follow_symlinks=False)
                except OSError:
                    continue
                if stat.S_ISLNK(details.st_mode):
                    entry_type = "blocked-link"
                elif details.st_dev != self.root.device:
                    entry_type = "blocked-device"
                elif stat.S_ISDIR(details.st_mode):
                    entry_type = "directory"
                elif stat.S_ISREG(details.st_mode) and details.st_nlink == 1:
                    entry_type = "file"
                else:
                    entry_type = "blocked-special"
                entries.append(
                    {
                        "name": name,
                        "type": entry_type,
                        "size": details.st_size if entry_type == "file" else None,
                        "modified_at": details.st_mtime,
                    }
                )
        return {"path": canonical_relative(parts), "entries": entries}

    def read(self, relative_path: str) -> dict[str, Any]:
        parts = normalize_relative_path(relative_path)
        with self._root_fd() as root_fd, self._directory_fd(
            root_fd, parts[:-1]
        ) as parent_fd:
            try:
                fd = os.open(
                    parts[-1], os.O_RDONLY | _NOFOLLOW | _CLOEXEC, dir_fd=parent_fd
                )
            except FileNotFoundError as exc:
                raise NotFoundError("Workspace file does not exist.") from exc
            except OSError as exc:
                raise ValidationError("Workspace file cannot be opened safely.") from exc
            try:
                details = os.fstat(fd)
                _ensure_regular(details, root_device=self.root.device)
                if details.st_size > MAX_FILE_BYTES:
                    raise ValidationError("Workspace file exceeds the one MiB limit.")
                chunks: list[bytes] = []
                remaining = MAX_FILE_BYTES + 1
                while remaining:
                    chunk = os.read(fd, min(64 * 1024, remaining))
                    if not chunk:
                        break
                    chunks.append(chunk)
                    remaining -= len(chunk)
                content_bytes = b"".join(chunks)
                if len(content_bytes) > MAX_FILE_BYTES:
                    raise ValidationError("Workspace file exceeds the one MiB limit.")
                try:
                    content = content_bytes.decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise ValidationError(
                        "First-release workspace reads require UTF-8 text."
                    ) from exc
            finally:
                os.close(fd)
        return {
            "path": canonical_relative(parts),
            "content": content,
            "sha256": f"sha256:{hashlib.sha256(content_bytes).hexdigest()}",
            "modified_at": details.st_mtime,
        }

    def write(
        self,
        relative_path: str,
        content: str,
        *,
        expected_sha256: str | None = None,
    ) -> dict[str, Any]:
        parts = normalize_relative_path(relative_path)
        if not isinstance(content, str):
            raise ValidationError("Workspace file content must be UTF-8 text.")
        encoded = content.encode("utf-8")
        if len(encoded) > MAX_FILE_BYTES:
            raise ValidationError("Workspace write exceeds the one MiB limit.")
        replacing = False
        original_identity: tuple[int, int, int, int] | None = None
        with self._root_fd() as root_fd, self._directory_fd(
            root_fd, parts[:-1]
        ) as parent_fd:
            self._require_shared_parent(root_fd, parent_fd)
            try:
                existing_fd = os.open(
                    parts[-1], os.O_RDONLY | _NOFOLLOW | _CLOEXEC, dir_fd=parent_fd
                )
            except FileNotFoundError:
                if expected_sha256 is not None:
                    raise ConflictError("The expected workspace file no longer exists.")
            except OSError as exc:
                raise ValidationError("Workspace target cannot be opened safely.") from exc
            else:
                try:
                    details = os.fstat(existing_fd)
                    _ensure_regular(details, root_device=self.root.device)
                    replacing = True
                    if expected_sha256 is None:
                        raise ConflictError(
                            "Replacing a file requires its current SHA-256 digest."
                        )
                    if _digest_fd(existing_fd) != expected_sha256:
                        raise ConflictError("Workspace file changed before this write.")
                    original_identity = (
                        details.st_dev,
                        details.st_ino,
                        details.st_size,
                        details.st_mtime_ns,
                    )
                finally:
                    os.close(existing_fd)
            temporary = f".friend-{uuid.uuid4().hex}.tmp"
            temp_fd = os.open(
                temporary,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | _NOFOLLOW | _CLOEXEC,
                0o660,
                dir_fd=parent_fd,
            )
            try:
                view = memoryview(encoded)
                while view:
                    written = os.write(temp_fd, view)
                    view = view[written:]
                os.fchmod(temp_fd, 0o660)
                os.fsync(temp_fd)
            except Exception:
                os.close(temp_fd)
                os.unlink(temporary, dir_fd=parent_fd)
                raise
            else:
                os.close(temp_fd)
            try:
                if replacing and original_identity is not None:
                    current = os.stat(
                        parts[-1], dir_fd=parent_fd, follow_symlinks=False
                    )
                    identity = (
                        current.st_dev,
                        current.st_ino,
                        current.st_size,
                        current.st_mtime_ns,
                    )
                    if identity != original_identity:
                        raise ConflictError("Workspace file changed before commit.")
                elif not replacing:
                    try:
                        os.stat(parts[-1], dir_fd=parent_fd, follow_symlinks=False)
                    except FileNotFoundError:
                        pass
                    else:
                        raise ConflictError("Workspace target was created concurrently.")
                os.replace(
                    temporary,
                    parts[-1],
                    src_dir_fd=parent_fd,
                    dst_dir_fd=parent_fd,
                )
                os.fsync(parent_fd)
            except Exception:
                try:
                    os.unlink(temporary, dir_fd=parent_fd)
                except FileNotFoundError:
                    pass
                raise
        return {
            "path": canonical_relative(parts),
            "sha256": f"sha256:{hashlib.sha256(encoded).hexdigest()}",
            "bytes": len(encoded),
            "created": not replacing,
        }

    def mkdir(self, relative_path: str) -> dict[str, Any]:
        parts = normalize_relative_path(relative_path)
        with self._root_fd() as root_fd, self._directory_fd(
            root_fd, parts[:-1]
        ) as parent_fd:
            self._require_shared_parent(root_fd, parent_fd)
            try:
                os.mkdir(parts[-1], 0o2770, dir_fd=parent_fd)
            except FileExistsError as exc:
                raise ConflictError("Workspace directory already exists.") from exc
            directory_fd = os.open(
                parts[-1],
                os.O_RDONLY | _DIRECTORY | _NOFOLLOW | _CLOEXEC,
                dir_fd=parent_fd,
            )
            try:
                os.fchmod(directory_fd, 0o2770)
                os.fsync(parent_fd)
            finally:
                os.close(directory_fd)
        return {"path": canonical_relative(parts), "created": True}

    def move(self, source: str, destination: str) -> dict[str, Any]:
        source_parts = normalize_relative_path(source)
        destination_parts = normalize_relative_path(destination)
        with self._root_fd() as root_fd, self._directory_fd(
            root_fd, source_parts[:-1]
        ) as source_parent, self._directory_fd(
            root_fd, destination_parts[:-1]
        ) as destination_parent:
            self._require_shared_parent(root_fd, destination_parent)
            try:
                details = os.stat(
                    source_parts[-1],
                    dir_fd=source_parent,
                    follow_symlinks=False,
                )
            except FileNotFoundError as exc:
                raise NotFoundError("Workspace source does not exist.") from exc
            if details.st_dev != self.root.device or stat.S_ISLNK(details.st_mode):
                raise ValidationError("Workspace source is outside the safe boundary.")
            if stat.S_ISREG(details.st_mode) and details.st_nlink != 1:
                raise ValidationError("Hard-linked files are not accepted.")
            if not stat.S_ISREG(details.st_mode) and not stat.S_ISDIR(details.st_mode):
                raise ValidationError("Workspace source has an unsupported type.")
            _rename_noreplace(
                source_parent,
                source_parts[-1],
                destination_parent,
                destination_parts[-1],
            )
            os.fsync(source_parent)
            if source_parent != destination_parent:
                os.fsync(destination_parent)
        return {
            "source": canonical_relative(source_parts),
            "destination": canonical_relative(destination_parts),
        }

    def delete(self, relative_path: str) -> dict[str, Any]:
        parts = normalize_relative_path(relative_path)
        with self._root_fd() as root_fd, self._directory_fd(
            root_fd, parts[:-1]
        ) as parent_fd:
            try:
                details = os.stat(
                    parts[-1], dir_fd=parent_fd, follow_symlinks=False
                )
            except FileNotFoundError as exc:
                raise NotFoundError("Workspace target does not exist.") from exc
            if details.st_dev != self.root.device or stat.S_ISLNK(details.st_mode):
                raise ValidationError("Workspace target is outside the safe boundary.")
            if stat.S_ISREG(details.st_mode):
                _ensure_regular(details, root_device=self.root.device)
                os.unlink(parts[-1], dir_fd=parent_fd)
                target_type = "file"
            elif stat.S_ISDIR(details.st_mode):
                try:
                    os.rmdir(parts[-1], dir_fd=parent_fd)
                except OSError as exc:
                    raise ConflictError(
                        "Only an empty workspace directory can be removed."
                    ) from exc
                target_type = "directory"
            else:
                raise ValidationError("Workspace target has an unsupported type.")
            os.fsync(parent_fd)
        return {"path": canonical_relative(parts), "deleted": target_type}
