import argparse
import csv
import fnmatch
import os
import sqlite3
import subprocess
import sys
import time
import urllib
from pathlib import Path

import click
import requests
from tree_sitter_languages import get_language, get_parser


@click.group()
def cli():
    pass


@cli.command("scan")
@click.argument("folders", nargs=-1)
@click.option("--lang", "langname")
@click.option("--ext", "extension")
def main_scan(folders, langname, extension):
    assert langname is not None

    lang = get_language(langname)
    parser = get_parser(langname)
    parser.set_language(lang)

    db = Database()
    db.create_tables()

    for folder in folders:
        print(f"Scanning {folder}")
        scan_folder(db, parser, folder, extension)


@cli.command("clear")
@click.argument("repo")
def main_clear(repo):
    db = Database()
    if repo == "*":
        confirm_or_bail("Clear the entire database? ")
        db.clear_all()
    else:
        confirm_or_bail(f"Clear {repo!r} from the database? ")
        db.clear_repo(repo)


@cli.command("collisions")
@click.option(
    "--lines", default=0, help="Filter out functions with fewer than this many lines"
)
@click.option(
    "--count", default=2, help="Filter out groups of fewer than this many matches"
)
@click.option(
    "--cross-repo", is_flag=True, help="Only show matches across repositories"
)
@click.option("--cross-lang", is_flag=True, help="Only show matches across languages")
@click.option(
    "--ignore-func",
    multiple=True,
    help="Ignore any function containing this glob pattern",
)
@click.option(
    "--ignore-path", multiple=True, help="Ignore any path containing this glob pattern"
)
@click.option(
    "--ignore-same-name", is_flag=True, help="Ignore matches with the same name"
)
def main_collisions(
    *, lines, count, cross_repo, cross_lang, ignore_func, ignore_path, ignore_same_name
):
    db = Database()
    groups = db.find_collisions(
        lines=lines,
        count=count,
        cross_repo=cross_repo,
        cross_lang=cross_lang,
        ignore_func=ignore_func,
        ignore_path=ignore_path,
        ignore_same_name=ignore_same_name,
    )
    for group in groups:
        print(f"Size: {len(group)}")
        for filename, repo, funcname in group:
            print(f"  {funcname} in {repo} @ {filename}")

    if groups:
        print()
        print(f"Found {len(groups)}.")


@cli.command("tree-sitter")
@click.argument("path")
@click.option("--lang", "langname")
def main_tree_sitter(path, langname):
    assert langname is not None

    lang = get_language(langname)
    parser = get_parser(langname)
    parser.set_language(lang)

    code = Path(path).read_bytes()
    tree = parser.parse(code)
    print_tree(tree.root_node)


def print_tree(node, indent=0):
    indent_str = "  " * indent
    print(indent_str + node.type)
    for child in node.children:
        print_tree(child, indent + 1)


@cli.command("download-crates")
@click.argument("crates", nargs=-1)
@click.option(
    "--csv",
    "csvpath",
    help="Path to CSV of crates.io database dump from https://static.crates.io/db-dump.tar.gz",
)
@click.option("--dest")
def main_download_crates(crates, csvpath, dest):
    # e.g., top crates from https://crates.io/crates?sort=downloads

    if dest:
        os.chdir(dest)

    crate_info = {}

    csv.field_size_limit(1000000)
    with open(csvpath) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["name"] in crates:
                crate_info[row["name"]] = row

    for crate in crates:
        if os.path.exists(crate):
            print(f"** Skipping {crate}: directory already exists")
            continue

        info = crate_info.get(crate)
        if not info:
            print(f"** Skipping {crate}: not found in CSV")
            continue

        repo_url = info["repository"]
        if not repo_url:
            print(f"** Skipping {crate}: no repository URL found")
            continue

        if not is_github(repo_url):
            print(f"** Skipping {crate}: don't know how to download from {repo_url}")
            continue

        # repair one malformed URL
        bad_pkg_end = "/tree/master/regex-syntax"
        if repo_url.endswith(bad_pkg_end):
            repo_url = repo_url[: -len(bad_pkg_end)]

        print(f"** Downloading {crate} from {repo_url}")
        try:
            sh("git", "clone", "--depth", "1", repo_url, crate)
        except subprocess.CalledProcessError as e:
            print(f"** Skipping {crate}: cloning failed with {e}")


