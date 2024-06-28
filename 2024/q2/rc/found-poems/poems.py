import argparse
import csv
import datetime
import itertools
import random
import re
import sys
import time
from collections import Counter
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
SENTENCE_SPLIT = re.compile(r"[.,;:/\n] +")
WORD_SPLIT = re.compile(r"(https?://[^ ]+|[\s.;,:/()]+)")


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

    text = (
        row["text"]
        .replace("&#x27;", "'")
        .replace("&quot;", '"')
        .replace("&#x2F", "/")
        .replace("<p>", "\n\n")
    )
    words = WORD_SPLIT.split(text)
    words_lower = [w.lower() for w in words]

    # if is_repetitive(words):
    #     return True

    ntotal += 1
    # stresses = scan(dct, text)
    # if stresses is None:
    #     nfailed += 1
    #     return False

    # feet = make_feet(stresses)

    # if is_sonnet(feet) and is_poetic(words_lower):
    #     return True

    if is_regular_length(dct, text):
        return True

    # if is_iambic(feet):
    #     return True

    # if is_haiku(text):
    #     return True

    return False


def is_regular_length(dct, text):
    if "<a href" in text or text.startswith("&gt;"):
        return False

    lines = [l for l in SENTENCE_SPLIT.split(text) if l]
    if len(lines) < 5:
        return False

    stresscounts = list(
        sorted(Counter(len(scan(dct, line) or []) & ~1 for line in lines))
    )
    if (
        0 < len(stresscounts) < 3
        and stresscounts[0] != 0
        and (len(stresscounts) == 1 or abs(stresscounts[1] - stresscounts[0]) < 3)
    ):
        print(stresscounts)
        return True

    return False


REPETITIVE_SKIP = {"you're", "couldn't", "chicken", "buffalo"}


def is_repetitive(words):
    if not (30 <= len(words) <= 100):
        return False

    word_counts = Counter(
        word.lower()
        for word in words
        if len(word) > 5 and not word.isspace() and word not in REPETITIVE_SKIP
    )

    if word_counts["and"] > 5:
        return True

    # items = word_counts.most_common(1)
    # if not items:
    #     return False

    # word, n = items[0]
    # if n > 5:
    #     print(word)
    #     if word == "january":
    #         return True

    return False


def is_sonnet(feet):
    return abs(sum(len(foot) for foot in feet) - (14 * 10)) < 5


POETIC_WORDS = {"flower", "rose", "roses", "nightingale"}


def is_poetic(words_lower):
    return any(w in words_lower for w in POETIC_WORDS)


def is_iambic(feet):
    return len(feet) >= 10 and iamb_percent(feet) > 0.8


def is_haiku(text):
    lines = [l for l in SENTENCE_SPLIT.split(text) if l]
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
    # dct["OF"] = [0]
    # dct["TO"] = [0]
    return dct


TOTAL_ROWS = 31499723
SHORT_ROWS = 1000000
PROGRESS_COUNTER = 100_000


def mainloop(dct, should_print, short):
    # from https://www.kaggle.com/datasets/nickalt/hacker-news
    # docs: https://github.com/HackerNews/API?tab=readme-ov-file
    with open(Path.home() / "Downloads" / "hn2023.csv") as f:
        reader = csv.DictReader(f)
        n = 0

        nrows = SHORT_ROWS if short else TOTAL_ROWS
        start_time = time.time_ns()
        printed_progress = False
        for i, row in enumerate(reader, start=1):
            if i % PROGRESS_COUNTER == 0:
                eprint(f"*** progress: {i / nrows:.1%}")

                if not printed_progress:
                    now = time.time_ns()
                    millis_per_row = ((now - start_time) / 1_000_000) / PROGRESS_COUNTER
                    estimated_time = (
                        millis_per_row * (nrows - PROGRESS_COUNTER)
                    ) / 1000.0
                    eprint(f"*** estimated time: {estimated_time:.1f}s")
                    eprint(f"*** per row: {millis_per_row:.3f} ms")

                printed_progress = True

            if look_for_poem(dct, row):
                if should_print:
                    print("--- poem ---")
                    print(f"by {row['by']}")
                    print(f"https://news.ycombinator.com/item?id={row['id']}")
                    print()
                    print(row["text"].replace("&#x27;", "'"))
                    print()
                    print("--- /poem ---")
                n += 1

            if short and i == SHORT_ROWS:
                break

        end_time = time.time_ns()

        nanos_elapsed = end_time - start_time
        millis_elapsed = nanos_elapsed / 1_000_000.0
        secs_elapsed = millis_elapsed / 1000.0

        eprint()
        eprint(f"Elapsed: {secs_elapsed:.1f}s")
        eprint(f"Per row: {millis_elapsed / nrows:.3f} ms")
        eprint()
        eprint(f"Found {n}")
        eprint(f"Failed to scan {nfailed} ({nfailed / ntotal:.1%})")


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--print", action="store_true")
    p.add_argument("--short", action="store_true")
    args = p.parse_args()

    dct = load_dct()

    try:
        mainloop(dct, args.print, args.short)
    except KeyboardInterrupt:
        print()
        sys.exit(1)

# extract_comments()
