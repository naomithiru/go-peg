import geopandas as gpd
import pandas as pd

from shapely.geometry import Point, LineString, MultiPoint, MultiLineString
from shapely import wkt
from shapely.ops import nearest_points
import shapely.wkt

import warnings
from shapely.errors import ShapelyDeprecationWarning

warnings.filterwarnings("ignore", category=ShapelyDeprecationWarning)


def load_data(path):
    """
    Loads the data from the given path,
    and prints the shape and crs of the data.
    """
    data = gpd.read_file(path)
    data = data.drop_duplicates(subset=["geometry"]).reset_index(drop=True)
    print(data.shape)
    data_crs = data.crs
    print("Project crs:", data.crs)
    return data, data_crs


def set_project_crs(df):
    """Sets the crs of the project to the loaded data crs"""
    PROJ_CRS = df.crs
    return PROJ_CRS


def check_multiline(df):
    """This function checks for multiline strings
    from the geometry column in a given dataset"""
    lst = df["geometry"].to_list()
    multiline_count = 0
    for item in lst:
        if isinstance(item, MultiLineString):
            multiline_count += 1
    print("MultiLinesStrings:", multiline_count)


# filter out multilinestring dataset
def multiline_to_linestring(df, PROJ_CRS):
    # filter out multilinestring dataset
    multiline_df = df[df["geometry"].apply(
        lambda x: isinstance(x, MultiLineString))]
    linestrings_df = df[df.geom_type == "LineString"]
    if len(linestrings_df) == len(df):
        print("No multiline strings found")
        return df
    else:
        print("Checking for multiline strings...")
        check_multiline(df)
        # turn multilinestrings into linestrings
        linestrings = []
        for idx, row in multiline_df.iterrows():
            inlines = row.geometry
            outcoords = [list(item.coords) for item in inlines]
            outline = shapely.geometry.LineString(
                [i for sublist in outcoords for i in sublist]
            )
            linestrings.append(outline)
        multiline_gdf = gpd.GeoDataFrame(
            (
                multiline_df.assign(exploded=linestrings)
                .drop(["geometry"], axis=1)
                .rename(columns={"exploded": "geometry"})
                .reset_index(drop=True)
            ),
            geometry="geometry",
            crs=PROJ_CRS,
        )

        gdf = linestrings_df.append(multiline_gdf).reset_index(drop=True)
        print("Checking for multiline strings after...")
        check_multiline(gdf)
    return gdf


def get_beginpoints_list(df):
    lst = df["geometry"].to_list()
    beginpoints = []
    for item in lst:
        first = Point(item.coords[0])
        first_precise = shapely.wkt.dumps(first)
        beginpoints.append(first_precise)
    return beginpoints


def get_endpoints_list(df):
    lst = df['geometry'].to_list()
    endpoints = []
    for item in lst:
        first = Point(item.coords[-1])
        first_precise = shapely.wkt.dumps(first)
        endpoints.append(first_precise)
    return endpoints


def add_beginpoints(df, PROJ_CRS):
    startnodes_gdf = df.copy()
    beginpoints = get_beginpoints_list(startnodes_gdf)

    startnodes_gdf["start_point"] = [wkt.loads(g) for g in beginpoints]
    startnodes_gdf = startnodes_gdf.drop(["geometry"], axis=1).rename(
        columns={"start_point": "geometry"}
    )

    startnodes_gdf = gpd.GeoDataFrame(
        startnodes_gdf, geometry=startnodes_gdf["geometry"], crs=PROJ_CRS
    )  # .drop(columns=[col])
    return startnodes_gdf


def add_endpoints(df, PROJ_CRS):
    endnodes_gdf = df.copy()
    endpoints = get_endpoints_list(endnodes_gdf)

    endnodes_gdf["end_point"] = [wkt.loads(g) for g in endpoints]
    endnodes_gdf = endnodes_gdf.drop(["geometry"], axis=1).rename(
        columns={"end_point": "geometry"}
    )

    endnodes_gdf = gpd.GeoDataFrame(
        endnodes_gdf, geometry=endnodes_gdf["geometry"], crs=PROJ_CRS
    )  # .drop(columns=[col])
    return endnodes_gdf



