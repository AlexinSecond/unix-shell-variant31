"""JSON-backed filesystem with all ordinary operations in memory."""

import base64
import binascii
import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Node:
    """Represent a directory or a file with bytes, without host files."""

    kind: str
    children: dict[str, "Node"] = field(default_factory=dict)
    content: bytes = b""
    mtime_ns: int = 0


def decode_file(data: dict) -> bytes:
    """Decode UTF-8 or strictly validated base64 file content."""
    content = data.get("content")
    encoding = data.get("encoding", "utf-8")
    if not isinstance(content, str):
        raise ValueError("file content must be a string")
    if encoding == "utf-8":
        return content.encode("utf-8")
    if encoding == "base64":
        try:
            return base64.b64decode(content, validate=True)
        except (ValueError, binascii.Error) as error:
            raise ValueError("invalid base64 content") from error
    raise ValueError(f"unsupported file encoding: {encoding}")


def validate_name(name: str) -> None:
    """Reject names that would corrupt the portable virtual path tree."""
    if not name or name in {".", ".."} or "/" in name or "\\" in name:
        raise ValueError(f"invalid VFS name: {name!r}")
    if "\x00" in name:
        raise ValueError("VFS names cannot contain NUL")


def expand_path(path: str, cwd: str) -> str:
    """Expand the virtual home and make a path absolute without collapsing."""
    if path == "~":
        path = "/"
    elif path.startswith("~/"):
        path = "/" + path[2:]
    return path if path.startswith("/") else cwd + "/" + path


def decode_node(data: object) -> Node:
    """Validate and recursively build a tree from the JSON schema."""
    if not isinstance(data, dict):
        raise ValueError("every VFS node must be an object")
    kind = data.get("type")
    if kind == "file":
        return Node("file", content=decode_file(data))
    if kind != "dir":
        raise ValueError("node type must be dir or file")
    children = data.get("children")
    if not isinstance(children, dict):
        raise ValueError("directory children must be an object")
    node = Node("dir")
    for name, child in children.items():
        validate_name(name)
        node.children[name] = decode_node(child)
    return node


class VirtualFileSystem:
    """Own a root tree and resolve POSIX paths independently of the OS."""

    def __init__(self, root: Node | None = None):
        """Use an empty directory as the default filesystem."""
        self.root = root if root is not None else Node("dir")
        if self.root.kind != "dir":
            raise ValueError("the VFS root must be a directory")

    @classmethod
    def load(cls, path: Path) -> "VirtualFileSystem":
        """Read a JSON source once, without extraction or modification."""
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            return cls(decode_node(data))
        except RecursionError as error:
            raise ValueError("VFS nesting is too deep") from error

    def resolve(self, path: str, cwd: str = "/") -> tuple[str, Node]:
        """Resolve ~, ., .. and check every traversed directory."""
        full = expand_path(path, cwd)
        names: list[str] = []
        stack = [self.root]
        for part in full.split("/"):
            if not part:
                continue
            if stack[-1].kind != "dir":
                raise ValueError(f"{path}: Not a directory")
            if part == ".":
                continue
            if part == "..":
                if names:
                    names.pop()
                    stack.pop()
                continue
            if part not in stack[-1].children:
                raise ValueError(f"{path}: No such file or directory")
            names.append(part)
            stack.append(stack[-1].children[part])
        if path.endswith("/") and stack[-1].kind != "dir":
            raise ValueError(f"{path}: Not a directory")
        return "/" + "/".join(names), stack[-1]

    def reset(self, path: Path) -> None:
        """Clear the physical JSON source, then replace the in-memory VFS."""
        data = {"type": "dir", "children": {}}
        path.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8"
        )
        self.root = Node("dir")
