import itertools
from pathlib import Path

import matplotlib.pyplot as plt
import mnist
import numpy as np
import pandas as pd
from tensorflow import keras
from tensorflow.keras.layers import Dense, Input
from tensorflow.keras.models import Sequential
from tensorflow.keras.utils import to_categorical


def open_mnist(path):
    with open(path, "rb") as fd:
        return mnist.parse_idx(fd)


# downloaded from https://www.kaggle.com/datasets/hojjatk/mnist-dataset?resource=download
# as http://yann.lecun.com/exdb/mnist/ no longer works
train_images = open_mnist("mnist/train-images.idx3-ubyte")
train_labels = open_mnist("mnist/train-labels.idx1-ubyte")
test_images = open_mnist("mnist/t10k-images.idx3-ubyte")
test_labels = open_mnist("mnist/t10k-labels.idx1-ubyte")

normalize = lambda x: (x / 255) - 0.5
train_images = normalize(train_images)
test_images = normalize(test_images)

flatten = lambda x: x.reshape((-1, 784))
train_images = flatten(train_images)
test_images = flatten(test_images)


def basic_model():
    model = Sequential(
        [
            Dense(64, activation="relu", input_shape=(784,)),
            Dense(64, activation="relu"),
            Dense(10, activation="softmax"),
        ]
    )
    model.compile(
        optimizer="adam", loss="categorical_crossentropy", metrics=["accuracy"]
    )

    model_path = Path("model.weights.h5")
    if model_path.exists():
        model.load_weights(model_path)
    else:
        model.fit(train_images, to_categorical(train_labels), epochs=5, batch_size=32)
        model.save_weights(model_path)

    return model


def create_model(hidden_layers, neurons):
    layers = []
    layers.append(Input((784,)))

    for _ in range(hidden_layers):
        layers.append(Dense(neurons, activation="relu"))

    layers.append(Dense(10, activation="softmax"))

    model = Sequential(layers)
    model.compile(
        optimizer="adam", loss="categorical_crossentropy", metrics=["accuracy"]
    )

    model.fit(
        train_images,
        to_categorical(train_labels),
        epochs=5,
        batch_size=32,
        verbose=0,
    )
    return model


layer_count_options = [1, 2, 3, 4]
# layer_count_options = [1, 2]
neuron_count_options = [16, 32, 64, 128]
# neuron_count_options = [16, 32]

layers_list = []
neurons_list = []
accuracy_list = []
for layer_count, neuron_count in itertools.product(
    layer_count_options, neuron_count_options
):
    print()
    print(f"layers: {layer_count}, neurons: {neuron_count}")
    model = create_model(layer_count, neuron_count)
    _, accuracy = model.evaluate(test_images, to_categorical(test_labels))

    # import random
    # accuracy = random.random()

    layers_list.append(layer_count)
    neurons_list.append(neuron_count)
    accuracy_list.append(accuracy)

df = pd.DataFrame(
    {"layers": layers_list, "neurons": neurons_list, "accuracy": accuracy_list}
)

# for each layer count, plot accuracy against number of neurons


def bar_graphs():
    fig = plt.figure()
    fig.subplots_adjust(hspace=0.8)  # vertical padding

    rows = len(layer_count_options)
    min_accuracy = min(accuracy_list)
    for i, layer_count in enumerate(layer_count_options, start=1):
        df1 = df[df["layers"] == layer_count]
        ax = fig.add_subplot(rows, 1, i)
        ax.bar(df1["neurons"].astype(str), df1["accuracy"])
        ax.set_xlabel("neurons")
        ax.set_title(f"layers={layer_count}")
        ax.set_ylim(min_accuracy, 1.0)
        ax.set_yticks(np.linspace(min_accuracy, 1.0, 20))

    plt.show()


def line_graphs():
    for layer_count in layer_count_options:
        df1 = df[df["layers"] == layer_count]
        plt.plot(
            df1["neurons"].astype(str), df1["accuracy"], label=f"layers={layer_count}"
        )

    min_accuracy = min(accuracy_list)
    plt.ylim(min_accuracy, 1.0)
    plt.ylabel("accuracy")
    plt.xlabel("neurons")
    plt.legend()
    plt.show()


line_graphs()

"""
Findings:

- Accuracy always increases after adding more neurons (except layers = 1, neurons = 64 --> 128)
- Relationship between number of layers and accuracy is less clear:
    - for neurons = 16, 2 layers is best (and 4 layers is by far the worst)
    - for neurons = 32, 1 layer is best (narrowly better than 3 layers)
    - for neurons = 64, 1 layer is best
    - for neurons = 128, 3 layers is best (and highest accuracy overall)

"""
