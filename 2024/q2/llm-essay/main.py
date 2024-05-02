"""
Write an N-paragraph essay about X topic.

1. Create an outline with one line per paragraph briefly describing what the paragraph will cover.
2. For each line in the outline, expand the line into a full paragraph.
3. For each paragraph, edit for style and clarity.
4. For each pair of paragraphs, edit the final sentence of the first paragraph and the first
   sentence of the second paragraph so that the paragraphs flow smoothly.
5. For each paragraph, edit for style and clarity.

"""

import math
import time
from typing import List

from openai import OpenAI


def main():
    fpath = "essay-" + str(math.floor(time.time())) + ".txt"

    outline = generate_outline(
        "the home front of the United States during World War II", 5
    )
    append_to_file(fpath, "\n".join(outline))

    paragraphs = outline_to_paragraphs(outline)
    append_to_file(fpath, "\n\n".join(paragraphs))

    paragraphs = copy_edit_paragraphs(paragraphs)
    append_to_file(fpath, "\n\n".join(paragraphs))


def copy_edit_paragraphs(paragraphs: List[str]) -> List[str]:
    r = []
    for para in paragraphs:
        para = ai(
            """
            You are a copy-editing assistant. You will be given a paragraph, and you should edit it
            for clarity and style. Focus on making the text concise while retaining precision.
            """,
            para,
        )
        r.append(para)

    return r


def outline_to_paragraphs(outline: List[str]) -> List[str]:
    paragraphs = []
    for line in outline:
        para = ai(
            """
            You are an essay-writing assistant. You will be given a line of text and it is your job
            to transform it into a paragraph of 3-5 sentences.
            """,
            line,
        )
        paragraphs.append(para)

    return paragraphs


def generate_outline(topic: str, n: int) -> List[str]:
    outline = ai(
        f"""
        Given a topic, generate an outline for a {n} paragraph essay about that topic. The outline
        should have one line for each paragraph with a brief description of what the paragraph will
        cover. The descriptions do not have to be complete sentences, but should convey enough
        information to be fleshed out into a full paragraph. One line per paragraph. No bullet
        points or other text formatting.
        """,
        topic,
    )
    return outline.splitlines()


def ai(instructions: str, query: str) -> str:
    print("Querying AI")
    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": instructions},
            {"role": "user", "content": query},
        ],
    )
    return response.choices[0].message.content


def append_to_file(name: str, contents: str) -> None:
    with open(name, "a") as f:
        f.write("------\n")
        f.write(contents)
        if not contents.endswith("\n"):
            f.write("\n")


if __name__ == "__main__":
    main()
