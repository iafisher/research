import functools
import re
from pathlib import Path

import tiktoken
import torch
from torch.utils.data import Dataset, DataLoader


# https://en.wikisource.org/wiki/The_Verdict
the_verdict = Path("the-verdict.txt").read_text()


class BaseTokenizer:
    def encode(self, text):
        raise NotImplementedError

    def decode(self, ids):
        raise NotImplementedError


class RegexTokenizer(BaseTokenizer):
    # ch 2

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


class BytePairEncodingTokenizer(BaseTokenizer):
    # ch 2

    def __init__(self):
        self.tokenizer = tiktoken.get_encoding("gpt2")

    def encode(self, text):
        return self.tokenizer.encode(text)

    def decode(self, ids):
        return self.tokenizer.decode(ids)


class GPTDatasetV1(Dataset):
    # ch 2

    def __init__(self, txt, tokenizer, max_length, stride):
        self.tokenizer = tokenizer
        self.input_ids = []
        self.target_ids = []

        token_ids = tokenizer.encode(txt)

        for i in range(0, len(token_ids) - max_length, stride):
            input_chunk = token_ids[i : i + max_length]
            target_chunk = token_ids[i + 1 : i + max_length + 1]
            self.input_ids.append(torch.tensor(input_chunk))
            self.target_ids.append(torch.tensor(target_chunk))

    def __len__(self):
        return len(self.input_ids)

    def __getitem__(self, idx):
        return self.input_ids[idx], self.target_ids[idx]


def create_dataloader_v1(
    txt,
    # group together samples into batches of this size
    batch_size=4,
    # size of the window
    max_length=256,
    # how much to shift the 'window' by
    stride=128,
    shuffle=True,
    # drop last batch to ensure all are of equal size
    drop_last=True,
):
    # ch 2
    tokenizer = BytePairEncodingTokenizer()
    dataset = GPTDatasetV1(txt, tokenizer, max_length=max_length, stride=stride)
    dataloader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        drop_last=drop_last,
    )
    return dataloader


TOKEN_UNKNOWN = "<|unk|>"
TOKEN_END_OF_TEXT = "<|endoftext|>"


def build_vocabulary(text, tokenizer=RegexTokenizer.tokenize):
    # ch 2
    tokens = tokenizer(text)
    tokens.append(TOKEN_UNKNOWN)
    tokens.append(TOKEN_END_OF_TEXT)

    return {token: index for index, token in enumerate(sorted(tokens))}


def example_regex_tokenize():
    # ch 2
    vocab = build_vocabulary(the_verdict)
    tokenizer = RegexTokenizer(vocab)


def example_byte_pair_encoding_tokenize():
    # ch 2
    tokenizer = BytePairEncodingTokenizer()
    print(tokenizer.encode(the_verdict))


def example_data_loader():
    # ch 2
    dataloader = create_dataloader_v1(
        the_verdict, batch_size=8, max_length=4, stride=4, shuffle=False
    )
    data_iter = iter(dataloader)
    inputs, targets = next(data_iter)
    print("Inputs: ", inputs)
    print("Targets:", targets)


def example_embedding():
    # ch 2
    input_ids = torch.tensor([2, 3, 5, 1])
    vocab_size = 6
    output_dim = 3

    # torch.manual_seed(123)
    embedding_layer = torch.nn.Embedding(vocab_size, output_dim)
    print("Weights:")
    print(embedding_layer.weight)
    print()

    print("Embedding:")
    print(embedding_layer(torch.tensor([3])))
    print()

    print("Embedding:")
    print(embedding_layer(input_ids))


def example_embedding_bigger():
    output_dim = 256  # compared to 12,288 for GPT-3
    vocab_size = 50257  # for BPE tokenizer

    token_embedding_layer = torch.nn.Embedding(vocab_size, output_dim)

    max_length = 4
    dataloader = create_dataloader_v1(
        the_verdict,
        batch_size=8,
        max_length=max_length,
        stride=max_length,
        shuffle=False,
    )
    data_iter = iter(dataloader)
    inputs, targets = next(data_iter)
    print(inputs.shape)  # 8 x 4 (batch_size x max_length)
    print(targets.shape)  # 8 x 4 (batch_size x max_length)

    token_embeddings = token_embedding_layer(inputs)
    print(token_embeddings.shape)  # 8 x 4 x 256 (batch_size x max_length x output_dim)
    # print(token_embeddings)

    # absolute position embedding (so model is aware of positional relationships)
    context_length = max_length
    pos_embedding_layer = torch.nn.Embedding(context_length, output_dim)
    pos_embeddings = pos_embedding_layer(torch.arange(context_length))
    print(pos_embeddings.shape)  # 4 x 256 (max_length x output_dim)
    print(pos_embeddings)

    # Q: token_embeddings and pos_embeddings have different shapes, so how does this
    #    addition work?
    #
    # A: Think of token_embeddings as an array of 4 x 256 matrices, and pos_embeddings as
    #    a single 4 x 256 matrix. pos_embeddings is simply added to every 4 x 256 element
    #    of token_embeddings.

    # Q: As far as I can tell, token_embeddings and pos_embeddings are both just filled
    #    with random numbers, so why does this do anything?
    #
    # A: The individual weights of token_embeddings are random, but every token with the
    #    same ID gets the same matrix of random weights. So it's not actually random.
    input_embeddings = token_embeddings + pos_embeddings
    print(input_embeddings.shape)  # 8 x 4 x 256

    """
    Explanation:

    We are creating an *embedding*, a representation of the raw input data (which is text)
    as continuous-valued tensors (i.e., N-dimensional matrices of real numbers), because
    that is the input that the neural network requires.

    First we choose the dimensions of the embedding. You can imagine that a 2D or 3D
    embedding would place similar words close to each other in geometric space. In order
    to represent more complex relationships, we use larger dimensions (256).

    We load the data and get the first input and target tensors, then use our embedding
    layer to create an embedding from the token IDs.

    We also create an embedding of the positions so that the neural network will be
    sensitive to positional relationships.

    To create the final input embedding, we add the token embeddings to the position
    embeddings.
    """


if __name__ == "__main__":
    # example_data_loader()
    # example_embedding()
    example_embedding_bigger()
