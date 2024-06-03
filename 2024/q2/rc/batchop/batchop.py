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

import abc
import argparse
import dataclasses
import decimal
import fnmatch
import subprocess
import sys
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Generator, Iterator, List, NoReturn, Optional, Union


PathLike = Union[str, Path]


class Filter(abc.ABC):
    @abc.abstractmethod
    def test(self, p: Path) -> bool:
        pass


def main_execute(cmdstr: str, *, directory: Optional[str]) -> None:
    parsed_cmd = parse_command(cmdstr)

    bop = BatchOp(root=directory)
    fileset = FileSet(parsed_cmd.filters)
    if parsed_cmd.command == "delete":
        bop.delete(fileset)
    elif parsed_cmd.command == "list":
        for p in bop.list(fileset):
            print(p)
    else:
        err_unknown_command(parsed_cmd.command)


@dataclass
class ParsedCommand:
    command: str
    filters: List[Filter]


def parse_command(cmdstr: str) -> ParsedCommand:
    # delete non-empty folders
    # delete folders that are not empty
    # delete folders that are non-empty

    tokens = tokenize(cmdstr)
    if len(tokens) == 0:
        err_empty_input()

    command = tokens.pop(0).lower()

    if command == "delete":
        filters = parse_np_and_preds(tokens)
        return ParsedCommand(command=command, filters=filters)
    elif command == "list":
        filters = parse_np_and_preds(tokens)
        return ParsedCommand(command=command, filters=filters)
    else:
        err_unknown_command(command)


Tokenizer = Iterator[str]


def parse_np_and_preds(tokens: List[str]) -> List[Filter]:
    filters = parse_np(tokens)

    i = 0
    while i < len(tokens):
        matched_one = False
        for pattern, filter_constructor in PATTERNS:
            m = try_phrase_match(pattern, tokens[i:])
            if m is not None:
                i += m.tokens_consumed
                if filter_constructor is not None:
                    f = filter_constructor(*m.captures)
                    if m.negated:
                        f = FilterNegated(f)

                    filters.append(f)

                matched_one = True
                break

        if not matched_one:
            # TODO: more helpful message
            raise BatchOpSyntaxError("could not parse")

    return filters


def parse_np(tokens: List[str]) -> List[Filter]:
    if len(tokens) == 0:
        err_empty_input()

    tkn = tokens.pop(0)

    # TODO: parse adjectival modifiers (e.g., 'non-empty')
    if tkn == "anything" or tkn == "everything":
        return []
    elif tkn == "files":
        return [FilterIsFile()]
    elif tkn == "folders":
        return [FilterIsFolder()]
    else:
        err_unknown_word(tkn)


@dataclass
class WordMatch:
    captured: Optional[Any]
    consumed: bool = True
    negated: bool = False


class BasePattern(abc.ABC):
    @abc.abstractmethod
    def test(self, token: str) -> Optional[WordMatch]:
        pass


@dataclass
class POpt(BasePattern):
    pattern: BasePattern

    def test(self, token: str) -> Optional[WordMatch]:
        m = self.pattern.test(token)
        if m is not None:
            return m
        else:
            return WordMatch(captured=None, consumed=False)


@dataclass
class PLit(BasePattern):
    literal: str
    case_sensitive: bool = False
    captures: bool = False

    def test(self, token: str) -> Optional[WordMatch]:
        if self.case_sensitive:
            matches = token == self.literal
        else:
            matches = token.lower() == self.literal.lower()

        if matches:
            captured = token if self.captures else None
            return WordMatch(captured=captured)
        else:
            return None


@dataclass
class PNot(BasePattern):
    def test(self, token: str) -> Optional[WordMatch]:
        if token.lower() == "not":
            return WordMatch(captured=None, negated=True)
        else:
            return WordMatch(captured=None, consumed=False)


@dataclass
class PDecimal(BasePattern):
    def test(self, token: str) -> Optional[WordMatch]:
        try:
            captured = decimal.Decimal(token)
        except decimal.InvalidOperation:
            return None
        else:
            return WordMatch(captured=captured)


@dataclass
class PInt(BasePattern):
    def test(self, token: str) -> Optional[WordMatch]:
        try:
            captured = int(token, base=0)
        except ValueError:
            return None
        else:
            return WordMatch(captured=captured)


@dataclass
class PString(BasePattern):
    def test(self, token: str) -> Optional[WordMatch]:
        if token != "":
            return WordMatch(captured=token)
        else:
            return None


