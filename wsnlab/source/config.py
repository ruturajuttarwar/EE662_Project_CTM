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
SIM_DURATION = 2000  # simulation Duration in seconds
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
NEIGHBOR_SHARE_INTERVAL = 500  # seconds - how often to broadcast neighbor table
NEIGHBOR_SHARE_TTL = 3  # Maximum hops for neighbor table sharing messages
MULTIHOP_NEIGHBOR_TIMEOUT = 45  # seconds - multi-hop neighbors expire faster than direct neighbors

## Cluster Management properties
MIN_CLUSTER_SIZE = 6  # Minimum registered nodes per cluster head (CH must have at least this many members)
YELLOW_NODE_CH_TIMEOUT = 120  # Seconds - base timeout for yellow node to become CH (INCREASED to reduce CH count)
YELLOW_NODE_CH_TIMEOUT_VARIANCE = 60  # Seconds - random variance added to base timeout (prevents simultaneous promotion)
MIN_CH_DISTANCE = 60  # Minimum distance between cluster heads (safety check for overlapping)

## Router Layer properties
ENABLE_ROUTER_LAYER = True              # Enable router-based cluster expansion
ROUTER_HEARTBEAT_INTERVAL = 20          # Seconds - router heartbeat interval



## Energy Model properties
ENABLE_ENERGY_MODEL = True              # Enable energy consumption model
INITIAL_ENERGY_JOULES = 10000           # Initial energy per node in Joules
TX_ENERGY_PER_BYTE = 0.0001            # Energy consumed per byte transmitted (J/byte)
RX_ENERGY_PER_BYTE = 0.00005           # Energy consumed per byte received (J/byte)
IDLE_ENERGY_PER_SECOND = 0.00001       # Energy consumed per second while idle (J/s)
SLEEP_ENERGY_PER_SECOND = 0.000001     # Energy consumed per second while sleeping (J/s)
ENABLE_PACKET_LOSS = True              # Enable packet loss simulation
PACKET_LOSS_PROBABILITY = 0.1          # Probability that a packet is lost during transmission (0.0-1.0)
ENERGY_SAMPLE_INTERVAL = 100           # Seconds - how often to sample energy state for CSV export


# Node Failure Simulation
ENABLE_NODE_FAILURE = True              # Enable random node failure simulation 
NODE_DOWNTIME_AFTER_CONNECTED = 2000    # Seconds - when ROOT checks to schedule node failures
NUMBER_OF_NODES_TO_FAIL = 5             # Number of random nodes to fail during simulation
NODE_RECOVERY_TIME_AFTER_DOWNTIME = 200 # Seconds - time node stays down before recovery
