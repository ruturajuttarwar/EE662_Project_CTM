## network properties
BROADCAST_NET_ADDR = 255
BROADCAST_NODE_ADDR = 255



## node properties
NODE_TX_RANGE = 100  # transmission range of nodes
NODE_ARRIVAL_MAX = 200  # max time to wake up
NODE_STARTUP_DELAY = 5  # seconds - delay before all nodes start routing (allows visualization of all nodes first)


## simulation properties
SIM_NODE_COUNT = 100  # noce count in simulation
SIM_NODE_PLACING_CELL_SIZE = 75  # cell size to place one node
SIM_DURATION = 5000  # simulation Duration in seconds
SIM_TIME_SCALE = 0.00001  #  The real time dureation of 1 second simualtion time
SIM_TERRAIN_SIZE = (1400, 1400)  #terrain size
SIM_TITLE = 'Data Collection Tree'  # title of visualization window
SIM_VISUALIZATION = True  # visualization active
SCALE = 1  # scale factor for visualization


## application properties
HEARTH_BEAT_TIME_INTERVAL = 10  # Reduced from 100 to help yellows discover registered nodes quickly
REPAIRING_METHOD = 'FIND_ANOTHER_PARENT' # 'ALL_ORPHAN', 'FIND_ANOTHER_PARENT'
EXPORT_CH_CSV_INTERVAL = 10  # simulation time units;
EXPORT_NEIGHBOR_CSV_INTERVAL = 10  # simulation time units;

## CTM-AdHoc Hybrid Routing properties
ENABLE_HYBRID_ROUTING = True  # Enable CTM-AdHoc hybrid routing (True) or use pure tree routing (False)
NEIGHBOR_TIMEOUT = 30  # seconds - remove neighbors that haven't sent heartbeat within this time

## Multi-Hop Neighbor Discovery properties
ENABLE_MULTIHOP_NEIGHBORS = True  # Enable multi-hop neighbor table sharing
MAX_NEIGHBOR_HOPS = 2  # Maximum hops for neighbor discovery (1=direct only, 2=2-hop, etc.)
NEIGHBOR_SHARE_INTERVAL = 2000  # seconds - how often to broadcast neighbor table
NEIGHBOR_SHARE_TTL = 3  # Maximum hops for neighbor table sharing messages
MULTIHOP_NEIGHBOR_TIMEOUT = 45  # seconds - multi-hop neighbors expire faster than direct neighbors

## Cluster Management properties
MIN_CLUSTER_SIZE = 6  # Minimum registered nodes per cluster head (CH must have at least this many members)
YELLOW_NODE_CH_TIMEOUT = 120  # Seconds - base timeout for yellow node to become CH (INCREASED to reduce CH count)
YELLOW_NODE_CH_TIMEOUT_VARIANCE = 60  # Seconds - random variance added to base timeout (prevents simultaneous promotion)
MIN_CH_DISTANCE = 60  # Minimum distance between cluster heads (safety check for overlapping)
ENABLE_CH_HANDOFF = False  # Allow cluster head role to move to better candidates (DISABLED - causes issues)
CH_HANDOFF_INTERVAL = 200  # Seconds - how often to check for better CH candidates

## Router Layer properties
ENABLE_ROUTER_LAYER = True              # Enable router-based cluster expansion
##ROUTER_PROMOTION_DISTANCE = 0.4         # 0.9 * NODE_TX_RANGE to detect edge nodes
ROUTER_HEARTBEAT_INTERVAL = 60          # Seconds - router heartbeat interval
##ROUTER_COLOR = (0.6, 0.2, 0.8)         # Purple/magenta color for routers

