import functools
import re
from pathlib import Path

import tiktoken
import torch
from torch import nn
from torch.utils.data import Dataset, DataLoader


# https://en.wikisource.org/wiki/The_Verdict
the_verdict = Path("the-verdict.txt").read_text()


GPT_CONFIG_124M = dict(
    vocab_size=50257,
    # context_length=1024,
    context_length=256,  # smaller context_length for training
    emb_dim=768,
    n_heads=12,
    n_layers=12,
    drop_rate=0.1,
    qkv_bias=False,
)


def text_to_token_ids(text, tokenizer):
    # ch 5
    encoded = tokenizer.encode(text, allowed_special={"<|endoftext|>"})
    encoded_tensor = torch.tensor(encoded).unsqueeze(0)
    return encoded_tensor


def token_ids_to_text(token_ids, tokenizer):
    # ch 5
    flat = token_ids.squeeze(0)
    return tokenizer.decode(flat.tolist())


def calc_loss_batch(input_batch, target_batch, model, device):
    # ch 5
    input_batch, target_batch = input_batch.to(device), target_batch.to(device)
    logits = model(input_batch)
    loss = torch.nn.functional.cross_entropy(
        logits.flatten(0, 1), target_batch.flatten()
    )
    return loss


def calc_loss_loader(data_loader, model, device, num_batches=None):
    # ch 5
    total_loss = 0.0
    if num_batches is None:
        num_batches = len(data_loader)
    else:
        num_batches = min(num_batches, len(data_loader))

    for i, (input_batch, target_batch) in enumerate(data_loader):
        if i < num_batches:
            loss = calc_loss_batch(input_batch, target_batch, model, device)
            total_loss += loss.item()
        else:
            break

    return total_loss / num_batches


def train_model_simple(
    model,
    train_loader,
    val_loader,
    optimizer,
    device,
    num_epochs,
    eval_freq,
    eval_iter,
    start_context,
):
    # ch 5
    train_losses = []
    val_losses = []
    track_tokens_seen = []
    tokens_seen = 0
    global_step = -1

    for epoch in range(num_epochs):
        model.train()
        for input_batch, target_batch in train_loader:
            optimizer.zero_grad()
            loss = calc_loss_batch(input_batch, target_batch, model, device)
            loss.backward()
            optimizer.step()
            tokens_seen += input_batch.numel()
            global_step += 1

            if global_step % eval_freq == 0:
                train_loss, val_loss = evaluate_model(
                    model, train_loader, val_loader, device, eval_iter
                )
                train_losses.append(train_loss)
                val_losses.append(val_loss)
                track_tokens_seen.append(tokens_seen)
                print(
                    f"Epoch {epoch + 1} (step {global_step:06d}): Train loss {train_loss:.3f}, val_loss {val_loss:.3f}"
                )

        generate_and_print_sample(
            model, train_loader.dataset.tokenizer, device, start_context
        )

    return train_losses, val_losses, track_tokens_seen


def evaluate_model(model, train_loader, val_loader, device, eval_iter):
    # ch 5
    model.eval()
    with torch.no_grad():
        train_loss = calc_loss_loader(
            train_loader, model, device, num_batches=eval_iter
        )
        val_loss = calc_loss_loader(val_loader, model, device, num_batches=eval_iter)

    model.train()
    return train_loss, val_loss


def generate_and_print_sample(model, tokenizer, device, start_context):
    # ch 5
    model.eval()
    context_size = model.pos_emb.weight.shape[0]
    encoded = text_to_token_ids(start_context, tokenizer).to(device)
    with torch.no_grad():
        token_ids = generate_text_simple(
            model=model, idx=encoded, max_new_tokens=50, context_size=context_size
        )
        decoded_text = token_ids_to_text(token_ids, tokenizer)
        print(decoded_text)

    model.train()


class DummyGPTModel(nn.Module):
    # ch 4

    def __init__(self, cfg):
        super().__init__()
        self.tok_emb = nn.Embedding(cfg["vocab_size"], cfg["emb_dim"])
        self.pos_emb = nn.Embedding(cfg["context_length"], cfg["emb_dim"])
        self.drop_emb = nn.Dropout(cfg["drop_rate"])
        self.trf_blocks = nn.Sequential(
            *[DummyTransformerBlock(cfg) for _ in range(cfg["n_layers"])]
        )
        self.final_norm = DummyLayerNorm(cfg["emb_dim"])
        self.out_head = nn.Linear(cfg["emb_dim"], cfg["vocab_size"], bias=False)

    def forward(self, in_idx):
        batch_size, seq_len = in_idx.shape
        tok_embeds = self.tok_emb(in_idx)
        pos_embeds = self.pos_emb(torch.arange(seq_len, device=in_idx.device))
        x = tok_embeds + pos_embeds
        x = self.drop_emb(x)
        x = self.trf_blocks(x)
        x = self.final_norm(x)
        logits = self.out_head(x)
        return logits