def unify_nodes(startnodes_gdf, endnodes_gdf, id_col, region, PROJ_CRS):
    """Unifies the startnodes and endnodes into one geometry
    and assigns a unique id to each node"""

    nodes_geom = pd.merge(
        startnodes_gdf[[id_col, "geometry"]],
        endnodes_gdf[[id_col, "geometry"]],
        on="geometry",
        how="outer",
    ).reset_index(drop=True)
    unique_id_df = nodes_geom[["geometry"]
                              ].drop_duplicates().reset_index(drop=True)
    unique_id_df["New_ID"] = range(1, len(unique_id_df) + 1)
    unique_id_df["node_id"] = region + unique_id_df["New_ID"].astype(str)
    gdf = gpd.GeoDataFrame(
        unique_id_df, geometry=unique_id_df["geometry"], crs=PROJ_CRS
    ).drop(columns=["New_ID"])
    return gdf


def extract_nodes_geometry(
        startnodes_gdf,
        endnodes_gdf,
        start_id,
        end_id,
        PROJ_CRS):
    nodes_gdf = (
        pd.merge(
            startnodes_gdf[[start_id, "geometry"]],
            endnodes_gdf[[end_id, "geometry"]],
            on="geometry",
            how="outer",
        )
        .reset_index(drop=True)
        .drop_duplicates(subset=["geometry"])
        .reset_index(drop=True)
    )
    # assign unique ids to the nodes
    start_node_id = (
        nodes_gdf.query(end_id + ".isna()")
        .drop(columns=[end_id])
        .rename(columns={start_id: "node_id"})
    )

    end_node_id = (
        nodes_gdf.query(start_id + ".isna()")
        .drop(columns=[start_id])
        .rename(columns={end_id: "node_id"})
    )

    other_nodes = (
        nodes_gdf.query(start_id + ".notna() & " + end_id + ".notna()")
        .drop(columns=[end_id])
        .rename(columns={start_id: "node_id"})
    )

    # df_list = [start_node_id, end_node_id, other_nodes]
    final_nodes_gdf = gpd.GeoDataFrame(
        (pd.concat([start_node_id, end_node_id, other_nodes]).reset_index(drop=True)),
        geometry="geometry",
        crs=PROJ_CRS,
    )

    return final_nodes_gdf


def add_node_ids_to_edges(
    startnodes_gdf, endnodes_gdf, water_nodes_df, id_col, water_data
):
    """Adds the node ids to the edges. This is done by merging the startnodes and endnodes with the water_nodes_df,
    and then merging them to each other"""

    startnodes_merged = (
        gpd.sjoin(startnodes_gdf, water_nodes_df, how="left")
        .rename(columns={"node_id": "start_ID"})
        .drop("index_right", axis=1)
    )
    endnodes_merged = (
        gpd.sjoin(endnodes_gdf, water_nodes_df, how="left")
        .rename(columns={"node_id": "end_ID"})
        .drop("index_right", axis=1)
    )

    nodes_geom = pd.merge(startnodes_merged, endnodes_merged, on=id_col)
    nodes = nodes_geom[[id_col, "start_ID", "end_ID"]]

    edges_with_nodes = pd.merge(
        water_data, nodes, on=id_col)  # .drop('id', axis=1)
    return edges_with_nodes


def find_external_nodes(df, begin_col, end_col):
    """This function extracts the endpoints of a sewer segment
    that are not beginpoints of another sewer segment"""

    beginpoints = df[begin_col].to_list()
    endpoints = df[end_col].to_list()
    beginpoints_set = set(beginpoints)
    endpoints_set = set(endpoints)
    external_nodes = list(endpoints_set - beginpoints_set)
    return external_nodes


def get_nearest_point(df, line_col, point_col):
    """
    For each point in points_df, find the nearest point in lines_df.
    """
    geoms = []
    for idx, row in df.iterrows():
        destinations = MultiPoint(row[line_col].coords)  # geometry_y
        nearest_geoms = nearest_points(
            row[point_col], destinations)  # geometry_x
        try:
            for coord in destinations:
                if coord == nearest_geoms[1]:
                    geoms.append(coord)
        except ValueError:
            print("No nearest point found for {}".format(row.point_col))
    return geoms


def get_point_coords(gdf):
    """Returns coordinates as tuples"""

    return gdf.geometry.apply(lambda geom: (geom.x, geom.y))


