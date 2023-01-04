# Polygon Locations of Interest
# Locations of Interest refer to any phonomenon occuring along the networks that have the potential to affect or be affected by pollution.
# The locations of interest have surface geometry, either point or polygon.
# Given a certain buffer distance, a location of interest can be identified based on whether it overlaps with a section of the network.


## Working with polygon locations of interest
# For working with polygon locations of interests, we will apply a buffer to the polygon. 
# If part of the water network falls within this buffer zone, it is identified, and the points of intersection, 
# i.e. starts-at point and ends-at point, following the direction of the flow of water, are extracted and recorded.

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



from shapely.geometry import Point, LineString, MultiLineString, MultiPoint
from shapely import wkt
from shapely.ops import nearest_points
import shapely.wkt



def main():

    def load_water_data():
        water_data = f.load_data(data_dest / "vl_water_PROCESSED_V2.shp")

        PROJ_CRS = f.set_project_crs(water_data)

        f.check_multiline(water_data)
        return water_data, PROJ_CRS

    water_data, PROJ_CRS = load_water_data()



    def load_locations_data():
        poly_locations = f.load_data(data_src / "flanders_locations/Production and industrial facilities\ProductionInstallation_polygons.shp")
        poly_locations = poly_locations.to_crs(PROJ_CRS) #use water crs on other datasets
        return poly_locations

    poly_locations = load_locations_data()



    def create_buffer():
        poly_buffers = f.create_buffers(poly_locations, 100)
        buffers_df = poly_buffers[['RecId', 'localId', 'namespace', 'buffer_zone']]
        buffers_gdf = gpd.GeoDataFrame(buffers_df, geometry='buffer_zone')
        return buffers_gdf

    buffers_gdf = create_buffer()

    # **Load water data to perform the intersection and identify the points of intersection between water and locations of iterest**
    # To linearly reference a location of interest(polygon) onto a water network(linestring), we need to perform an overlay of the polygons onto the linesrings.
    # The resulting geometry is a linestring that falls within the boundaries of a polygon, with all the properties of the original linestring and polygon.
    # With this data, we can extract the point where the water intersects the polygon.
    def clip_to_buffer():
        water_truncated = water_data[['VHAS', 'geometry']]

        clipped_water_df = f.clipGDF_keepgeomtyp_line(water_truncated, buffers_gdf)

        assert clipped_water_df.VHAS.nunique() == clipped_water_df.geometry.nunique()
        return clipped_water_df
    clipped_water_df = clip_to_buffer()

    #clipped.to_file(r"C:\Workdir\Develop\TR_USECASE\data_transform\clipped.shp")
    # Add begin and end points to the linestrings. These mark the start_at points and end_at point of the location of interest on a water network

    # def get_start_end_points_df():

    #     clipped_df = clipped_water_df.copy()
    #     clipped_df['start_point'] = f.get_beginpoints_list(clipped_df)
    #     clipped_df['end_point'] = f.get_endpoints_list(clipped_df)
 

    # # def get_start_points_df():
    #     start_pts = clipped_df[['VHAS', 'start_point']].merge(water_data[['VHAS', 'geometry']], how='left', on='VHAS')
    #     start_pts['start_point'] = clipped_df['start_point'].apply(wkt.loads)
    #     start_pts = gpd.GeoDataFrame(start_pts, geometry='start_point')
    #     # return start_pts

    # # start_pts = get_start_points_df()

    #     start_pts['new_start_points'] = f.get_nearest_point(start_pts, 'geometry', 'start_point')
    #     start_pts['from_distance'] = start_pts.apply(lambda row: row.geometry.project(row.new_start_points), axis=1)
    #     print("Start points done")
    # # start_pts
    # # def get_end_points_df():
    #     end_pts = clipped_df[['VHAS', 'end_point']].merge(water_data[['VHAS', 'geometry']], how='left', on='VHAS')
    #     end_pts['end_point'] = clipped_df['end_point'].apply(wkt.loads)
    #     end_pts = gpd.GeoDataFrame(end_pts, geometry='end_point')
    #     # return end_pts

    # # end_pts = get_end_points_df()

    #     end_pts['new_end_points'] = f.get_nearest_point(end_pts, 'geometry', 'end_point')
    #     end_pts['to_distance'] = end_pts.apply(lambda row: row.geometry.project(row.new_end_points), axis=1)

    #     return start_pts, end_pts

    # start_pts, end_pts = get_start_end_points_df()

    def add_beginpoints(col, df):
        lst = df[col].to_list()
        beginpoints = []
        for item in lst:
                if isinstance(item, LineString):
                    first = Point(item.coords[0])
                    first_precise = shapely.wkt.dumps(first) #, rounding_precision=5)
                    beginpoints.append(first_precise)
                elif isinstance(item, MultiLineString):
                    first = Point(item.boundary[0])
                    first_precise = shapely.wkt.dumps(first) #, rounding_precision=5)
                    beginpoints.append(first_precise)
        return beginpoints


    def add_endpoints(col, df):
        lst = df[col].to_list()
        endpoints = []
        for item in lst:
                if isinstance(item, LineString):
                    last = Point(item.coords[-1])
                    last_precise = shapely.wkt.dumps(last) #, rounding_precision=5)
                    endpoints.append(last_precise)
                elif isinstance(item, MultiLineString):
                    last = Point(item.boundary[-1])
                    last_precise = shapely.wkt.dumps(last) #, rounding_precision=5)
                    endpoints.append(last_precise)
        return endpoints

    clipped_df = clipped_water_df.copy()
    clipped_df['start_point'] = add_beginpoints('geometry', clipped_df)
    clipped_df['end_point'] = add_endpoints('geometry', clipped_df)


    def get_start_points_df():
        start_pts = clipped_df[['VHAS', 'start_point']].merge(water_data[['VHAS', 'geometry']], how='left', on='VHAS')
        start_pts['start_point'] = clipped_df['start_point'].apply(wkt.loads)
        start_pts = gpd.GeoDataFrame(start_pts, geometry='start_point')
        start_pts['new_start_points'] = f.get_nearest_point(start_pts, 'geometry', 'start_point')
        start_pts['from_distance'] = start_pts.apply(lambda row: row.geometry.project(row.new_start_points), axis=1)
        return start_pts

    start_pts = get_start_points_df()
    # start_pts['new_start_points'] = f.get_nearest_point(start_pts, 'geometry', 'start_point')
    # start_pts['from_distance'] = start_pts.apply(lambda row: row.geometry.project(row.new_start_points), axis=1)


    def get_end_points_df():
        end_pts = clipped_df[['VHAS', 'end_point']].merge(water_data[['VHAS', 'geometry']], how='left', on='VHAS')
        end_pts['end_point'] = clipped_df['end_point'].apply(wkt.loads)
        end_pts = gpd.GeoDataFrame(end_pts, geometry='end_point')
        end_pts['new_end_points'] = f.get_nearest_point(end_pts, 'geometry', 'end_point')
        end_pts['to_distance'] = end_pts.apply(lambda row: row.geometry.project(row.new_end_points), axis=1)

        return end_pts

    end_pts = get_end_points_df()
    # end_pts['new_end_points'] = f.get_nearest_point(end_pts, 'geometry', 'end_point')
    # end_pts['to_distance'] = end_pts.apply(lambda row: row.geometry.project(row.new_end_points), axis=1)


    # Merge the two dfs
    def linear_reference():
        """ Merge the start and end points 
            and linearly referencethe points along the water network"""

        linear_reference_df = start_pts[['VHAS', 'new_start_points', 'from_distance']].merge(end_pts[['VHAS', 'new_end_points', 'to_distance']], how='left', on='VHAS')
        # ## Merge locations of interest
        water_polygon = gpd.sjoin(buffers_gdf, water_data[['VHAS', 'geometry']]).reset_index()
        linear_reference_gdf = water_polygon[['RecId', 'localId', 'namespace', 'VHAS', 'buffer_zone']]\
                                .merge(linear_reference_df[['VHAS', 'from_distance', 'to_distance']], how='left', on='VHAS') #\
                                    #.rename(columns={'buffer_zone':'geometry'})
        return linear_reference_gdf

    linear_reference_gdf = linear_reference()
    # linear_reference_gdf.to_file(r"C:\Workdir\Develop\TR_USECASE\data_transform\vl_polygon_loc.shp")
    # linear_reference_gdf2 = linear_reference_gdf.to_crs(epsg=3035)
    # print(linear_reference_gdf.shape)
    # print(linear_reference_gdf.crs)
    # linear_reference_gdf2.to_file(r"C:\Workdir\Develop\TR_USECASE\data_transform\vl_polygon_loc2.shp")

if __name__ == "__main__":
    initialTime = time.time()

    main()
    
    #point_loc2.to_file(r"..\data_transform\vl_point_locations.shp")
    print("Done")
    finishTime = time.time()
    print(f"Time taken: {finishTime - initialTime}")
    print("**************************************************************")