class DummyTransformerBlock(nn.Module):
    # ch 4

    def __init__(self, cfg):
        super().__init__()

    def forward(self, x):
        return x


class DummyLayerNorm(nn.Module):
    # ch 4

    def __init__(self, normalized_shape, eps=1e-5):
        super().__init__()

    def forward(self, x):
        return x


class LayerNorm(nn.Module):
    # ch 4

    def __init__(self, emb_dim, eps=1e-5):
        super().__init__()
        self.eps = eps
        self.scale = nn.Parameter(torch.ones(emb_dim))
        self.shift = nn.Parameter(torch.zeros(emb_dim))

    def forward(self, x):
        # dim=-1 because last dimension is the embedding
        mean = x.mean(dim=-1, keepdim=True)
        # unbiased=False doesn't really matter but keeps us compatible with GPT-2
        variance = x.var(dim=-1, keepdim=True, unbiased=False)
        # `+ self.eps` to avoid division by zero
        norm_x = (x - mean) / torch.sqrt(variance + self.eps)
        return self.scale * norm_x + self.shift


class GELU(nn.Module):
    # ch 4

    def forward(self, x):
        return (
            0.5
            * x
            * (
                1
                + torch.tanh(
                    torch.sqrt(torch.tensor(2.0 / torch.pi))
                    * (x + 0.044715 * torch.pow(x, 3))
                )
            )
        )


class FeedForward(nn.Module):
    # ch 4

    def __init__(self, cfg):
        super().__init__()
        self.layers = nn.Sequential(
            # expand the input times 4 with a linear transformation
            nn.Linear(cfg["emb_dim"], 4 * cfg["emb_dim"]),
            # apply GELU -- a non-linear transformation
            GELU(),
            # contract the input back to the original dimension
            nn.Linear(4 * cfg["emb_dim"], cfg["emb_dim"]),
        )

    def forward(self, x):
        return self.layers(x)


class TransformerBlock(nn.Module):
    # ch 4

    def __init__(self, cfg):
        super().__init__()
        self.att = MultiHeadAttention(
            d_in=cfg["emb_dim"],
            d_out=cfg["emb_dim"],
            context_length=cfg["context_length"],
            num_heads=cfg["n_heads"],
            dropout=cfg["drop_rate"],
            qkv_bias=cfg["qkv_bias"],
        )
        self.ff = FeedForward(cfg)
        self.norm1 = LayerNorm(cfg["emb_dim"])
        self.norm2 = LayerNorm(cfg["emb_dim"])
        self.drop_resid = nn.Dropout(cfg["drop_rate"])

    def forward(self, x):
        shortcut = x
        x = self.norm1(x)
        x = self.att(x)
        x = self.drop_resid(x)
        x = x + shortcut

        shortcut = x
        x = self.norm2(x)
        x = self.ff(x)
        x = self.drop_resid(x)
        x = x + shortcut
        return x


class GPTModel(nn.Module):
    # ch 4

    def __init__(self, cfg):
        super().__init__()
        self.tok_emb = nn.Embedding(cfg["vocab_size"], cfg["emb_dim"])
        self.pos_emb = nn.Embedding(cfg["context_length"], cfg["emb_dim"])
        self.drop_emb = nn.Dropout(cfg["drop_rate"])
        self.trf_blocks = nn.Sequential(
            *[TransformerBlock(cfg) for _ in range(cfg["n_layers"])]
        )
        self.final_norm = LayerNorm(cfg["emb_dim"])
        self.out_head = nn.Linear(cfg["emb_dim"], cfg["vocab_size"], bias=False)

    def forward(self, in_idx):
        batch_size, seq_len = in_idx.shape
        tok_embeds = self.tok_emb(in_idx)
        pos_embeds = self.pos_emb(torch.arange(seq_len, device=in_idx.device))
        x = tok_embeds + pos_embeds
        x = self.drop_emb(x)
        x = self.trf_blocks(x)
        x = self.final_norm(x)
        logits = self.out_head(x)
        return logits


def generate_text_simple(model, idx, max_new_tokens, context_size):
    for _ in range(max_new_tokens):
        idx_cond = idx[:, -context_size:]
        with torch.no_grad():
            logits = model(idx_cond)

        logits = logits[:, -1, :]
        probs = torch.softmax(logits, dim=-1)
        # select the next token with the highest probability score
        idx_next = torch.argmax(probs, dim=-1, keepdim=True)
        idx = torch.cat((idx, idx_next), dim=1)

    return idx


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

    def encode(self, text, **kwargs):
        return self.tokenizer.encode(text, **kwargs)

    def decode(self, ids, **kwargs):
        return self.tokenizer.decode(ids, **kwargs)


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


