from pathlib import Path
import os


path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
print(path)

data_src = Path(path + '/data/data_preprocess' )
data_dest = Path(path + '/data/data_transform')

type1_water = data_src/"flanders_hydro_network/Wlas.shp"
type1_sewer_edges = data_src/"flanders_sewernetwork/Streng.shp"
type1_sewer_points = data_src/"flanders_sewernetwork/Hydpnt.shp"
type1_sewer_nodes = data_src/"flanders_sewernetwork/Koppnt.shp"


type2_water = data_src/"wal_hydronetwork/MESU__CENTRELINES.shp"
type2_sewer_nodes = data_src/"wal_hydronetwork/disharge_points.shp"


type3_water = data_src/"bxl_networks/bxk_hydronetwork.shp"
type3_sewer_nodes = data_src/"bxl_networks/bxl_uwwtd_discharge.shp"
