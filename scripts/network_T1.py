# VL network

import time
import pandas as pd
import geopandas as gpd

import os
import sys

path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
print(path)
sys.path.insert(0, path)

from processing import funcs as f
from processing import config as cfg


def networkT1_main():
    sewer_node_id = "CODEKOPPNT"
    water_line_id = "VHAS"
    water_node_id = "node_id"
    prefix = "VL"

    def prepare_water_data():

        water_data = f.load_data(cfg.type1_water)

        PROJ_CRS = f.set_project_crs(water_data)

        water_data = f.multiline_to_linestring(water_data, PROJ_CRS)

        startnodes_gdf = f.add_beginpoints(water_data, PROJ_CRS)
        endnodes_gdf = f.add_endpoints(water_data, PROJ_CRS)

        water_nodes_df = f.unify_nodes(
            startnodes_gdf, endnodes_gdf, water_line_id, prefix, PROJ_CRS
        )

        water_final = f.add_node_ids_to_edges(
            startnodes_gdf, endnodes_gdf, water_nodes_df, water_line_id, water_data
        )
        return water_final, water_nodes_df, PROJ_CRS


    def prepare_sewer_data():
        sewer_edges = f.load_data(cfg.type1_sewer_edges)

        sewer_nodes = f.load_data(cfg.type1_sewer_nodes)

        if sewer_points == None:
            return sewer_nodes, sewer_edges
        else:
            sewer_points = f.load_data(cfg.type1_sewer_points)
        return sewer_points, sewer_nodes, sewer_edges

    sewer_points, sewer_nodes, sewer_edges = prepare_sewer_data()


    def get_sewer_nodes():
        full_sewer_nodes = pd.merge(
            sewer_nodes,
            sewer_points,
            left_on="NRKPNT",
            right_on=sewer_node_id,
            how="left",
        )
        return full_sewer_nodes


    def join_water_and_sewer():
        external_nodes = f.find_external_nodes(sewer_edges, "BEGINKPNT", "EINDKPNT")

        ext_nodes_df = (
            sewer_points.query("CODEKOPPNT in @external_nodes")
            .query("VHAS != 0")
            .drop_duplicates(subset=sewer_node_id)
            .drop(columns=["geometry"])
            .merge(
                sewer_nodes[["NRKPNT", "geometry"]],
                left_on=sewer_node_id,
                right_on="NRKPNT",
            )
            .drop(columns=["NRKPNT"])
            .drop_duplicates(subset="geometry")
        )
        water_final_cols = [water_line_id, "geometry"]
        ext_nodes_cols = ["NRHPNT", sewer_node_id, water_line_id, "geometry"]
        sewer_water_df = (
            ext_nodes_df[ext_nodes_cols]
            .merge(water_final[water_final_cols], on=water_line_id, how="left")
            .drop_duplicates(subset="geometry_x", keep="first")
            .query("geometry_y.notnull()")
            .assign(
                new_points=lambda x: f.get_nearest_point(x, "geometry_y", "geometry_x")
            )
        )
        print(sewer_water_df.shape)

        sewer_water_df = gpd.GeoDataFrame(
            sewer_water_df, geometry="new_points", crs=PROJ_CRS
        ).drop_duplicates(subset="new_points")

        conn_node_cols = ["NRHPNT", sewer_node_id, water_line_id, "new_points"]
        water_cols = [water_line_id, sewer_node_id, "geometry_y"]
        connection_nodes_df = (
            sewer_water_df[conn_node_cols]
            .rename(columns={"new_points": "geometry"})
            .reset_index(drop=True)
        )

        connection_nodes_gdf = gpd.GeoDataFrame(
            connection_nodes_df, geometry="geometry", crs=PROJ_CRS
        )
        print("Connection_nodes_df: ", connection_nodes_gdf.shape)

        water_df = (
            sewer_water_df[water_cols]
            .rename(columns={"geometry_y": "geometry"})
            .reset_index(drop=True)
        )
        water_gdf = gpd.GeoDataFrame(water_df, geometry="geometry", crs=PROJ_CRS)
        return connection_nodes_gdf, water_gdf, sewer_water_df


    def project_and_split_lines():

        nodes_gdf = connection_nodes_gdf.copy()
        nodes_gdf["coords"] = f.get_point_coords(nodes_gdf)

        water_gdf["coords"] = water_gdf.apply(
            lambda row: f.get_line_coords(row.geometry), axis=1
        )
        print(water_gdf.shape)
        splitlines_df = f.split_lines(water_gdf, nodes_gdf, water_line_id, PROJ_CRS)
        return splitlines_df


    def add_splitlines_to_waterGDF():
        water_nodes_df["source"] = "water_node"

        connection_nodes = (
            connection_nodes_gdf[[sewer_node_id, "geometry"]]
            .rename(columns={sewer_node_id: water_node_id})
            .assign(source="connection_node")
        )

        final_nodes_combined = (
            pd.concat([water_nodes_df, connection_nodes])
            .drop_duplicates(subset="geometry", keep="first")
            .reset_index(drop=True)
        )

        waternodes = f.get_new_water_nodes(
            final_nodes_combined, water_nodes_df, prefix, PROJ_CRS
        )

        final_waternodes = (
            waternodes.merge(
                full_sewer_nodes[["STATUS", "LBLTYPE", "NRKPNT"]],
                left_on="sewernode_id",
                right_on="NRKPNT",
                how="left",
            )
            .drop_duplicates(subset="geometry", keep="first")
            .reset_index(drop=True)
        )

        node_id = water_node_id
        line_id = water_line_id
        splitlines_with_ids = f.line_segments_start_end_ids(
            splitlines_df,
            waternodes[["geometry", water_node_id]],
            line_id,
            node_id,
            PROJ_CRS,
        )

        splitlines_final = f.get_new_water_unique_ID(
            splitlines_with_ids, water_final, water_line_id, PROJ_CRS
        )

        segments_to_water = f.merge_segments_to_water(
            splitlines_df, splitlines_final, water_final, water_line_id, PROJ_CRS
        )
        print("Segments to water: ", segments_to_water.shape)
        return final_waternodes, segments_to_water


    water_final, water_nodes_df, PROJ_CRS = prepare_water_data()
    sewer_points, sewer_nodes, sewer_edges = prepare_sewer_data()
    full_sewer_nodes = get_sewer_nodes()
    connection_nodes_gdf, water_gdf, sewer_water_df = join_water_and_sewer()
    splitlines_df = project_and_split_lines()
    final_waternodes, segments_to_water = add_splitlines_to_waterGDF()




if __name__ == "__main__":
    initialTime = time.time()

    networkT1_main()
    
    print("Done")
    finishTime = time.time()
    print(f"Time taken: {finishTime - initialTime}")
    print("**************************************************************")