def example_dummy_gpt():
    # ch 4

    tokenizer = tiktoken.get_encoding("gpt2")
    batch = []
    txt1 = "Every effort moves you"
    txt2 = "Every day holds a"

    batch.append(torch.tensor(tokenizer.encode(txt1)))
    batch.append(torch.tensor(tokenizer.encode(txt2)))
    batch = torch.stack(batch, dim=0)

    torch.manual_seed(123)
    model = DummyGPTModel(GPT_CONFIG_124M)
    logits = model(batch)
    print(
        "Output shape:", logits.shape
    )  # (num of inputs) X (num of tokens) X (vocab size)
    print(logits)


def example_layer_normalization():
    # ch 4
    torch.manual_seed(123)
    batch_example = torch.randn(2, 5)
    # ReLU: standard activation function which ensures all outputs are non-negative
    layer = nn.Sequential(nn.Linear(5, 6), nn.ReLU())
    out = layer(batch_example)
    print(out)

    # dim=-1 --> compute mean per row
    # keepdim=True --> keep original shape of input
    mean = out.mean(dim=-1, keepdim=True)
    variance = out.var(dim=-1, keepdim=True)
    print("Mean:", mean)
    print("Variance:", variance)

    out_norm = (out - mean) / torch.sqrt(variance)
    mean = out_norm.mean(dim=-1, keepdim=True)
    variance = out_norm.var(dim=-1, keepdim=True)
    print("Normalized:", out_norm)
    print("Mean:", mean)
    print("Variance:", variance)


def example_layer_normalization_by_module():
    # ch 4
    torch.manual_seed(123)
    batch_example = torch.randn(2, 5)

    ln = LayerNorm(emb_dim=5)
    out_ln = ln(batch_example)
    mean = out_ln.mean(dim=-1, keepdim=True)
    variance = out_ln.var(dim=-1, unbiased=False, keepdim=True)
    print("Mean:", mean)
    print("Variance:", variance)


def example_relu_versus_gelu():
    # ch 4
    import matplotlib.pyplot as plt

    gelu, relu = GELU(), nn.ReLU()

    x = torch.linspace(-3, 3, 100)
    y_gelu, y_relu = gelu(x), relu(x)
    plt.figure(figsize=(8, 3))
    for i, (y, label) in enumerate([(y_gelu, "GELU"), (y_relu, "ReLU")], start=1):
        plt.subplot(1, 2, i)
        plt.plot(x, y)
        plt.title(f"{label} activation function")
        plt.xlabel("x")
        plt.ylabel(f"{label}(x)")
        plt.grid(True)
    plt.tight_layout()
    plt.show()

    # ReLU is a piecewise function with a sharp corner at 0; GELU is a smooth curve, which
    # can make optimization easier


def example_feedforward():
    # ch 4

    ffn = FeedForward(GPT_CONFIG_124M)
    x = torch.rand(2, 3, 768)
    out = ffn(x)
    print(out.shape)


def example_shortcut_connections():
    # ch 4

    class ExampleDeepNeuralNet(nn.Module):
        def __init__(self, layer_sizes, use_shortcut):
            super().__init__()
            self.use_shortcut = use_shortcut
            self.layers = nn.ModuleList(
                [
                    nn.Sequential(nn.Linear(layer_sizes[0], layer_sizes[1]), GELU()),
                    nn.Sequential(nn.Linear(layer_sizes[1], layer_sizes[2]), GELU()),
                    nn.Sequential(nn.Linear(layer_sizes[2], layer_sizes[3]), GELU()),
                    nn.Sequential(nn.Linear(layer_sizes[3], layer_sizes[4]), GELU()),
                    nn.Sequential(nn.Linear(layer_sizes[4], layer_sizes[5]), GELU()),
                ]
            )

        def forward(self, x):
            for layer in self.layers:
                layer_output = layer(x)
                if self.use_shortcut and x.shape == layer_output.shape:
                    x = x + layer_output
                else:
                    x = layer_output

            return x

    def print_gradients(model, x):
        output = model(x)
        target = torch.tensor([[0.0]])

        loss = nn.MSELoss()
        loss = loss(output, target)

        # calculate gradients
        loss.backward()

        for name, param in model.named_parameters():
            if "weight" in name:
                print(f"{name} has a gradient mean of {param.grad.abs().mean().item()}")

    layer_sizes = [3, 3, 3, 3, 3, 1]
    sample_input = torch.tensor([[1.0, 0.0, -1.0]])
    torch.manual_seed(123)
    model_without_shortcut = ExampleDeepNeuralNet(layer_sizes, use_shortcut=False)
    # shows vanishing gradients problem
    print("no shortcut:")
    print_gradients(model_without_shortcut, sample_input)
    print()

    # hmm... when I forgot to add `torch.manual_seed()` I got different numbers
    # (obviously), but they appeared to show the vanishing gradient problem still.
    torch.manual_seed(123)
    model_with_shortcut = ExampleDeepNeuralNet(layer_sizes, use_shortcut=True)
    print("shortcut:")
    print_gradients(model_with_shortcut, sample_input)


