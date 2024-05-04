import functools
import re
from pathlib import Path

import tiktoken
import torch
from torch import nn
from torch.utils.data import Dataset, DataLoader


# https://en.wikisource.org/wiki/The_Verdict
the_verdict = Path("the-verdict.txt").read_text()


class SelfAttention(nn.Module):
    """
    ch 3

    This is a simplified self-attention mechanism, use CausalAttention instead.
    """

    def __init__(self, d_in, d_out, qkv_bias=False):
        super().__init__()
        self.d_out = d_out
        self.W_query = nn.Linear(d_in, d_out, bias=qkv_bias)
        self.W_key = nn.Linear(d_in, d_out, bias=qkv_bias)
        self.W_value = nn.Linear(d_in, d_out, bias=qkv_bias)

    def forward(self, x):
        keys = self.W_key(x)
        queries = self.W_query(x)
        values = self.W_value(x)

        attn_scores = queries @ keys.T
        attn_weights = torch.softmax(attn_scores / keys.shape[-1] ** 0.5, dim=-1)
        context_vec = attn_weights @ values
        return context_vec


class CausalAttention(nn.Module):
    """
    ch 3

    This class implements two improvements over SelfAttention:

    - causal self-attention, meaning that inputs past the current token are masked so they
      don't affect the context vector
    - random dropout of some attention weights to avoid overfit

    """

    def __init__(self, d_in, d_out, context_length, dropout, qkv_bias=False):
        super().__init__()
        self.d_out = d_out
        self.W_query = nn.Linear(d_in, d_out, bias=qkv_bias)
        self.W_key = nn.Linear(d_in, d_out, bias=qkv_bias)
        self.W_value = nn.Linear(d_in, d_out, bias=qkv_bias)
        self.dropout = nn.Dropout(dropout)
        self.register_buffer(
            "mask", torch.triu(torch.ones(context_length, context_length), diagonal=1)
        )

    def forward(self, x):
        b, num_tokens, d_in = x.shape
        keys = self.W_key(x)
        queries = self.W_query(x)
        values = self.W_value(x)

        attn_scores = queries @ keys.transpose(1, 2)
        attn_scores.masked_fill_(self.mask.bool()[:num_tokens, :num_tokens], -torch.inf)
        attn_weights = torch.softmax(attn_scores / keys.shape[-1] ** 0.5, dim=-1)
        attn_weights = self.dropout(attn_weights)

        context_vec = attn_weights @ values
        return context_vec


class MultiHeadAttentionWrapper(nn.Module):
    """
    ch 3

    Use the equivalent but more computationally efficient MultiHeadAttention class
    instead.
    """

    def __init__(self, d_in, d_out, context_length, dropout, num_heads, qkv_bias=False):
        super().__init__()
        self.heads = nn.ModuleList(
            [
                CausalAttention(d_in, d_out, context_length, dropout, qkv_bias)
                for _ in range(num_heads)
            ]
        )

    def forward(self, x):
        return torch.cat([head(x) for head in self.heads], dim=-1)


class MultiHeadAttention(nn.Module):
    """
    ch 3

    Equivalent to MultiHeadAttentionWrapper but more efficient
    """

    def __init__(self, d_in, d_out, context_length, dropout, num_heads, qkv_bias=False):
        super().__init__()
        assert d_out % num_heads == 0, "d_out must be divisible by num_heads"

        self.d_out = d_out
        self.num_heads = num_heads
        self.head_dim = d_out // num_heads
        self.W_query = nn.Linear(d_in, d_out, bias=qkv_bias)
        self.W_key = nn.Linear(d_in, d_out, bias=qkv_bias)
        self.W_value = nn.Linear(d_in, d_out, bias=qkv_bias)
        self.out_proj = nn.Linear(d_out, d_out)
        self.dropout = nn.Dropout(dropout)
        self.register_buffer(
            "mask", torch.triu(torch.ones(context_length, context_length), diagonal=1)
        )

    def forward(self, x):
        b, num_tokens, d_in = x.shape
        keys = self.W_key(x)
        queries = self.W_query(x)
        values = self.W_value(x)

        keys = keys.view(b, num_tokens, self.num_heads, self.head_dim)
        queries = queries.view(b, num_tokens, self.num_heads, self.head_dim)
        values = values.view(b, num_tokens, self.num_heads, self.head_dim)

        keys = keys.transpose(1, 2)
        queries = queries.transpose(1, 2)
        values = values.transpose(1, 2)

        attn_scores = queries @ keys.transpose(2, 3)
        mask_bool = self.mask.bool()[:num_tokens, :num_tokens]

        attn_scores.masked_fill_(mask_bool, -torch.inf)

        attn_weights = torch.softmax(attn_scores / keys.shape[-1] ** 0.5, dim=-1)
        attn_weights = self.dropout(attn_weights)

        context_vec = (attn_weights @ values).transpose(1, 2)

        context_vec = context_vec.contiguous().view(b, num_tokens, self.d_out)
        context_vec = self.out_proj(context_vec)
        return context_vec


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


