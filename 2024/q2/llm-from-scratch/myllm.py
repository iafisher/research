import functools
import re
from pathlib import Path


# https://en.wikisource.org/wiki/The_Verdict
the_verdict = Path("the-verdict.txt").read_text()


class BaseTokenizer:
    def encode(self, text):
        raise NotImplementedError

    def decode(self, ids):
        raise NotImplementedError


class RegexTokenizer(BaseTokenizer):
    def __init__(self, token_to_id):
        self.token_to_id = token_to_id
        self.id_to_token = {id_: token for token, id_ in self.token_to_id.items()}

    def encode(self, text):
        tokens = self.tokenize(text)
        return [
            (
                self.token_to_id[token]
                if token in self.token_to_id
                else self.token_to_id[TOKEN_UNKNOWN]
            )
            for token in tokens
        ]

    def decode(self, ids):
        words = [self.id_to_token[id_] for id_ in ids]
        return functools.reduce(self._concatenate, words)

    @classmethod
    def tokenize(cls, text):
        return [
            item.strip()
            for item in re.split(r'([,.:;?_!"()\']|--|\s)', text)
            if item and not item.isspace()
        ]

    @classmethod
    def _concatenate(cls, left, right):
        if right in ",.?!)':;":
            return left + right
        elif left.endswith(('"', "(")):
            return left + right
        else:
            return left + " " + right


TOKEN_UNKNOWN = "<|unk|>"
TOKEN_END_OF_TEXT = "<|endoftext|>"


def build_vocabulary(text, tokenizer=RegexTokenizer.tokenize):
    tokens = tokenizer(text)
    tokens.append(TOKEN_UNKNOWN)
    tokens.append(TOKEN_END_OF_TEXT)

    return {token: index for index, token in enumerate(sorted(tokens))}


vocab = build_vocabulary(the_verdict)
tokenizer = RegexTokenizer(vocab)
# print(tokenizer.decode(tokenizer.encode(the_verdict)))
print(tokenizer.encode("Hello, world!"))
