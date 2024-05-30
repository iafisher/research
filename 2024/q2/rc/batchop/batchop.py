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

"""

import fnmatch
import subprocess
from pathlib import Path
from typing import Callable, Generator, List, Optional, Union


PathLike = Union[str, Path]
Filter = Callable[[Path], bool]


class FileSet:
    filters: List[Filter]

    def __init__(self) -> None:
        self.filters = []

    def resolve(self, root: Path) -> Generator[Path, None, None]:
        ps = root.glob("**/*")
        for p in ps:
            if all(f(p) for f in self.filters):
                yield p

    def is_folder(self) -> "FileSet":
        def f(p: Path) -> bool:
            return p.is_dir()

        self.filters.append(f)
        return self

    def is_empty(self) -> "FileSet":
        def f(p: Path) -> bool:
            # TODO: ignore files or filter them out?
            # TODO: more efficient way to check if directory is empty
            return not p.is_dir() or not list(p.glob("*"))

        self.filters.append(f)
        return self

    def is_named(self, pat: str) -> "FileSet":
        def f(p: Path) -> bool:
            # TODO: case-insensitive file systems?
            return fnmatch.fnmatch(p.name, pat)

        self.filters.append(f)
        return self

    def is_not_named(self, pat: str) -> "FileSet":
        def f(p: Path) -> bool:
            return not fnmatch.fnmatch(p.name, pat)

        self.filters.append(f)
        return self

    def is_not_in(self, pat: str) -> "FileSet":
        def f(p: Path) -> bool:
            # TODO: messy
            return not (p.is_dir() and fnmatch.fnmatch(p.name, pat)) and all(
                not fnmatch.fnmatch(s, pat) for s in p.parts[:-1]
            )

        self.filters.append(f)
        return self

    def is_not_hidden(self) -> "FileSet":
        def f(p: Path) -> bool:
            # TODO: cross-platform?
            return all(not s.startswith(".") for s in p.parts)

        self.filters.append(f)
        return self

    # TODO: is_not_git_ignored()


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


b = BatchOp()
for p in b.list(FileSet().is_folder().is_empty()):
    print(p)