@cli.command("download-pypi")
@click.argument("pkgs", nargs=-1)
@click.option("--dest")
def main_download_pypi(pkgs, dest):
    # e.g., top packages from https://pypistats.org/top

    if dest:
        os.chdir(dest)

    for pkg in pkgs:
        if os.path.exists(pkg):
            print(f"** Skipping {pkg}: directory already exists")
            continue

        manifest = requests.get(f"https://pypi.org/pypi/{pkg}/json").json()
        project_urls = manifest["info"].get("project_urls", {})
        repo_url = get_repo_url(project_urls)
        if not repo_url:
            print(f"** Skipping {pkg}: no repository URL found")
            continue

        if not is_github(repo_url):
            print(f"** Skipping {pkg}: don't know how to download from {repo_url}")
            continue

        print(f"** Downloading {pkg} from {repo_url}")
        sh("git", "clone", "--depth", "1", repo_url, pkg)


def get_repo_url(project_urls):
    possibilities = ["Source", "source", "Code", "Source Code", "Homepage"]
    for possibility in possibilities:
        if r := project_urls.get(possibility):
            return r

    return None


def is_github(url_str):
    return url_str and urllib.parse.urlparse(url_str).netloc == "github.com"


def scan_folder(db, parser, folder, extension):
    folder = Path(folder)
    repo_name = folder.name

    total_files = 0
    total_hashes = 0
    global_start_time = time.perf_counter()
    for path in folder.glob("**/*." + extension):
        start_time = time.perf_counter()
        nhashes = scan_file(db, parser, repo_name, folder, path)
        end_time = time.perf_counter()
        elapsed_ms = (end_time - start_time) * 1000.0

        print(f"Processed {path} in {elapsed_ms:.1f} ms ({nhashes:,} hashes)")
        total_files += 1
        total_hashes += nhashes

    global_end_time = time.perf_counter()
    if total_files > 0:
        elapsed_secs = global_end_time - global_start_time

        print()
        print(
            f"Processed {total_files:,} files in {elapsed_secs:.1f} s ({total_hashes:,} hashes)"
        )


def scan_file(db, parser, repo_name, repo_root, path):
    code = path.read_bytes()
    rel_path = path.relative_to(repo_root)
    tree = parser.parse(code)

    with db.transaction():
        count = 0
        for funcdef in find_function_definitions(tree.root_node):
            hsh = hash_function_def(funcdef.child_by_field_name("body"))
            db.store_hash(repo_name, str(rel_path), funcdef, hsh)
            count += 1

        return count


def find_function_definitions(root_node):
    for child in root_node.children:
        if child.type == "function_definition" or child.type == "function_item":
            yield child
        else:
            for grandchild in child.children:
                yield from find_function_definitions(grandchild)


def hash_function_def(funcdef):
    functuple = tree_to_tuple(funcdef)
    return hash(functuple)


def tree_to_tuple(tree):
    return (tree.type, tuple(tree_to_tuple(child) for child in tree.children))


