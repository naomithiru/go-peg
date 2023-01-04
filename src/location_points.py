# # Point Locations of Interest

# Locations of interest refer to any phonomenon occuring along the networks that have the potential to affect or be affected by pollution.
# The locations of interest have surface geometry, either point or polygon.
# This notebook develops the methodology for point locations of interest.
# For working with point locations of interests, we will project a point to the nearest water geometry, applying a threshold distance to exclude points that are too far away from the nearest water geometry.
# **Load water data to perform the intersection and identify the points of intersection between water and locations of iterest**


import os
import sys

path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
print(path)
sys.path.insert(0, path)

import geopandas as gpd
import pandas as pd
import numpy as np
import time

from processing import config as cfg
from processing import funcs as f
from processing.config import data_dest, data_src

print("********************************************************")

def main():
    def load_water_data():
        water_data = f.load_data(data_dest / "vl_water_PROCESSED_V2.shp")

        PROJ_CRS = f.set_project_crs(water_data)

        f.check_multiline(water_data)
        return water_data, PROJ_CRS

    water_data, PROJ_CRS = load_water_data()


    def load_locations_data():

        point_locations = f.load_data(data_src / "flanders_locations/Production and industrial facilities/ProductionInstallation_points.shp")

        point_locations = point_locations.to_crs(PROJ_CRS) #use water crs on other datasets
        return point_locations

    point_locations = load_locations_data()


    def project_points_to_lines():
        water_cols = ['VHAS', 'NAAM', 'start_ID', 'end_ID', 'geometry']
        loc_cols = ['gml_id', 'identifier', 'name', 'localId', 'geometry']

        projected_df = (gpd.sjoin_nearest(
                    point_locations[loc_cols], 
                    water_data[water_cols])
                    .merge(water_data['geometry'], left_on="index_right", right_index=True)
                    .drop(columns=['index_right'])
                    .rename(columns={'index_left': 'ID'})
                    .reset_index(drop=True)
                    ) #merge operation adds the geometry column
        #get distance of location of interest from water. With this distance we can filter out locations by distance from water
        projected_df["distance"] = projected_df.apply(lambda r: r["geometry_x"].distance(r["geometry_y"]), axis=1)
        # revisit and figure out why there are duplicates in the dataframe
        projected_df = projected_df.drop_duplicates(subset=['geometry_x'])

        return projected_df

    projected_df = project_points_to_lines()


    def get_reference_points():
        projected_df['loc_nodes'] = f.get_nearest_point(projected_df, 'geometry_y', 'geometry_x')
        #consider retaining the original point geometry for the linear referenced df.
        gdf = gpd.GeoDataFrame(projected_df, geometry='loc_nodes', crs=PROJ_CRS ).drop(['geometry_x'], axis=1)

        distances = []
        for row in gdf.iterrows():
            dist = row[1]['geometry_y'].project(row[1]['loc_nodes'])
            distances.append(dist)

        gdf['ref_at'] = distances

        point_locations_df = gdf.drop(['geometry_y', 'start_ID', 'end_ID'], axis=1) #.rename(columns={'loc_nodes': 'geometry'})
        final_crs = point_locations_df.crs
        print("point_locations_df: ", point_locations_df.shape)
        print('final_crs:', final_crs)
        return point_locations_df, final_crs

    point_locations_df, final_crs = get_reference_points()


if __name__ == "__main__":
    initialTime = time.time()

    main()
    
    #point_loc2.to_file(r"..\data_transform\vl_point_locations.shp")
    print("Done")
    finishTime = time.time()
    print(f"Time taken: {finishTime - initialTime}")
    print("**************************************************************")
