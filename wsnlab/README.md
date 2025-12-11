# Hierarchical Wireless Sensor Network with Router Layer

## Overview

This is a **Data Collection Tree (DCT)** simulation for a Wireless Sensor Network with **Router Layer** and **CTM-AdHoc Hybrid Routing**. The simulation models how 100 sensor nodes self-organize into a hierarchical network structure where distant cluster heads are connected through automatically promoted router nodes, enabling multi-hop network coverage beyond single-hop range.

---

## What the Simulation Does

### Network Formation
1. **Node Startup** - All 100 nodes appear on the visualization panel, then wake up after a startup delay
2. **Root Election** - One node becomes the ROOT 
3. **Initial Cluster Formation** - Nodes near ROOT join as REGISTERED (green)
4. **Router Promotion** - Distant yellow nodes trigger router nomination from nearby greens
5. **Router Selection** - Parent CH selects closest green as ROUTER based on distance
6. **CH Creation** - ROUTER promotes yellow to CLUSTER_HEAD, extending network reach
7. **Hierarchical Tree** - Process repeats, forming ROOT→ROUTER→CH→REGISTERED hierarchy

### Network Roles
- **ROOT** (Black) - Network coordinator, root of the tree
- **CLUSTER_HEAD** (Blue) - Cluster coordinators, manage member nodes
- **ROUTER** (Orange) - Bridge nodes connecting distant cluster heads
- **REGISTERED** (Green) - Nodes successfully joined a cluster
- **UNREGISTERED** (Yellow) - Nodes searching for a network
- **UNDISCOVERED** (White) - Nodes not yet awake

### Routing Methods (CTM-AdHoc Hybrid)
1. **Direct Mesh** - Send directly to neighbor if in range
2. **Intra-Cluster** - Forward to cluster member
3. **Downward Tree** - Forward down to child cluster
4. **Upward Tree** - Forward up to parent
5. **Multi-Hop** - Use multi-hop neighbors for longer routes

---

## Key Features

### Cluster Management
- **Adaptive Timeouts** - Yellow nodes wait 120-180s before becoming CHs
- **Unlimited Cluster Size** - CHs accept all nodes in range (MAX_CLUSTER_SIZE = 0)
- **Join Retry Logic** - Nodes keep trying to join before becoming CHs
- **Router Layer** - Edge nodes become routers to bridge clusters (prevents overlap)

### Router Layer Implementation
- **Automatic Router Nomination** - Green nodes nominate themselves when yellow broadcasts JOIN_REQUEST
- **Distance-Based Selection** - Parent CH selects closest green as router (prevents overlap)
- **Competitive Nomination** - Multiple greens compete, best one wins based on distance
- **Router Promotion Flow** - Green→ROUTER→requests CH promotion for yellow→Yellow becomes CH
- **Lock Management** - Parent CH locks during promotion, unlocks on completion message
- **Multi-Hop Extension** - Enables cluster heads beyond single-hop range of ROOT

### Network Optimization
- **Multi-Hop Neighbor Discovery** - Nodes learn about 2-hop neighbors
- **Neighbor Table Sharing** - CHs broadcast neighbor information
- **Stale Neighbor Cleanup** - Remove neighbors not heard from in 30s
- **Heartbeat Mechanism** - Periodic announcements every 100s

### Visualization
- **Real-time Display** - Watch network form in real-time
- **Color-coded Roles** - Easy identification of node roles
- **TX Range Visualization** - See transmission ranges of CHs

---

## Configuration

Edit `wsnlab/source/config.py`:

