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

TODO: `--make-sandbox`
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
import sys
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Generator, Iterator, List, NoReturn, Optional, Union


PathLike = Union[str, Path]
Filter = Callable[[Path], bool]


def main_execute(cmdstr: str, *, directory: Optional[str]) -> None:
    parsed_cmd = parse_command(cmdstr)

    bop = BatchOp(root=directory)
    if parsed_cmd.command == "delete":
        bop.delete(parsed_cmd.fileset)
    else:
        err_unknown_command(parsed_cmd.command)


@dataclass
class ParsedCommand:
    command: str
    fileset: "FileSet"


def parse_command(cmdstr: str) -> ParsedCommand:
    # delete non-empty folders
    # delete folders that are not empty
    # delete folders that are non-empty

    fs = FileSet()

    tkniter = tokenize(cmdstr)
    command = next(tkniter)

    if command == "delete":
        return parse_delete_command(tkniter)
    else:
        err_unknown_command(command)


Tokenizer = Iterator[str]


def parse_delete_command(tkniter: Tokenizer) -> ParsedCommand:
    # Examples:
    #   delete non-empty folders
    #   delete folders that are non-empty and
    #   delete anything ending with '.o'
    #
    # Syntax:
    #   DELETE np pred*

    fs = FileSet()
    fs = parse_np(tkniter, fs)

    while True:
        opt = parse_pred(tkniter, fs)
        if opt is None:
            break
        else:
            fs = opt

    ensure_end_of_tokens(tkniter)
    return ParsedCommand(command="delete", fileset=fs)


def parse_np(tkniter: Tokenizer, fs: "FileSet") -> "FileSet":
    tkn = next(tkniter)

    # TODO: parse adjectival modifiers (e.g., 'non-empty')
    if tkn == "anything" or tkn == "everything":
        return fs
    elif tkn == "files":
        return fs.is_file()
    elif tkn == "folders":
        return fs.is_folder()
    else:
        err_unknown_word(tkn)


def parse_pred(tkniter: Tokenizer, fs: "FileSet") -> Optional["FileSet"]:
    try:
        tkn = next(tkniter)
    except StopIteration:
        return None

    if tkn == "that":
        tkn = next(tkniter)

    if tkn == "is":
        tkn = next(tkniter)
        if tkn == "a" or tkn == "an":
            tkn = next(tkniter)

        if tkn == "file":
            return fs.is_file()
        elif tkn == "folder":
            return fs.is_folder()
        else:
            err_unknown_word(tkn)
    else:
        err_unknown_word(tkn)


def tokenize(cmdstr: str) -> Generator[str, None, None]:
    # TODO: more sophisticated tokenization
    for word in cmdstr.split():
        yield word.lower()


def ensure_end_of_tokens(tkniter: Tokenizer) -> None:
    try:
        next(tkniter)
    except StopIteration:
        return
    else:
        # TODO: better error message
        raise BatchOpSyntaxError("trailing input")


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
            err_unknown_command(cmd)
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


def err_unknown_word(word: str) -> NoReturn:
    raise BatchOpSyntaxError(f"unknown word: {word!r}")


def err_unknown_command(cmd: str) -> NoReturn:
    raise BatchOpSyntaxError(f"unknown command: {cmd!r}")


class TestCommandParsing(unittest.TestCase):
    def test_delete_command(self):
        cmd = parse_command("delete everything")
        self.assertEqual(cmd.command, "delete")
        self.assertEqual(len(cmd.fileset.filters), 0)

        cmd = parse_command("delete anything that is a file")
        self.assertEqual(cmd.command, "delete")
        # TODO: assert on type of filter
        self.assertEqual(len(cmd.fileset.filters), 1)

        cmd = parse_command("delete folders")
        self.assertEqual(cmd.command, "delete")
        # TODO: assert on type of filter
        self.assertEqual(len(cmd.fileset.filters), 1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--directory")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("words", nargs="*")
    args = parser.parse_args()

    if args.self_test:
        unittest.main(argv=[sys.argv[0]])
    else:
        if len(args.words) > 0:
            cmdstr = " ".join(args.words)
            main_execute(cmdstr, directory=args.directory)
        else:
            main_interactive(args.directory)