def get_line_coords(line):
    """Returns a list of tuples of coordinates"""

    coords_list = []
    multi_points = MultiPoint(line.coords)

    multi_points_list = [shapely.wkt.dumps(g) for g in multi_points]
    multi_points_geoms = [shapely.wkt.loads(i) for i in multi_points_list]
    for i in multi_points_geoms:
        long, lat = i.x, i.y
        coords_list.append((long, lat))

    return coords_list


# Split function
def get_line_segments(l, points_list):

    """l = linestring, a data structure of a list made up of tuples of coordinates
       points_list = list of points to split the linestring at"""

    idx_list = [
        i for i, item in enumerate(l) if item in points_list
    ]  # compares the two lists and returns the indexes of occurence

    p = [l[i] for i in idx_list]  # get correct order of points list on the line

    super_list = []

    start_idx = 0

    # print("Index list: ", idx_list)
    if len(idx_list) == 1 and (
        p[0] == l[0] or p[0] == l[-1]
    ):  #      (i == 0 or i == len(l)-1) and len(idx_list) == 1:
        print("One split point, at first or last index")
        line_segment = LineString(l)
        super_list.append(line_segment)

    elif len(idx_list) == 2 and (p[0] == l[0] or p[1] == l[-1]):
        print("Two split points, at first and last index")
        line_segment = LineString(l)
        super_list.append(line_segment)

    else:
        # import pdb; pdb.set_trace()
        for i in idx_list:
            # In the case of the first coordinates of a line being a split point but there are other split points
            if i == 0 and len(idx_list) > 1:
                index_list = len(idx_list)
                print(f"First index is a split point, with {index_list} split points")
                continue
            elif i != 0 and len(idx_list) == 1:
                stop_idx = i + 1
                print(f"One split point at index {i}")
                # print('stop_idx:', stop_idx)
                # print('length of list:', len(l))
                if len(l) - stop_idx == 1:
                    last_segment = l #[stop_idx-1: len(l)+1]
                    last_segment_geom = LineString(last_segment)
                    super_list.append(last_segment_geom)
                else:
                    print(f"One split point at index {i}")
                    # # stop_idx = i + 1  # grab list elements until index i
                    # print(f"stop index is {stop_idx}")
                    line_list = l[start_idx:stop_idx]
                    line_segment = LineString(line_list)
                    super_list.append(line_segment)
                    # print('index_list:' ,len(idx_list))
                    # print('stop_idx:', stop_idx)
                    # print('length of list:', len(l))
                    if len(l) > stop_idx:
                        last_segment = l[i: len(l)+1]
                        last_segment_geom = LineString(last_segment)
                        super_list.append(last_segment_geom)

            else:
                print("Many split points")
                stop_idx = i + 1  # grab list elements until index i
                # print(f"stop index is {stop_idx}")

                line_list = l[start_idx:stop_idx]
                line_segment = LineString(line_list)
                super_list.append(line_segment)
                start_idx = (
                    i  # reset the start index to the number of the prevous stop index
                )

                # super list still has one more segment to add
                # print('Super_list:', len(super_list))
                # print('index_list:' ,len(idx_list))
                # print('stop_idx:', stop_idx)
                # print('length of list:', len(l))
                if len(idx_list) - len(super_list)  == 1:
                    print('super list still has one more segment to add')
                    # last_segment = l[stop_idx - 1 : len(l)]
                    last_segment = l[i: len(l)+1]
                    # print('stop_idx:', stop_idx)
                    # print('length of list:', len(l))
                    if stop_idx == len(l):
                        # print("Split point at end of list") # stop index goes beyond the line list
                        break
                    # n = len(l) - len(super_list)
                    # last_segment = l[stop_idx-1:len(l)] # Grab the last segments of the list from the prevous stop_idx-1, to the end of the lin len(l)
                    elif len(l) - stop_idx == 1:
                        del super_list[-1]
                        last_segment = l[i: len(l)+1]
                        last_segment_geom = LineString(last_segment)
                        super_list.append(last_segment_geom)

                    else:
                        last_segment_geom = LineString(last_segment)
                        super_list.append(last_segment_geom)
                        print("Last segment added")
                # elif len(super_list) < len(idx_list):
                #     last_segment = l[stop_idx - 1 : len(l)]

    return super_list


