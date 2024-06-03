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
    elif parsed_cmd.command == "count":
        n = bop.count(fileset)
        print(n)
    else:
        err_unknown_command(parsed_cmd.command)


@dataclass
class ParsedCommand:
    command: str
    filters: List[Filter]


def parse_command(cmdstr: str) -> ParsedCommand:
    tokens = tokenize(cmdstr)
    if len(tokens) == 0:
        err_empty_input()

    command = tokens.pop(0).lower()

    if command in ("count", "delete", "list"):
        filters = parse_np_and_preds(tokens)
        return ParsedCommand(command=command, filters=filters)
    else:
        err_unknown_command(command)


def parse_np_and_preds(tokens: List[str]) -> List[Filter]:
    filters = parse_np(tokens)
    filters.extend(parse_preds(tokens))
    return filters


def parse_preds(tokens: List[str]) -> List[Filter]:
    filters = []
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
            raise BatchOpSyntaxError(f"could not parse starting at {tokens[i]!r}")

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
        tokens.insert(0, tkn)
        return []


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
class PAnyLit(BasePattern):
    literals: List[str]
    case_sensitive: bool = False
    captures: bool = False

    def test(self, token: str) -> Optional[WordMatch]:
        matches = False
        for literal in self.literals:
            if self.case_sensitive:
                matches = token == literal
            else:
                matches = token.lower() == literal.lower()

            if matches:
                break

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


def tokenize(cmdstr: str) -> List[str]:
    # TODO: more sophisticated tokenization
    # TODO: handle quoted strings
    return cmdstr.split()


def main_interactive(d: Optional[str]) -> None:
    root = path_or_default(d)

    fs = FileSet()
    while True:
        # TODO: separate counts for files and directories
        # TODO: default to ignoring .git + .gitignore?
        current_files = list(fs.resolve(root))
        print(f"{plural(len(current_files), 'file')}")

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

        if s.lower() == "list":
            for p in current_files:
                print(p)
            continue
        elif s[0] == "!":
            cmd = s[1:]
            if cmd == "pop":
                fs.pop()
            elif cmd == "clear":
                fs.clear()
            else:
                print(f"error: unknown directive: {cmd!r}")

            continue

        tokens = tokenize(s)
        filters = parse_preds(tokens)
        fs.filters.extend(filters)


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

    def is_in(self, pattern: str) -> "FileSet":
        self.filters.append(FilterIsIn(pattern))
        return self

    def is_not_in(self, pattern: str) -> "FileSet":
        self.filters.append(FilterNegated(FilterIsIn(pattern)))
        return self

    def is_hidden(self) -> "FileSet":
        self.filters.append(FilterIsHidden())
        return self

    def is_not_hidden(self) -> "FileSet":
        self.filters.append(FilterNegated(FilterIsHidden()))
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
        if p.is_dir():
            # TODO: more efficient way to check if directory is empty
            return len(list(p.glob("*"))) == 0
        else:
            return p.stat().st_size == 0


@dataclass
class FilterIsNamed(Filter):
    pattern: str

    def test(self, p: Path) -> bool:
        # TODO: case-insensitive file systems?
        return fnmatch.fnmatch(p.name, self.pattern)


@dataclass
class FilterIsIn(Filter):
    pattern: str

    def test(self, p: Path) -> bool:
        # TODO: messy
        return (p.is_dir() and fnmatch.fnmatch(p.name, self.pattern)) or any(
            fnmatch.fnmatch(s, self.pattern) for s in p.parts[:-1]
        )


@dataclass
class FilterIsHidden(Filter):
    def test(self, p: Path) -> bool:
        # TODO: cross-platform?
        # TODO: only consider parts from search root?
        return any(s.startswith(".") for s in p.parts)


@dataclass
class FilterSizeGreater(Filter):
    base: decimal.Decimal
    multiple: int

    def test(self, p: Path) -> bool:
        return p.stat().st_size > (self.base * self.multiple)