@dataclass
class PSizeUnit(BasePattern):
    def test(self, token: str) -> Optional[WordMatch]:
        token_lower = token.lower()
        if token_lower in ("b", "byte", "bytes"):
            captured = 1
        elif token_lower in ("kb", "kilobyte", "kilobytes"):
            captured = 1_000
        elif token_lower in ("mb", "megabyte", "megabytes"):
            captured = 1_000_000
        elif token_lower in ("gb", "gigabyte", "gigabytes"):
            captured = 1_000_000_000
        else:
            return None

        return WordMatch(captured=captured)


@dataclass
class PhraseMatch:
    captures: List[Any]
    negated: bool
    tokens_consumed: int


def try_phrase_match(
    patterns: List[BasePattern], tokens: List[str]
) -> Optional[PhraseMatch]:
    captures = []
    negated = False
    i = 0

    for pattern in patterns:
        if i >= len(tokens):
            # in case patterns ends with optional patterns
            token = ""
        else:
            token = tokens[i]

        m = pattern.test(token)
        if m is not None:
            if m.consumed:
                i += 1

            if m.captured is not None:
                captures.append(m.captured)

            if m.negated:
                if negated:
                    raise BatchOpImpossibleError(
                        "multiple negations in the same pattern"
                    )

                negated = True
        else:
            return None

    return PhraseMatch(captures=captures, negated=negated, tokens_consumed=i)


# PATTERNS = [
#     # that? is a? NOT file
#     # that? is a? NOT folder
#     # > INT SIZE
#     # >= INT SIZE
#     # < INT SIZE
#     # <= INT SIZE
#     # that? is NOT empty
#     # that? is? NOT named PAT
#     # that? is NOT in PAT
#     # that? is NOT hidden
#     # with ext|extension STR
#     [POpt(PLit("that")), PLit("is"), POpt(PLit("a")), PLit("file")],
#     [POpt(PLit("that")), PLit("is"), POpt(PLit("a")), PLit("folder")],
#     [PLit(">"), PDecimal(), PSizeUnit()],
#     [PLit(">="), PDecimal(), PSizeUnit()],
#     [PLit("<"), PDecimal(), PSizeUnit()],
#     [PLit("<="), PDecimal(), PSizeUnit()],
# ]


def parse_pred(tkniter: Tokenizer) -> List[Filter]:
    try:
        tkn = next(tkniter)
    except StopIteration:
        return []

    if tkn == "that":
        tkn = next(tkniter)

    if tkn == "is" or tkn == "are":
        tkn = next(tkniter)
        if tkn == "a" or tkn == "an":
            tkn = next(tkniter)

        if tkn == "not":
            negated = True
            tkn = next(tkniter)
        else:
            negated = False

        f: Filter
        if tkn == "file":
            f = FilterIsFile()
        elif tkn == "folder":
            f = FilterIsFolder()
        elif tkn == "empty":
            f = FilterIsEmpty()
        else:
            err_unknown_word(tkn)

        if negated:
            return [FilterNegated(f)]
        else:
            return [f]
    else:
        err_unknown_word(tkn)


def tokenize(cmdstr: str) -> List[str]:
    # TODO: more sophisticated tokenization
    return cmdstr.split()


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


@dataclass
class FileSet:
    filters: List[Filter] = dataclasses.field(default_factory=list)

    def resolve(self, root: Path) -> Generator[Path, None, None]:
        ps = root.glob("**/*")
        for p in ps:
            if all(f.test(p) for f in self.filters):
                yield p

    def pop(self) -> None:
        self.filters.pop()

    def clear(self) -> None:
        self.filters.clear()

    def is_folder(self) -> "FileSet":
        self.filters.append(FilterIsFolder())
        return self

    def is_file(self) -> "FileSet":
        self.filters.append(FilterIsFile())
        return self

    def is_empty(self) -> "FileSet":
        self.filters.append(FilterIsEmpty())
        return self

    def is_named(self, pattern: str) -> "FileSet":
        self.filters.append(FilterIsNamed(pattern))
        return self

    def is_not_named(self, pattern: str) -> "FileSet":
        self.filters.append(FilterNegated(FilterIsNamed(pattern)))
        return self

    def is_not_in(self, pattern: str) -> "FileSet":
        self.filters.append(FilterIsNotIn(pattern))
        return self

    def is_not_hidden(self) -> "FileSet":
        self.filters.append(FilterIsNotHidden())
        return self

    # TODO: is_not_git_ignored() -- https://github.com/mherrmann/gitignore_parser


@dataclass
class FilterNegated(Filter):
    inner: Filter

    def test(self, p: Path) -> bool:
        return not self.inner.test(p)


@dataclass
class FilterIsFolder(Filter):
    def test(self, p: Path) -> bool:
        return p.is_dir()