```python
# Network
SIM_NODE_COUNT = 100                    # Number of nodes
NODE_TX_RANGE = 100                     # Transmission range
NODE_STARTUP_DELAY = 5                  # Delay before nodes wake up

# Cluster Management
MAX_CLUSTER_SIZE = 0                    # 0 = unlimited
YELLOW_NODE_CH_TIMEOUT = 120            # Seconds before becoming CH
YELLOW_NODE_CH_TIMEOUT_VARIANCE = 60    # Random variance
MIN_CH_DISTANCE = 60                    # Minimum distance between CHs

# Router Layer
ENABLE_ROUTER_LAYER = True              # Enable router-based cluster expansion
ROUTER_HEARTBEAT_INTERVAL = 60          # Router heartbeat interval
MIN_CLUSTER_SIZE = 3                    # Minimum nodes per cluster before CH promotion

# Routing
ENABLE_HYBRID_ROUTING = True            # CTM-AdHoc hybrid routing
ENABLE_MULTIHOP_NEIGHBORS = True        # Multi-hop neighbor discovery
NEIGHBOR_TIMEOUT = 30                   # Remove stale neighbors after 30s
```

---

## Running the Simulation

### Main Simulation
```bash
cd wsnlab
python3 data_collection_tree.py
```

The simulation will:
1. Create 100 nodes at random positions
2. Display them on the visualization panel
3. Wait 5 seconds for all nodes to appear
4. Start network formation with router layer
5. Show real-time color changes (white→yellow→green→blue/orange)
6. Export CSV files when complete or when you press Ctrl+C

### Read Statistics
```bash
python3 read_stats.py
```
Analyzes exported CSV files and displays network statistics

---

## Output Files

### Routing Tables (Merged Format - One Line Per Node)

**neighbors_table.csv** - Direct 1-hop neighbors
```csv
node_id,node_role,neighbor_count,neighbors
11,ROOT,7,0(REGISTERED,1,98.5);1(REGISTERED,1,75.4);...
```

**members_table.csv** - Cluster members
```csv
node_id,node_role,member_count,members
5,CLUSTER_HEAD,5,23(REGISTERED);45(REGISTERED);...
```

**child_networks_table.csv** - Tree structure
```csv
node_id,node_role,child_count,children
0,ROOT,3,5(CLUSTER_HEAD)[5,12,23,45,67];...
```

### Message Log

**message_log.csv** - Meaningful messages only (no HEART_BEAT spam)
```csv
timestamp,source_id,source_role,dest,dest_id,message_type,details
7.5,23,UNREGISTERED,BROADCAST,,PROBE,Looking for network
8.3,23,UNREGISTERED,5.254,5,JOIN_REQUEST,Request to join
8.6,5,CLUSTER_HEAD,BROADCAST,23,JOIN_REPLY,Assigned addr [11,23]
```

### Statistics

**routing_statistics.csv** - Routing method counts per node
```csv
node_id,role,direct_mesh,intra_cluster,downward_tree,upward_tree,...
```

### Network Topology

**node_distances.csv** - All pairwise distances (100x100 matrix)
**neighbor_distances.csv** - Distances between neighbors only
**clusterhead_distances.csv** - Distances between CHs only

---

## Expected Results (100 nodes)

### Without Router Layer
```
CLUSTER_HEAD    :  8-12 nodes
REGISTERED      :  88-92 nodes
ROOT            :   1 node
Isolated        :   0 nodes
```

### With Router Layer (ENABLE_ROUTER_LAYER = True)
```
CLUSTER_HEAD    :  5-8 nodes (blue)
ROUTER          :  2-4 nodes (orange)
REGISTERED      :  87-93 nodes (green)
ROOT            :   1 node (black)
Isolated        :   0 nodes
Network Depth   :   3-4 hops (ROOT→ROUTER→CH→REGISTERED)
```

### CSV File Sizes
```
neighbors_table.csv:      ~100 rows (6-8x smaller than before)
members_table.csv:        ~5-10 rows (10-15x smaller)
child_networks_table.csv: ~5-10 rows (2-3x smaller)
message_log.csv:          ~100-200 rows (5-10x smaller)
```

---

## How to Verify Network Formation

### Check neighbors_table.csv
```bash
# Show first 10 nodes
head -11 neighbors_table.csv

# Find nodes with most neighbors
sort -t',' -k3 -rn neighbors_table.csv | head -5

# Find isolated nodes
awk -F',' '$3 == 0' neighbors_table.csv
```

