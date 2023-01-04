# WAL network

import os
os.environ['PATH']
import sys

# path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# print(path)
# sys.path.insert(0, path)

import geopandas as gpd
import pandas as pd
import time

from config import config as cfg
from config import funcs as f


def networkT2_main():
    water_node_id = "node_id"
    water_line_id = "CENTRELINE"
    sewer_node_id = "dcpCode"
    prefix = "WAL"

    def prepare_water_data():
        path = cfg.type2_water
        water_data = f.load_data(path)
        print("Wata data ", water_data.shape)

        PROJ_CRS = f.set_project_crs(water_data)
        water_data_df = f.multiline_to_linestring(water_data, PROJ_CRS)
        startnodes_gdf = f.add_beginpoints(water_data_df, PROJ_CRS)
        endnodes_gdf = f.add_endpoints(water_data_df, PROJ_CRS)

        water_nodes_df = f.unify_nodes(
            startnodes_gdf, endnodes_gdf, water_line_id, prefix, PROJ_CRS
        )
        water_final = f.add_node_ids_to_edges(
            startnodes_gdf, endnodes_gdf, water_nodes_df, water_line_id, water_data
        )

        return water_final, water_nodes_df, PROJ_CRS

    water_final, water_nodes_df, PROJ_CRS = prepare_water_data()

    def prepare_sewer_data():
        wal_disharge_pts = f.load_data(
            cfg.type2_sewer_nodes
        )
        sewer_cols = [
            "dcpState",
            "dcpCode",
            "dcpName",
            "dcpWaterBo",
            "dcpRecei_1",
            "dcpBeginLi",
            "dcpEndLife",
            "dcpWFDRBD",
            "rptMStateK",
            "geometry",
        ]
        sewer_nodes = (
            wal_disharge_pts[sewer_cols].query('rptMStateK == "BE"').to_crs(PROJ_CRS)
        )
        return sewer_nodes

    sewer_nodes = prepare_sewer_data()

    def join_water_and_sewer():

        sewer_water_df = sewer_nodes.sjoin_nearest(water_final).merge(
            water_final["geometry"], left_on="index_right", right_index=True
        )

        def nodesGDF_and_waterGDF(
            sewer_node_id, water_line_id, sewer_water_df, PROJ_CRS
        ):
            sewer_water_df["new_points"] = f.get_nearest_point(
                sewer_water_df, "geometry_y", "geometry_x"
            )
            print("Sewer water df :", sewer_water_df.shape)

            connection_nodes_gdf = gpd.GeoDataFrame(
                (
                    sewer_water_df[[sewer_node_id, water_line_id, "new_points"]].rename(
                        columns={"new_points": "geometry"}
                    )
                ),
                geometry="geometry",
                crs=PROJ_CRS,
            )
            water_gdf = gpd.GeoDataFrame(
                (
                    sewer_water_df[[water_line_id, "geometry_y"]].rename(
                        columns={"geometry_y": "geometry"}
                    )
                ),
                geometry="geometry",
                crs=PROJ_CRS,
            )
            return connection_nodes_gdf, water_gdf

        connection_nodes_gdf, water_gdf = nodesGDF_and_waterGDF(
            sewer_node_id, water_line_id, sewer_water_df, PROJ_CRS
        )
        return connection_nodes_gdf, water_gdf

    connection_nodes_gdf, water_gdf = join_water_and_sewer()

    def project_and_split_lines():
        nodes_gdf = connection_nodes_gdf.copy()
        nodes_gdf["coords"] = f.get_point_coords(connection_nodes_gdf)
        water_gdf["coords"] = water_gdf.apply(
            lambda row: f.get_line_coords(row.geometry), axis=1
        )
        splitlines_df = f.split_lines(water_gdf, nodes_gdf, water_line_id, PROJ_CRS)
        return splitlines_df

    splitlines_df = project_and_split_lines()

    def add_splitlines_to_waterGDF():

        final_nodes_combined = f.combine_nodes(
            water_nodes_df, connection_nodes_gdf, sewer_node_id
        )
        waternodes = f.get_new_water_nodes(
            final_nodes_combined, water_nodes_df, prefix, PROJ_CRS
        )

        final_waternodes = pd.merge(
            waternodes,
            sewer_nodes[["dcpCode", "dcpName", "dcpWaterBo", "dcpState"]],
            left_on="sewernode_id",
            right_on=sewer_node_id,
            how="left",
        )

        splitlines_with_ids = f.line_segments_start_end_ids(
            splitlines_df, waternodes, water_line_id, water_node_id, PROJ_CRS
        )

        splitlines_final = f.get_new_water_unique_ID(
            splitlines_with_ids, water_final, water_line_id, PROJ_CRS
        )

        segments_to_water = f.merge_segments_to_water(
            splitlines_df, splitlines_final, water_final, water_line_id, PROJ_CRS
        )

        print("Final water data :", segments_to_water.shape)
        return final_waternodes, segments_to_water

    final_waternodes, segments_to_water = add_splitlines_to_waterGDF()


if __name__ == "__main__":
    initialTime = time.time()

    networkT2_main()

    print("Done")
    finishTime = time.time()
    print(f"Time taken: {finishTime - initialTime}")
    print("********************************************************")