def example_self_attention():
    # ch 3
    inputs = torch.tensor(
        [
            [0.43, 0.15, 0.89],
            [0.55, 0.87, 0.66],
            [0.57, 0.85, 0.64],
            [0.22, 0.58, 0.33],
            [0.77, 0.25, 0.10],
            [0.05, 0.80, 0.55],
        ]
    )

    # input embedding to generate context vector for
    query = inputs[1]
    attn_scores_2 = torch.empty(inputs.shape[0])
    for i, x_i in enumerate(inputs):
        attn_scores_2[i] = torch.dot(x_i, query)
    print("Attention scores:", attn_scores_2)

    # normalize so they add up to 1
    attn_weights_2_naive = attn_scores_2 / attn_scores_2.sum()
    print("Attention weights (naive):  ", attn_weights_2_naive)

    # softmax is a better normalization function
    attn_weights_2 = torch.softmax(attn_scores_2, dim=0)
    print("Attention weights (softmax):", attn_weights_2)

    context_vec_2 = torch.zeros(query.shape)
    for i, x_i in enumerate(inputs):
        context_vec_2 += attn_weights_2[i] * x_i

    print("Context vector:", context_vec_2)

    # calculate all context vectors at once
    attn_scores = inputs @ inputs.T
    # equivalent to:
    #
    #   attn_scores = torch.empty(inputs.shape[0], inputs.shape[0])
    #   for i, x_i in enumerate(inputs):
    #       for j, x_j in enumerate(inputs):
    #           attn_scores[i, j] = torch.dot(x_i, x_j)
    #

    attn_weights = torch.softmax(attn_scores, dim=1)
    all_context_vecs = attn_weights @ inputs
    print("All context vectors:", all_context_vecs)

    """
    Big idea: for each input token, we want the model to be aware of its relationships
    with the other tokens in the input. To do this we compute a context vector of size M
    for each input 1..N where context_vec[i][j] represents how much token j is related to
    token i. M is the # of dimensions of the embedding.

    A simple way to do this is compute a vector of N attention weights, then sum the
    weighted input tokens to produce the context vector.

    Caveat: in this function we compute attention weights simply using the dot product,
    but in real life you'll want the attention weights to be trainable.
    """


def example_self_attention2():
    # ch 3
    inputs = torch.tensor(
        [
            [0.43, 0.15, 0.89],
            [0.55, 0.87, 0.66],
            [0.57, 0.85, 0.64],
            [0.22, 0.58, 0.33],
            [0.77, 0.25, 0.10],
            [0.05, 0.80, 0.55],
        ]
    )

    x_2 = inputs[1]
    d_in = inputs.shape[1]
    d_out = 2

    torch.manual_seed(123)
    W_query = torch.nn.Parameter(torch.rand(d_in, d_out), requires_grad=False)
    W_key = torch.nn.Parameter(torch.rand(d_in, d_out), requires_grad=False)
    W_value = torch.nn.Parameter(torch.rand(d_in, d_out), requires_grad=False)

    query_2 = x_2 @ W_query
    key_2 = x_2 @ W_key
    value_2 = x_2 @ W_value
    print(query_2)

    keys = inputs @ W_key
    values = inputs @ W_value

    keys_2 = keys[1]
    attn_score_22 = query_2.dot(keys_2)
    print("attn_score_22:", attn_score_22)

    attn_scores_2 = query_2 @ keys.T

    d_k = keys.shape[-1]
    attn_weights_2 = torch.softmax(attn_scores_2 / d_k**0.5, dim=-1)
    print("attn_weights_2:", attn_weights_2)

    context_vec_2 = attn_weights_2 @ values
    print("context_vec_2:", context_vec_2)

    """
    The math here is more complex but the big idea is that we've introduced three new
    matrices: query (W_q), key (W_k), and value (W_v)

    W_q is combined with the input embedding to produce the query vector, which is
    combined with the key vector (from W_k) for the attention weights, and then with the
    value vector (from W_v) for the attention scores.

    W_q, W_k, and W_v can all be tuned during the training process, unlike our simpler
    algorithm.
    """


def example_multi_head_attention():
    # ch 3

    torch.manual_seed(123)

    inputs = torch.tensor(
        [
            [0.43, 0.15, 0.89],
            [0.55, 0.87, 0.66],
            [0.57, 0.85, 0.64],
            [0.22, 0.58, 0.33],
            [0.77, 0.25, 0.10],
            [0.05, 0.80, 0.55],
        ]
    )

    batch = torch.stack((inputs, inputs), dim=0)

    batch_size, context_length, d_in = batch.shape
    d_out = 2
    multi_head_attention = MultiHeadAttention(
        d_in, d_out, context_length, 0.0, num_heads=2
    )
    context_vecs = multi_head_attention(batch)
    print(context_vecs)


if __name__ == "__main__":
    # example_data_loader()
    # example_embedding()
    # example_embedding_bigger()
    # example_self_attention()
    # example_self_attention2()
    example_multi_head_attention()