### Check members_table.csv
```bash
# Show all CHs and their member counts
grep "CLUSTER_HEAD" members_table.csv

# Count total members
awk -F',' 'NR>1 {sum+=$3} END {print sum}' members_table.csv
```

### Check message_log.csv
```bash
# Show all messages
cat message_log.csv

# Count message types
cut -d',' -f6 message_log.csv | sort | uniq -c

# Trace a specific node
grep "^23," message_log.csv
```

## Troubleshooting

### Too many CHs (50+)
**Cause:** MAX_CLUSTER_SIZE too small  
**Fix:** Set `MAX_CLUSTER_SIZE = 0` in config.py

### Isolated nodes (red)
**Cause:** Nodes can't find CHs  
**Fix:** Increase `YELLOW_NODE_CH_TIMEOUT` to 180

### Empty CSV files
**Cause:** Simulation ended too early  
**Fix:** Run longer (wait 100+ seconds)

### No messages in message_log.csv
**Cause:** Simulation too short  
**Fix:** Run longer or check `NODE_STARTUP_DELAY`



### Router Layer Algorithm
1. **Yellow Detection** - Unregistered node (yellow) broadcasts JOIN_REQUEST
2. **Router Nomination** - Nearby green nodes receive request, nominate themselves with distance
3. **Nomination Collection** - Parent CH collects nominations for 2 seconds
4. **Router Selection** - CH selects closest green as router (distance-based)
5. **Router Approval** - Selected green receives ROUTER_APPROVAL, others get ROUTER_REJECTION
6. **CH Promotion Request** - Router sends NETWORK_REQUEST to ROOT for yellow's CH address
7. **ROOT Approval** - ROOT allocates CH address, sends NETWORK_REPLY to router
8. **BECOME_CH Message** - Router sends BECOME_CH to yellow with new CH address
9. **Yellow→CH** - Yellow becomes CLUSTER_HEAD (blue), router becomes ROUTER (orange)
10. **Lock Release** - New CH sends ROUTER_PROMOTION_COMPLETE to unlock parent CH
11. **Next Yellow** - Parent CH processes next yellow in queue

### Network Formation (Without Router Layer)
1. ROOT sends HEART_BEAT
2. Yellow nodes receive HEART_BEAT, send JOIN_REQUEST
3. CH/ROOT sends JOIN_REPLY with address
4. Node sends JOIN_ACK, becomes REGISTERED

### Routing Decision (CTM-AdHoc Hybrid)
1. Check if destination is a direct neighbor → Direct mesh
2. Check if destination is a cluster member → Intra-cluster
3. Check if destination is in child networks → Downward tree
4. Check multi-hop neighbors → Multi-hop route
5. Forward to parent → Upward tree

### Adaptive CH Promotion (Fallback)
1. Node becomes UNREGISTERED (yellow)
2. Waits 60-90 seconds for CH heartbeat or router promotion
3. If no response, becomes CLUSTER_HEAD (blue)
4. Sends HEART_BEAT to attract members


### Core Components
- **SensorNode Class** - Main node implementation with role-based behavior
- **Router Nomination System** - Competitive selection of router nodes
- **Lock Management** - Prevents race conditions during promotions
- **Event-Based Completion** - ROUTER_PROMOTION_COMPLETE message unlocks parent
- **Mesh Routing** - route_and_forward_package() handles multi-hop delivery
- **Neighbor Management** - Heartbeat protocol with timeout-based cleanup

### Message Types
- `PROBE` - Network discovery
- `HEART_BEAT` - Neighbor maintenance
- `JOIN_REQUEST` - Cluster membership request (triggers router nomination)
- `ROUTER_NOMINATION` - Green nominates self for router role
- `ROUTER_APPROVAL/REJECTION` - CH's router selection decision
- `NETWORK_REQUEST/REPLY` - CH address allocation from ROOT
- `BECOME_CH` - Router promotes yellow to CH
- `ROUTER_PROMOTION_COMPLETE` - Unlock parent CH after promotion
- `ROUTER_REGISTER` - Router registers with parent CH
