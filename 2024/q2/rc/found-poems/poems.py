import csv
import datetime
import itertools
import random
import re
from pathlib import Path

import inflect

# import prosodic
import pandas as pd
import spacy

# python -m spacy download en_core_web_sm
# nlp = spacy.load("en_core_web_sm")


def iambic(n):
    return [i % 2 for i in range(n * 2)]


IAMB10 = iambic(10)
REGEX = re.compile(r"[.,;:/\n] +")


def extract_comments():
    # this took 15 minutes on my laptop with 16 GB RAM
    p = Path.home() / "Downloads" / "hacker-news.parquet"
    df = pd.read_parquet(p, engine="pyarrow")
    tstamp = int(datetime.datetime(2014, 1, 1).timestamp())
    df2 = df[(df["type"] == "comment") & (df["time"] >= tstamp)]
    df3 = df2[["by", "time", "text", "id"]]
    df3.to_csv(Path.home() / "Downloads" / "hn2023.csv")


ntotal = 0
nfailed = 0


def look_for_poem(dct, row) -> bool:
    global ntotal
    global nfailed

    text = row["text"]

    stresses = scan(dct, text)

    ntotal += 1
    if stresses is None:
        nfailed += 1
        return False

    feet = make_feet(stresses)

    if is_iambic(feet):
        return True

    if is_haiku(text):
        return True

    return False


def is_iambic(feet):
    return len(feet) >= 10 and iamb_percent(feet) > 0.8


def is_haiku(text):
    lines = [l for l in REGEX.split(text) if l]
    return (
        len(lines) == 3
        and syllables(dct, lines[0]) == 5
        and syllables(dct, lines[1]) == 7
        and syllables(dct, lines[2]) == 5
    )


def syllables(dct, line):
    es = [
        dct.get(word.upper().rstrip(",").rstrip(".").rstrip('"').rstrip("'"))
        for word in line.split()
    ]
    if any(e is None for e in es):
        return None

    return sum(len(e) for e in es)


def scan(dct, text):
    r = []
    for word in text.split():
        word = normalize_word(word)
        if not word:
            continue

        if isinstance(word, list):
            stresses = []
            for subword in word:
                x = dct.get(normalize_word(subword, recurse=False))
                if x is None:
                    stresses = None
                    break
                else:
                    stresses.extend(x)
        else:
            stresses = dct.get(word)

        if stresses is None:
            # if random.randint(1, 100) == 42:
            #     print("failed:", word)

            return None

        r.extend(stresses)

    return r


# 967679 (96.8%) -- base
# 913236 (91.3%) -- normalize_word
# 870663 (87.1%) -- upper() at end
# 866945 (86.7%) -- number_to_words
# 488997 (48.9%) -- more refinements
# 470352 (47.0%) -- fixed number_to_words more


inflect_engine = inflect.engine()


def normalize_word(word, recurse=True):
    word = (
        word.upper()
        .rstrip(",")
        .rstrip(".")
        .strip('"')
        .strip("'")
        .strip(":")
        .strip("?")
        .strip("(")
        .strip(")")
        .replace("&#X27;", "'")
    )
    if recurse and word.isdigit():
        try:
            return (
                inflect_engine.number_to_words(word, comma=False).replace("-").split()
            )
        except Exception:
            pass

    word = strip_prefix(word, "&GT;")
    word = strip_prefix(word, "&QUOT;")

    if not word.isalpha():
        return ""

    return word


def strip_prefix(word, prefix):
    if word.startswith(prefix):
        return word[len(prefix) :]
    else:
        return word


def iamb_percent(feet):
    if not feet:
        return 0.0

    return sum(1 for f in feet if is_iamb(f)) / len(feet)


def is_iamb(foot):
    return foot == [0, 1]


def make_feet(stresses):
    r = []

    start = 0
    for i, stress in enumerate(stresses):
        if stress == 1 and start != i:
            r.append(stresses[start : (i + 1)])
            start = i + 1

    if start < len(stresses) - 1:
        r.append(stresses[start:])

    return r


def has_pattern(stresses):
    if len(stresses) < 10:
        return None

    if stresses[-30:] == iambic(30):
        return 10

    return None


def load_dct():
    dct = {}
    # https://github.com/Alexir/CMUdict/blob/master/cmudict-0.7b
    with open(Path.home() / "Downloads" / "cmudict-0.7b", encoding="latin1") as f:
        for line in f:
            if line.startswith(";"):
                continue

            word, *defn = line.split()
            dct[word] = [min(int(p[-1]), 1) for p in defn if p and p[-1].isdigit()]

    # dct["AT"] = [0]
    # dct["ITS"] = [0]
    dct["OF"] = [0]
    dct["TO"] = [0]
    return dct


def mainloop(dct):
    # from https://www.kaggle.com/datasets/nickalt/hacker-news
    # docs: https://github.com/HackerNews/API?tab=readme-ov-file
    with open(Path.home() / "Downloads" / "hn2023.csv") as f:
        reader = csv.DictReader(f)
        n = 0
        for i, row in enumerate(reader, start=1):
            if i % 100_000 == 0:
                print(i)

            if look_for_poem(dct, row):
                print("--- poem ---")
                print(f"by {row['by']}")
                print(f"https://news.ycombinator.com/item?id={row['id']}")
                print()
                print(row["text"])
                print()
                print("--- /poem ---")
                n += 1

            if i == 1_000_000:
                break

        print(f"Found {n}")
        print(f"Failed to scan {nfailed} ({nfailed / ntotal:.1%})")


dct = load_dct()
mainloop(dct)

# extract_comments()