@dataclass
class FilterSizeGreaterEqual(Filter):
    base: decimal.Decimal
    multiple: int

    def test(self, p: Path) -> bool:
        return p.stat().st_size >= (self.base * self.multiple)


@dataclass
class FilterSizeLess(Filter):
    base: decimal.Decimal
    multiple: int

    def test(self, p: Path) -> bool:
        return p.stat().st_size < (self.base * self.multiple)


@dataclass
class FilterSizeLessEqual(Filter):
    base: decimal.Decimal
    multiple: int

    def test(self, p: Path) -> bool:
        return p.stat().st_size <= (self.base * self.multiple)


@dataclass
class FilterHasExtension(Filter):
    ext: str

    def __init__(self, ext: str) -> None:
        if ext.startswith("."):
            self.ext = ext
        else:
            self.ext = "." + ext

    def test(self, p: Path) -> bool:
        return p.suffix == self.ext


class BatchOp:
    def __init__(self, root: Optional[PathLike]) -> None:
        self.root = path_or_default(root)

    def list(self, fileset: FileSet) -> Generator[Path, None, None]:
        yield from list(fileset.resolve(self.root))

    def count(self, fileset: FileSet) -> int:
        return sum(1 for _ in fileset.resolve(self.root))

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
    # 'that is a file'
    (
        [
            POpt(PLit("that")),
            PAnyLit(["is", "are"]),
            PNot(),
            POpt(PLit("a")),
            PLit("file"),
        ],
        FilterIsFile,
    ),
    # 'that is a folder'
    (
        [
            POpt(PLit("that")),
            PAnyLit(["is", "are"]),
            PNot(),
            POpt(PLit("a")),
            PLit("folder"),
        ],
        FilterIsFolder,
    ),
    # 'that is named X'
    ([POpt(PAnyLit(["is", "are"])), PNot(), PLit("named"), PString()], FilterIsNamed),
    # 'that is empty'
    (
        [POpt(PLit("that")), PAnyLit(["is", "are"]), PNot(), PLit("empty")],
        FilterIsEmpty,
    ),
    # '> X bytes'
    ([PAnyLit([">", "gt"]), PDecimal(), PSizeUnit()], FilterSizeGreater),
    # '>= X bytes'
    ([PAnyLit([">=", "gte", "ge"]), PDecimal(), PSizeUnit()], FilterSizeGreaterEqual),
    # '< X bytes'
    ([PAnyLit(["<", "lt"]), PDecimal(), PSizeUnit()], FilterSizeLess),
    # '<= X bytes'
    ([PAnyLit(["<=", "lte", "le"]), PDecimal(), PSizeUnit()], FilterSizeLessEqual),
    # 'that is in X'
    (
        [
            POpt(PLit("that")),
            POpt(PAnyLit(["is", "are"])),
            PNot(),
            PLit("in"),
            PString(),
        ],
        FilterIsIn,
    ),
    # 'that is hidden'
    (
        [POpt(PLit("that")), POpt(PAnyLit(["is", "are"])), PNot(), PLit("hidden")],
        FilterIsHidden,
    ),
    # 'that has extension X'
    (
        [
            POpt(PLit("that")),
            PAnyLit(["has", "have"]),
            PAnyLit(["ext", "extension"]),
            PString(),
        ],
        FilterHasExtension,
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

    def test_match_string(self):
        pattern = [PLit("named"), PString()]
        m = try_phrase_match(pattern, ["named", "test.txt"])
        self.assert_match(m, captures=["test.txt"])

        m = try_phrase_match(pattern, ["named"])
        self.assert_no_match(m)

    def test_match_any_lit(self):
        pattern = [PAnyLit(["gt", ">"])]
        m = try_phrase_match(pattern, ["gt"])
        self.assert_match(m)

        m = try_phrase_match(pattern, [">"])
        self.assert_match(m)

        m = try_phrase_match(pattern, ["<"])
        self.assert_no_match(m)

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
