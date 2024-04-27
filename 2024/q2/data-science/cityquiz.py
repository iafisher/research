import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.cluster import KMeans, SpectralClustering
from sklearn.naive_bayes import CategoricalNB, GaussianNB, MultinomialNB


def silly_world_map():
    df = city_data()
    sns.scatterplot(x="longitude", y="latitude", data=df, hue="quiz", legend=False)
    plt.show()


def classify_quizzes():
    # guess a quiz based on city coordinates
    print("loading data")
    df = city_data()

    n_clusters = 6  # inhabited continents

    print("kmeans")
    kmeans = KMeans(n_clusters=n_clusters)
    X = df[["longitude", "latitude"]]
    kmeans.fit(X)
    y_kmeans = kmeans.predict(X)

    print("bayes")
    factorized, index = df["quiz"].factorize()
    nb = CategoricalNB()
    nb = GaussianNB()
    nb.fit(X, factorized)
    y_nb = nb.predict(X)

    print("matplotlib")
    fig, axs = plt.subplots(1, 2, figsize=(10, 5))

    # predict random uniformly-distributed points
    rng = np.random.RandomState()
    x_coordinates = np.random.uniform(low=-180, high=180, size=(2000, 1))
    y_coordinates = np.random.uniform(low=-90, high=90, size=(2000, 1))
    Xnew = np.column_stack([x_coordinates, y_coordinates])
    ynew1 = kmeans.predict(Xnew)
    ynew2 = nb.predict(Xnew)

    axs[0].scatter(X["longitude"], X["latitude"], c=y_kmeans, s=5, cmap="Pastel1")
    axs[1].scatter(X["longitude"], X["latitude"], c=y_nb, s=5, cmap="Pastel1")
    axs[0].scatter(Xnew[:, 0], Xnew[:, 1], c=ynew1, s=5, cmap="Pastel1", alpha=0.3)
    axs[1].scatter(Xnew[:, 0], Xnew[:, 1], c=ynew2, s=5, cmap="Pastel1", alpha=0.3)

    plt.show()


def city_data():
    return pd.read_csv("/Users/iafisher/Code/cityquiz-data/cities-from-db.csv")


if __name__ == "__main__":
    sns.set()

    # silly_world_map()
    classify_quizzes()