# pass a dataframe to the function
def split_lines(water_gdf, nodes_gdf, water_line_id, PROJ_CRS):

    water_no_duplicates = water_gdf.drop_duplicates(subset=water_line_id)

    groups = nodes_gdf.groupby(water_line_id)

    codes_list = nodes_gdf[water_line_id].to_list()
    unique_code_list = list(set(codes_list))

    all_segments = []
    ids = []

    for num, i in enumerate(unique_code_list):
        points_list = groups.get_group(i).coords.to_list()
        # print("Points list: ", points_list)

        line = water_no_duplicates[water_no_duplicates[water_line_id] == i]["coords"][:1]
        # indx = water_no_duplicates[water_no_duplicates[water_line_id] == i].index [0]

        points_list = groups.get_group(i).coords.to_list()

        line_segments = get_line_segments(*line, points_list)
        num_segments = len(line_segments)

        all_segments.extend(line_segments)
        # ids.append(indx)
        num_unique_ids = [i] * num_segments
        # get group for each unique code
        # group_ids = groups.get_group(i)[unique_id].to_list()

        # assert len(flat_list) == len(water_no_duplicates)
        ids.extend(num_unique_ids)

        print(f"Line: {i}")
        # print(f'len({line_segments}) line_segments added')
        # print(line_segments)
        # all_segments = all_segments.extend(line_segment)

    ## Create dataframe with all segments
    # print(len(all_segments))
    # print(len(ids))
    # ids_list = list(range(len(ids)))
    gdf_segments = gpd.GeoDataFrame(
        list(range(len(all_segments))), geometry=all_segments, crs=PROJ_CRS
        )
    gdf_segments.columns = ["index", "geometry"]
    gdf_segments[water_line_id] = ids
    gdf_segments = gdf_segments.set_index("index")
    gdf_segments = gdf_segments.drop_duplicates(subset="geometry")
    return gdf_segments


def combine_nodes(water_nodes_df, connection_nodes_gdf, unique_id):
    water_nodes_df["source"] = "water_node"

    connection_nodes = (
        connection_nodes_gdf[[unique_id, "geometry"]]
        .rename(columns={unique_id: "node_id"})
        .assign(source="connection_node")
    )

    final_nodes_combined = (
        pd.concat([water_nodes_df, connection_nodes])
        .drop_duplicates(subset="geometry", keep="first")
        .reset_index(drop=True)
    )
    return final_nodes_combined


def add_sewernode_id(row):
    if row["source"] == "connection_node":
        return row["node_id"]
    else:
        return None


def get_new_water_nodes(df, water_nodes_df, prefix, PROJ_CRS):
    df["sewernode_id"] = df.apply(add_sewernode_id, axis=1)

    conn_df = df.query('source == "connection_node"')
    water_nodes = df.query('source == "water_node"')

    nodes_list = water_nodes["node_id"].to_list()
    start_num = max([int(i[len(prefix):]) for i in nodes_list])

    diff = len(df.index) - len(water_nodes_df.index)

    conn_df["node_id"] = range((start_num + 1), (start_num + diff + 1))
    conn_df["node_id"] = prefix + conn_df["node_id"].astype(str)

    new_nodes_gdf = (
        gpd.GeoDataFrame(
            pd.concat([water_nodes, conn_df]), geometry="geometry", crs=PROJ_CRS
        ).reset_index(drop=True)
        # .drop(columns=['index'])
    )
    return new_nodes_gdf