@dataclass
class FilterIsFile(Filter):
    def test(self, p: Path) -> bool:
        return p.is_file()


@dataclass
class FilterIsEmpty(Filter):
    def test(self, p: Path) -> bool:
        # TODO: ignore files or filter them out?
        # TODO: more efficient way to check if directory is empty
        return not p.is_dir() or not list(p.glob("*"))


@dataclass
class FilterIsNamed(Filter):
    pattern: str

    def test(self, p: Path) -> bool:
        # TODO: case-insensitive file systems?
        return fnmatch.fnmatch(p.name, self.pattern)


@dataclass
class FilterIsNotIn(Filter):
    pattern: str

    def test(self, p: Path) -> bool:
        # TODO: messy
        return not (p.is_dir() and fnmatch.fnmatch(p.name, self.pattern)) and all(
            not fnmatch.fnmatch(s, self.pattern) for s in p.parts[:-1]
        )


@dataclass
class FilterIsNotHidden(Filter):
    def test(self, p: Path) -> bool:
        # TODO: cross-platform?
        return all(not s.startswith(".") for s in p.parts)


def parse_filter(fs: FileSet, line: str) -> FileSet:
    # TODO: structural parsing
    # TODO: handle commands (delete, rename, etc.)
    # TODO: unify with parse_command

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

    return r


def plural(n: int, s: str) -> str:
    return f"{n} {s}" if n == 1 else f"{n} {s}s"


class BatchOpError(Exception):
    pass


class BatchOpSyntaxError(BatchOpError):
    pass


class BatchOpImpossibleError(BatchOpError):
    pass


def err_unknown_word(word: str) -> NoReturn:
    raise BatchOpSyntaxError(f"unknown word: {word!r}")


def err_unknown_command(cmd: str) -> NoReturn:
    raise BatchOpSyntaxError(f"unknown command: {cmd!r}")


def err_empty_input() -> NoReturn:
    raise BatchOpSyntaxError("empty input")


PATTERNS = [
    (
        [POpt(PLit("that")), PLit("is"), PNot(), POpt(PLit("a")), PLit("file")],
        FilterIsFile,
    ),
    (
        [POpt(PLit("that")), PLit("is"), PNot(), POpt(PLit("a")), PLit("folder")],
        FilterIsFolder,
    ),
]


class TestCommandParsing(unittest.TestCase):
    def test_delete_command(self):
        cmd = parse_command("delete everything")
        self.assertEqual(cmd.command, "delete")
        self.assertEqual(cmd.filters, [])

        cmd = parse_command("delete anything that is a file")
        self.assertEqual(cmd.command, "delete")
        self.assertEqual(cmd.filters, [FilterIsFile()])

        cmd = parse_command("delete folders")
        self.assertEqual(cmd.command, "delete")
        self.assertEqual(cmd.filters, [FilterIsFolder()])


class TestPatternMatching(unittest.TestCase):
    def test_match_literal(self):
        pattern = [PLit("is")]
        m = try_phrase_match(pattern, ["is"])
        self.assert_match(m)

        m = try_phrase_match(pattern, ["are"])
        self.assert_no_match(m)

    def test_match_optional(self):
        pattern = [POpt(PLit("an"))]
        m = try_phrase_match(pattern, ["folder"])
        self.assert_match(m)

        m = try_phrase_match(pattern, ["an"])
        self.assert_match(m)

        m = try_phrase_match(pattern, [])
        self.assert_match(m)

    def test_match_complex(self):
        pattern = [POpt(PLit("is")), PNot(), PDecimal(), PSizeUnit()]
        m = try_phrase_match(pattern, ["is", "10.7", "gigabytes"])
        self.assert_match(m, [decimal.Decimal("10.7"), 1_000_000_000])

        m = try_phrase_match(pattern, ["10.7", "gigabytes"])
        self.assert_match(m, [decimal.Decimal("10.7"), 1_000_000_000])

        m = try_phrase_match(pattern, ["is", "not", "2.1", "mb"])
        self.assert_match(m, [decimal.Decimal("2.1"), 1_000_000], negated=True)

        m = try_phrase_match(pattern, ["not", "2.1", "mb"])
        self.assert_match(m, [decimal.Decimal("2.1"), 1_000_000], negated=True)

    def assert_match(
        self, m: PhraseMatch, captures: List[Any] = [], negated: bool = False
    ) -> None:
        self.assertIsNotNone(m)
        self.assertEqual(m.captures, captures)
        self.assertEqual(m.negated, negated)

    def assert_no_match(self, m: Optional[PhraseMatch]) -> None:
        self.assertIsNone(m)


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
