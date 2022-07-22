""" docstring
"""

# import
import os
import joblib
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely import geometry
from sklearn import metrics
import matplotlib.pyplot as plt
from sklearn.cluster import DBSCAN
from IPython.display import display
from sklearn.model_selection import train_test_split

# read dataset
def load_dataset(accidents_csv) :
    """ load dataset

    Args : 
        - accidents_csv (str) : data in db/shared absolute or relative path;

    return : 
        - accidents_df (DataFrame) : dataframe of accidents in doi & coi.
    """

    # load
    accidents_df = pd.read_csv(accidents_csv, index_col=[0])

    # necessary columns
    keep_cols = ["lat", "long", "catv"]
    accidents_model_df = accidents_df[keep_cols]
    # display
    display(accidents_model_df.sample(2))
    display(accidents_model_df.dtypes)
    display(accidents_model_df.shape)
    return accidents_model_df

def split_dataset(dataset:pd.DataFrame) :
    """split dataset
    """

    # X, y
    X = dataset[["lat", "long"]].copy()
    y = dataset["catv"].copy()

    # split
    X_train, X_test, y_train, y_test = train_test_split(X, y)

    # display
    display(f"train shape : {X_train.shape}")
    display(f"test shape : {X_test.shape}")

    return X_train, X_test

def train_model(X_train:pd.DataFrame, hyperparam:dict, model_name:str = "DBSCAN") :
    """ train model

    Args :
        - X_train (DataFrame): split_dataset();
        - hyperparam (Dict) : dict of model hyperparameters
        - model_name (Str) : "DBSCAN", scale it for others cases.
    """

    # define model
    if model_name == "DBSCAN" :

        # model hyperparameters
        eps = hyperparam["eps"]
        min_samples = hyperparam["min_samples"]
        metric = hyperparam["metric"]

        # model
        db = DBSCAN(eps=eps, min_samples=min_samples, metric=metric)
        db.fit(X_train)

        # number of clusters
        labels = db.labels_
        indices_clusters = db.core_sample_indices_

        print(f"Number of clusters created : {len(set(labels))}")

        # fill clusters in 
        X_train["cluster"] = db.labels_

        # metrics
        sil_score = round(metrics.silhouette_score(X_train, X_train['cluster']), 3)
        display(f"Silhouette score : {sil_score}")

        # save model
        model_name = "./model.joblib"
        if os.path.exists(model_name) : 
            joblib.dump(db, model_name)
            print(f"{model_name} exported !")

        else : 
            print(f"{model_name} exists !")

        # cluster
        cluster = X_train.copy()
        cluster_gdf = gpd.GeoDataFrame(cluster, 
                        geometry=gpd.points_from_xy(cluster.long, cluster.lat),
                        crs="epsg:4326")

        # save cluster
        cluster_geojson = "./cluster_points.geojson"
        if os.path.exists(cluster_geojson) : 
            cluster_gdf.to_file(cluster_geojson)
            print(f"{cluster_geojson} exported !")

        else : 
            print(f"{cluster_geojson} exists !")

        return cluster, cluster_gdf, sil_score


def plot_clusters(cluster) :
    """plot clusters
    """

    plt.figure(figsize=(9,9))
    plt.scatter(cluster["long"], cluster["lat"], c=cluster["cluster"])
    plt.show()


def stack_cluster(cluster_gdf, cluster_idx) :
    """ organize cluster geometry
    """

    # cluster index
    cluster_indexes = list(set(cluster_gdf["cluster"]))
    cluster_gdf_list = []

    for cluster_idx in cluster_indexes : 
        # recup cluster group
        mask_cluster = cluster_gdf["cluster"] == cluster_idx
        cluster_group_gdf = cluster_gdf[mask_cluster]

        # cluster_group_gdf.shape[0] > 10
        if  cluster_idx!=-1:
            # new cluster
            df_cluster = pd.DataFrame([cluster_idx], columns=["cluster_index"])

            # create polygons from list of point 
            list_geometry = cluster_group_gdf["geometry"].to_list()
            poly = geometry.Polygon([[p.x, p.y] for p in list_geometry])

            # take polygons cover
            # cluster_cover = poly
            cluster_cover = poly.convex_hull

            # covert to gdf
            df_cluster["geometry"] = cluster_cover
            cluster_cover_gdf = gpd.GeoDataFrame(df_cluster, geometry=df_cluster["geometry"], crs="epsg:4326")
            #display(cluster_cover_gdf)

            # saved
            cluster_cover_gdf.to_file(f"./clusters/cluster_polygons_{str(cluster_idx)}.geojson")
            # add
            cluster_gdf_list.append(cluster_cover_gdf)

    # merge geodataframe
    clusters_all_gdf = pd.concat(cluster_gdf_list, axis=0)
    clusters_all_gdf = clusters_all_gdf.reset_index(drop=True)
    print(clusters_all_gdf.shape)

    # save all as cluster_polygons
    clusters_all_gdf.to_file("./cluster_polygons.geojson")

if __name__ == "__main__" :
    # load dataset
    accidents_csv = "../../db/shared/accidents_2R_75.csv"
    accidents_df = load_dataset(accidents_csv)

    # split data
    X_train, X_test = split_dataset(accidents_df)

    # train model@
    model_name = "DBSCAN"
    hyperparam = {
        "eps" : 0.01, 
        "min_samples" : 3, 
        "metric" : "euclidean"
    }
    cluster, cluster_gdf, sil_score = train_model(accidents_df, hyperparam, model_name)

    # plot cluster
    mask_little = cluster["cluster"].isin([-1, 0, 1, 2, 4, 5, 6, 8, 12, 15])
    df_mask = cluster[~mask_little]
    plot_clusters(cluster)

    # stack cluster
    cluster_idx = 22
    stack_cluster(cluster_gdf, cluster_idx)
    