def line_segments_start_end_ids(
    splitlines_df, all_nodes_gdf, line_id, node_id, PROJ_CRS
):
    """Returns the start and end ids of the line segments for a given node id"""

    splitlines_df["coords"] = splitlines_df.apply(
        lambda row: get_line_coords(row.geometry), axis=1
    )  # %time
    all_nodes_gdf["coords"] = get_point_coords(all_nodes_gdf)

    # join linestrings to the nearest node, in this case the node attached to
    # the line
    joined_lines_nodes = gpd.sjoin_nearest(
        splitlines_df, all_nodes_gdf, how="left"
    ).reset_index()

    # identify the nodes that corresponding to the line start and end points
    idx_start = []
    start_id = []
    idx_end = []
    end_id = []

    for idx, row in joined_lines_nodes.iterrows():
        if row.coords_right == row.coords_left[0]:
            idx_start.append(row["index"])
            start_id.append(row[node_id])
        elif row.coords_right == row.coords_left[-1]:
            idx_end.append(row["index"])
            end_id.append(row[node_id])

    start_id_df = (
        pd.DataFrame({"line_index": idx_start, f"start_{node_id}": start_id})
        .merge(
            joined_lines_nodes[["index", node_id, line_id, "geometry"]],
            left_on="line_index",
            right_on="index",
            how="left",
        )
        .drop_duplicates("geometry")
    )

    end_id_df = (
        pd.DataFrame({"line_index": idx_end, f"end_{node_id}": end_id})
        .merge(
            joined_lines_nodes[["index", node_id, line_id, "geometry"]],
            left_on="line_index",
            right_on="index",
            how="left",
        )
        .drop_duplicates("geometry")
    )

    merged_start_end_df = gpd.GeoDataFrame(
        (
            pd.merge(start_id_df, end_id_df, on="geometry", how="outer")
            .drop(
                [
                    "line_index_x",
                    "index_x",
                    "node_id_x",
                    "index_y",
                    "line_index_y",
                    "node_id_y",
                    line_id + "_y",
                ],
                axis=1,
            )
            .rename(
                columns={
                    "start_node_id": "start_ID",
                    "end_node_id": "end_ID",
                    f"{line_id}_x": line_id,
                }
            )
        ),
        geometry="geometry",
        crs=PROJ_CRS,
    )

    return merged_start_end_df


def get_new_water_unique_ID(df, water_final, col, PROJ_CRS):
    """Get unique ID for each new split segment in a dataframe
    Assert that the number of unique IDs is equal to the number of split segments
    """
    # the new split lines need a new unique uniqueID value
    df["num_id"] = df.groupby(col).cumcount() + 1
    df["new_string_id"] = df[col].astype(str) + "_" + df["num_id"].astype(str)

    # assert df[col].nunique() == len(df)
    df = gpd.GeoDataFrame(
        (df.merge(
            water_final,
            on=col,
            how="left") .drop(
            [
                col,
                "num_id",
                "start_ID_y",
                "end_ID_y",
                "geometry_y"],
            axis=1) .rename(
            columns={
                "new_string_id": col,
                "start_ID_x": "start_ID",
                "end_ID_x": "end_ID",
                "geometry_x": "geometry",
            })),
        geometry="geometry",
        crs=PROJ_CRS,
    )
    return df


def merge_segments_to_water(
    split_segments, split_segments_final, water_df, col, PROJ_CRS
):
    """This function merges segments to water polygons"""

    split_segments = split_segments.astype({col: str}, errors="raise")
    split_segments_final = split_segments_final.astype(
        {col: str}, errors="raise")
    water_df = water_df.astype({col: str}, errors="raise")
    # assert split_segments_final[col].nunique() == split_segments_final['geometry'].nunique()
    # assert water_df[col].nunique() == water_df['geometry'].nunique()

    linestrings_to_drop = split_segments[col].to_list()

    water_df_trimmed = water_df.query(
        col + " not in @linestrings_to_drop"
    )  # .reset_index(drop=True)

    # merge the split lines with the original water lines
    merged_df = gpd.GeoDataFrame(
        pd.concat([split_segments_final, water_df_trimmed], ignore_index=True),
        geometry="geometry",
        crs=PROJ_CRS,
    )
    # recalculate lenth of water segments in final df
    merged_df["new_length"] = merged_df["geometry"].apply(lambda x: x.length)

    # assert merged_df['geometry'].nunique() == merged_df[col].nunique()
    return merged_df



