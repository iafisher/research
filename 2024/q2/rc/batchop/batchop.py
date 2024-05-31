"""
Supported operations:

- delete <fileset>
- rename <pattern1> <pattern2>
- move <fileset> <destination>
- list <fileset>
- replace <pattern1> <pattern2> <fileset>
- run <cmd> <fileset>

Python interface:

    bop = BatchOp()
    bop.delete(FileSet().is_empty().is_folder().is_named("Archive"))

Command-line interface:

    $ batchop 'delete all folders named "Archive" that are not empty'
    $ batchop 'rename %_trip.jpg to %.jpg'

Interactive interface:

    $ batchop
    671 files, 17 folders
    > is a file
    671 files
    > ends with .md
    534 files
    > move to markdown-files

TODO: `rename` command (needs design)
TODO: human-readable parser (needs design)
TODO: gitignore support
TODO: `move` command
TODO: `replace` command
TODO: `run` command
TODO: profiling + optimization

"""

import argparse
import fnmatch
import functools
import subprocess
from pathlib import Path
from typing import Callable, Generator, List, Optional, Union


PathLike = Union[str, Path]
Filter = Callable[[Path], bool]


def main_interactive(d: Optional[str]) -> None:
    root = path_or_default(d)

    fs = FileSet()
    while True:
        # TODO: separate counts for files and directories
        # TODO: default to ignoring .git + .gitignore?
        n = sum(1 for _ in fs.resolve(root))
        print(f"{plural(n, 'file')}")

        try:
            s = input("> ").strip()
        except BatchOpSyntaxError as e:
            print(f"error: {e}")
            continue
        except EOFError:
            print()
            break

        if not s:
            continue

        fs = parse_filter(fs, s)


def make_filter(f: Filter):
    @functools.wraps(f)
    def inner(self) -> "FileSet":
        self.filters.append(f)
        return self

    return inner


class FileSet:
    filters: List[Filter]

    def __init__(self) -> None:
        self.filters = []

    def resolve(self, root: Path) -> Generator[Path, None, None]:
        ps = root.glob("**/*")
        for p in ps:
            if all(f(p) for f in self.filters):
                yield p

    def pop(self) -> None:
        self.filters.pop()

    def clear(self) -> None:
        self.filters.clear()

    @make_filter
    def is_folder(p: Path) -> bool:
        return p.is_dir()

    @make_filter
    def is_file(p: Path) -> bool:
        return p.is_file()

    @make_filter
    def is_empty(p: Path) -> bool:
        # TODO: ignore files or filter them out?
        # TODO: more efficient way to check if directory is empty
        return not p.is_dir() or not list(p.glob("*"))

    @make_filter
    def is_named(p: Path) -> bool:
        # TODO: case-insensitive file systems?
        return fnmatch.fnmatch(p.name, pat)

    @make_filter
    def is_not_named(p: Path) -> bool:
        return not fnmatch.fnmatch(p.name, pat)

    @make_filter
    def is_not_in(p: Path) -> bool:
        # TODO: messy
        return not (p.is_dir() and fnmatch.fnmatch(p.name, pat)) and all(
            not fnmatch.fnmatch(s, pat) for s in p.parts[:-1]
        )

    @make_filter
    def is_not_hidden(p: Path) -> bool:
        # TODO: cross-platform?
        return all(not s.startswith(".") for s in p.parts)

    # TODO: is_not_git_ignored() -- https://github.com/mherrmann/gitignore_parser


def parse_filter(fs: FileSet, line: str) -> FileSet:
    # TODO: structural parsing
    # TODO: handle commands (delete, rename, etc.)

    line = line.strip().lower()
    if line == "is a file" or line == "is file":
        return fs.is_file()
    elif line == "is a folder" or line == "is folder":
        return fs.is_folder()
    elif line == "is not hidden":
        return fs.is_not_hidden()
    elif line.startswith("!"):
        cmd = line[1:]
        if cmd == "pop":
            fs.pop()
            return fs
        elif cmd == "clear":
            fs.clear()
            return fs
        else:
            raise BatchOpSyntaxError("unknown command")
    else:
        raise BatchOpSyntaxError("could not parse")


class BatchOp:
    def __init__(self, root: Optional[PathLike]) -> None:
        self.root = path_or_default(root)

    def list(self, fileset: FileSet) -> Generator[Path, None, None]:
        yield from list(fileset.resolve(self.root))

    def delete(self, fileset: FileSet) -> None:
        # TODO: don't remove files that are in a directory that will be removed
        # TODO: don't use -rf except for directories
        # TODO: pass paths to `rm` in batches
        for p in fileset.resolve(self.root):
            sh(["rm", "-rf", str(p)])


def sh(args: List[str]) -> None:
    subprocess.run(args, capture_output=True, check=True)


def path_or_default(p: Optional[PathLike]) -> Path:
    if p is None:
        r = Path(".")
    elif isinstance(p, Path):
        r = p
    else:
        r = Path(p)

    return r.absolute()


def plural(n: int, s: str) -> str:
    return f"{n} {s}" if n == 1 else f"{n} {s}s"


class BatchOpSyntaxError(Exception):
    pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--directory")
    args = parser.parse_args()

    main_interactive(args.directory)