def example_transformer_block():
    # ch 4

    torch.manual_seed(123)
    x = torch.rand(2, 4, 768)
    block = TransformerBlock(GPT_CONFIG_124M)
    output = block(x)

    print("Input shape:", x.shape)
    print("Output shape:", output.shape)


def example_gpt_model():
    # ch 4
    torch.manual_seed(123)
    model = GPTModel(GPT_CONFIG_124M)

    batch = []
    txt1 = "Every effort moves you"
    txt2 = "Every day holds a"

    tokenizer = tiktoken.get_encoding("gpt2")
    batch.append(torch.tensor(tokenizer.encode(txt1)))
    batch.append(torch.tensor(tokenizer.encode(txt2)))
    batch = torch.stack(batch, dim=0)

    out = model(batch)
    print("Output shape:", out.shape)

    nparams = sum(p.numel() for p in model.parameters())
    print(f"Model parameters: {nparams:,}")


def example_text_generation():
    # ch 4
    start_context = "Hello, I am"
    tokenizer = tiktoken.get_encoding("gpt2")
    encoded = tokenizer.encode(start_context)
    encoded_tensor = torch.tensor(encoded).unsqueeze(0)

    torch.manual_seed(123)
    model = GPTModel(GPT_CONFIG_124M)
    # put in eval mode
    model.eval()

    out = generate_text_simple(
        model=model,
        idx=encoded_tensor,
        max_new_tokens=6,
        # max_new_tokens=10,
        context_size=GPT_CONFIG_124M["context_length"],
    )
    decoded_text = tokenizer.decode(out.squeeze(0).tolist())
    print(decoded_text)


def example_text_to_token_ids():
    start_content = "Every effort moves you"
    tokenizer = tiktoken.get_encoding("gpt2")

    torch.manual_seed(123)
    model = GPTModel(GPT_CONFIG_124M)
    model.eval()
    token_ids = generate_text_simple(
        model=model,
        idx=text_to_token_ids(start_content, tokenizer),
        max_new_tokens=10,
        context_size=GPT_CONFIG_124M["context_length"],
    )
    print("Output:", token_ids_to_text(token_ids, tokenizer))


def example_training():
    # ch 5
    torch.manual_seed(123)
    model = GPTModel(GPT_CONFIG_124M)

    train_data = the_verdict
    train_ratio = 0.9
    split_idx = int(train_ratio * len(train_data))
    train_data = the_verdict[:split_idx]
    val_data = the_verdict[split_idx:]

    train_loader = create_dataloader_v1(
        train_data,
        batch_size=2,
        max_length=GPT_CONFIG_124M["context_length"],
        stride=GPT_CONFIG_124M["context_length"],
        drop_last=True,
        shuffle=True,
    )

    val_loader = create_dataloader_v1(
        val_data,
        batch_size=2,
        max_length=GPT_CONFIG_124M["context_length"],
        stride=GPT_CONFIG_124M["context_length"],
        drop_last=False,
        shuffle=False,
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    train_loss = calc_loss_loader(train_loader, model, device)
    val_loss = calc_loss_loader(val_loader, model, device)
    print("Training loss:", train_loss)
    print("Validation loss:", val_loss)

    optimizer = torch.optim.AdamW(model.parameters(), lr=0.0004, weight_decay=0.1)
    num_epochs = 10
    train_losses, val_losses, tokens_seen = train_model_simple(
        model,
        train_loader,
        val_loader,
        optimizer,
        device,
        num_epochs=num_epochs,
        eval_freq=5,
        eval_iter=1,
        start_context="Every effort moves you",
    )


if __name__ == "__main__":
    # example_data_loader()
    # example_embedding()
    # example_embedding_bigger()
    # example_self_attention()
    # example_self_attention2()
    # example_multi_head_attention()
    # example_dummy_gpt()
    # example_layer_normalization()
    # example_layer_normalization_by_module()
    # example_relu_versus_gelu()
    # example_feedforward()
    # example_shortcut_connections()
    # example_transformer_block()
    # example_gpt_model()
    # example_text_generation()
    # example_text_to_token_ids()
    example_training()