def clipGDF_keepgeomtyp_line(gdf, mask):
    """
    Clips Line Geodataframe with Polygon GeoDataFrame

    Input Variables:
    --------------------------------------------------------------------
    gdf
        GeoDataFrame to clip
    mask
        Geodataframe defining clipping extent

    Returns:
    --------------------------------------------------------------------
    clipped GeoDataFrame inclulding only line geometries
    """

    from shapely.geometry import LineString, MultiLineString,GeometryCollection
    clipped_gdf=gpd.clip(gdf,mask)
    clipped_gdf.reset_index(inplace=True,drop=True) #index now newly assigned, old dropped
    
    if isinstance(clipped_gdf,gpd.GeoSeries):
        #print("GeoSeries")
        features_rmv=[] #list to store indexes to features to remove
        GCunpack_list=[] #list to store indexes to features with GeometryCollection
        for idx in range(len(clipped_gdf)):
            #if feature is neither LineString, MultiLineStrin or GeomCollection --> remove
            if not (isinstance(clipped_gdf.iloc[idx],LineString) or isinstance(clipped_gdf.iloc[idx],MultiLineString) or isinstance(clipped_gdf.iloc[idx],GeometryCollection)): 
                features_rmv.append(idx)
            #if feature is GeomCollection --> unpack, remove points and replace feature with new geometry
            elif isinstance(clipped_gdf.iloc[idx],GeometryCollection):
                GCunpack_list.append(idx)

        for idx in GCunpack_list: #iterate over features with Geomcollection
            unpack_list=[]
            #print(clipped_gdf.iloc[idx])
            for geom in clipped_gdf.iloc[idx]: #grab all lines in this GC
                if isinstance(geom,LineString):
                    unpack_list.append(geom)

            if len(unpack_list)>1: #if more than 1 lines --> create MuLineString
                new_geom = MultiLineString(unpack_list)
                clipped_gdf.iloc[idx]= new_geom #insert at index of feature
            elif len(unpack_list)==1: #if 1 line, create LineString
                new_geom = LineString(unpack_list[0])
                clipped_gdf.iloc[idx]=new_geom

        clipped_gdf.drop(features_rmv,inplace=True) #remove all point features
        clipped_gdf.reset_index(inplace=True,drop=True) #reset index

    if isinstance(clipped_gdf,gpd.GeoDataFrame):
        #print("GeoDataFrame")
        features_rmv=[] #list to store indexes to features to remove
        GCunpack_list=[] #list to store indexes to features with GeometryCollection 
        for idx,row in clipped_gdf.iterrows(): #iterate over features
            #if feature is neither LineString, MultiLineStrin or GeomCollection --> remove
            if not (isinstance(clipped_gdf.iloc[idx].geometry,LineString) or isinstance(clipped_gdf.iloc[idx].geometry,MultiLineString) or isinstance(clipped_gdf.iloc[idx].geometry,GeometryCollection)):  
                features_rmv.append(idx)
            #if feature is GeomCollection --> unpack, remove points and replace feature with new geometry
            elif isinstance(clipped_gdf.iloc[idx].geometry,GeometryCollection):
                GCunpack_list.append(idx)


        for idx in GCunpack_list: #iterate over features with Geomcollection
            unpack_list=[]
            for geom in clipped_gdf.iloc[idx].geometry: #grab all lines in this GC
                if isinstance(geom,LineString):
                    unpack_list.append(geom)
            #print('unpacked_list',unpack_list)
            if len(unpack_list)>1: #if more than 1 lines --> create MuLineString
                geom_df = pd.DataFrame({'id':['geometry'],0:[MultiLineString(unpack_list)]}) #create new Dataframe with geometry
                geom_df.set_index('id',inplace=True)
                newline = clipped_gdf.iloc[idx,clipped_gdf.columns != 'geometry'].append(geom_df) #concat new geometry with feature attributes
                clipped_gdf.iloc[idx]=newline[0] #insert at index of feature
            elif len(unpack_list)==1: #if 1 line, create LineString
                geom_df = pd.DataFrame([LineString(unpack_list[0])],index=['geometry'])
                newline = clipped_gdf.iloc[idx,clipped_gdf.columns != 'geometry'].append(geom_df)
                clipped_gdf.iloc[idx]=newline[0]

        clipped_gdf.drop(features_rmv,inplace=True) #remove all point features
        clipped_gdf.reset_index(inplace=True,drop=True) #reset index

    return clipped_gdf



def create_buffers(df, buffer_size):
    """
    Creates a buffer around each point in the given dataframe.
    """
    
    df['buffer_zone'] = df['geometry'].apply(lambda x: x.buffer(buffer_size))
    mergedpolys = []
    for index, row in df.iterrows():
        mergedpoly = row['geometry'].union(row['buffer_zone']).wkt
        mergedpolys.append(wkt.loads(mergedpoly))
    df['mergedpolys'] = mergedpolys

    return df