class Database:
    def __init__(self):
        self.connection = sqlite3.connect("iso.db", isolation_level=None)
        self.connection.row_factory = sqlite3.Row

    def transaction(self):
        return TransactionManager(self.connection)

    def create_tables(self):
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS codehashes(
              hash VARCHAR NOT NULL,
              repo VARCHAR NOT NULL,
              filepath VARCHAR NOT NULL,
              funcname VARCHAR NOT NULL,
              start_line INT NOT NULL,
              start_column INT NOT NULL,
              end_line INT NOT NULL,
              end_column INT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS codehashes_index ON codehashes(hash);
            """
        )

    def store_hash(self, repo, filepath, funcdef, hsh):
        funcname = funcdef.child_by_field_name("name").text.decode("utf8")
        start_line, start_column = funcdef.start_point
        end_line, end_column = funcdef.end_point
        self.connection.execute(
            """
            INSERT INTO codehashes(
              hash, repo, filepath, funcname, start_line, start_column, end_line, end_column
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                hsh,
                repo,
                filepath,
                funcname,
                start_line,
                start_column,
                end_line,
                end_column,
            ),
        )

    def find_collisions(
        self,
        *,
        lines,
        count,
        cross_repo,
        cross_lang,
        ignore_func,
        ignore_path,
        ignore_same_name,
    ):
        cursor = self.connection.execute(
            """
            SELECT
              GROUP_CONCAT(filepath, char(0)) AS filepaths,
              GROUP_CONCAT(repo, char(0)) AS repos,
              GROUP_CONCAT(funcname, char(0)) AS funcnames
            FROM codehashes
            GROUP BY hash
            HAVING COUNT(*) >= ? AND MIN(end_line - start_line) >= ?
            """,
            (
                count,
                lines,
            ),
        )

        r = []
        for row in cursor.fetchall():
            filepaths = row["filepaths"].split("\0")
            repos = row["repos"].split("\0")
            funcnames = row["funcnames"].split("\0")
            filtered = [
                (filepath, repo, funcname)
                for (filepath, repo, funcname) in zip(filepaths, repos, funcnames)
                if not should_ignore(
                    filepath=filepath,
                    funcname=funcname,
                    ignore_path=ignore_path,
                    ignore_func=ignore_func,
                )
            ]

            filtered = filter_probably_same(filtered)

            if cross_repo:
                filtered = filter_cross_repo(filtered)

            if cross_lang:
                filtered = filter_cross_lang(filtered)

            if ignore_same_name:
                filtered = filter_same_name(filtered)

            if len(filtered) < count:
                continue

            r.append(filtered)

        return r

    def clear_repo(self, repo):
        self.connection.execute(
            """
            DELETE FROM codehashes WHERE repo = ?
            """,
            (repo,),
        )

    def clear_all(self):
        self.connection.execute(
            """
            DELETE FROM codehashes
            """
        )


def filter_probably_same(group):
    func_files_seen = set()

    r = []
    for item in group:
        filename = os.path.basename(item[0])
        funcname = item[2]

        if (filename, funcname) in func_files_seen:
            continue
        else:
            func_files_seen.add((filename, funcname))
            r.append(item)

    return r


def filter_cross_repo(group):
    repos_seen = set()

    r = []
    for item in group:
        repo = item[1]
        if repo in repos_seen:
            continue
        else:
            repos_seen.add(repo)
            r.append(item)

    if len(repos_seen) < 2:
        return []

    return r


def filter_cross_lang(group):
    langs_seen = set()

    r = []
    for item in group:
        lang = os.path.splitext(item[0])[1]
        if lang in langs_seen:
            continue
        else:
            langs_seen.add(lang)
            r.append(item)

    return r


def filter_same_name(group):
    names_seen = set()

    r = []
    for item in group:
        funcname = item[2]
        if funcname in names_seen:
            continue
        else:
            names_seen.add(funcname)
            r.append(item)

    return r


def should_ignore(*, filepath, funcname, ignore_path, ignore_func):
    if any(fnmatch.fnmatch(filepath, p) for p in ignore_path):
        return True

    if any(fnmatch.fnmatch(funcname, p) for p in ignore_func):
        return True

    return False


class TransactionManager:
    def __init__(self, db):
        self.db = db

    def __enter__(self):
        self.db.execute("BEGIN")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.db.execute("ROLLBACK")
        else:
            self.db.execute("COMMIT")


def confirm_or_bail(prompt):
    while True:
        r = input(prompt)
        r = r.strip().lower()
        if r in ("y", "yes"):
            return True
        elif r in ("n", "no"):
            print("Aborted.", file=sys.stderr)
            sys.exit(2)
        else:
            print("Please enter 'yes' or 'no'.")


def sh(*args):
    subprocess.run(args, check=True)


if __name__ == "__main__":
    cli()
