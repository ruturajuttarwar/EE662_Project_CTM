# Data Collection Tree - Wireless Sensor Network Routing Protocols

## Overview

This project implements and compares two routing protocols for Wireless Sensor Networks (WSN):

1. **data_collection_tree_CH.py** - Basic Tree Routing (Baseline)
2. **data_collection_tree_v3.py** - CTM-AdHoc Hybrid Routing (Advanced)

Both implementations include comprehensive energy models for performance comparison and analysis.

---

## Protocol Comparison

### data_collection_tree_CH.py (Baseline)

**Basic Tree Routing Protocol:**
- Simple cluster head formation
- Pure tree-based routing (upward/downward only)
- Direct parent-child relationships
- No router layer
- Single routing method
- Energy model enabled for comparison

**Routing:**
- Upward: Node → Parent CH → ROOT
- Downward: ROOT → Child CH → Node
- No mesh or multi-hop routing

**Use Case:** Baseline for comparison, simpler network structure

---

### data_collection_tree_v3.py (Advanced - CTM-AdHoc)

**CTM-AdHoc Hybrid Routing Protocol:**
- **5 Routing Methods** - Intelligent routing decisions
- **3-Table Routing System** - neighbors, members, child_networks
- **Router Layer** - Automatic network expansion
- **Network Maintenance** - Self-healing at 1000s
- **Multi-Hop Discovery** - Extended neighbor awareness
- **Energy Model** - Complete energy tracking
- **Data Generation** - Application-layer traffic simulation
- **Node Failure** - Resilience testing

**Routing Methods (Priority Order):**
1. **Direct Mesh** - Send directly to neighbors
2. **Intra-Cluster** - Forward within cluster
3. **Downward Tree** - Route to child clusters
4. **Upward Tree** - Route to parent
5. **Multi-Hop** - Use 2-hop neighbors

**Use Case:** Advanced protocol with better energy efficiency and routing flexibility

---

## Evolution from Previous Version

**Previous (data_collection_tree_CH.py):**
- Basic cluster head formation
- Simple tree structure
- Direct join only
- No router layer
- Single routing method
- Energy model (NEW - added for comparison)

**V3 (data_collection_tree_v3.py) - CURRENT:**
- **CTM-AdHoc Hybrid Routing** - 5 routing methods
- **3-Table Routing System** - neighbors, members, child_networks
- **Router Layer** - Boolean lock with timeout recovery
- **Network Maintenance** - Automatic cleanup at 1000s
- **Prevention Logic** - Stops invalid connections at source
- **Enhanced Diagnostics** - Comprehensive logging
- **Energy Model** - Complete energy consumption tracking
- **Packet Loss Simulation** - Realistic network conditions
- **Data Generation** - Application-layer traffic (optional)
- **Node Failure** - Resilience testing (optional)

---

## Key Features

### 1. CTM-AdHoc Hybrid Routing Protocol (V3 Only)

**5 Routing Methods (Priority Order):**

1. **Direct Mesh** - Send directly if destination is a neighbor
   ```
   Node A → Node B (if B in neighbors_table)
   ```

2. **Intra-Cluster** - Forward to cluster member
   ```
   CH → Member (if member in members_table)
   ```

3. **Downward Tree** - Forward to child cluster
   ```
   CH → Child CH (if dest network in child_networks_table)
   ```

4. **Upward Tree** - Forward to parent
   ```
   Node → Parent CH → ROOT
   ```

5. **Multi-Hop** - Use multi-hop neighbors
   ```
   Node → 2-hop neighbor (if enabled)
   ```

---

### 2. Energy Model (NEW)

**Complete energy consumption tracking with node lifetime simulation:**

#### **Key Features:**
- ✅ Per-node energy tracking (TX, RX, idle, sleep)
- ✅ Node death when energy depleted
- ✅ Packet loss simulation
- ✅ Periodic energy sampling (every 100s)
- ✅ Two CSV outputs for analysis
- ✅ Real-time energy statistics

#### **Energy Consumption:**
```
TX:    0.0001 J/byte  (transmitting packets)
RX:    0.00005 J/byte (receiving packets)
Idle:  0.001 J/s      (listening for packets)
Sleep: 0.0001 J/s     (undiscovered state)
```

#### **Node Lifetime:**
- Initial energy: 10,000 Joules (configurable)
- Nodes die when energy reaches 0
- Dead nodes cannot send/receive
- Network adapts to node failures

#### **Data Collection:**
- **energy_timeline.csv** - Time-series data every 100s
- **energy_summary.csv** - Per-node final statistics
- Tracks: energy consumed, packets sent/received, node death time

---

### 3. Three-Table Routing System

### 3. Three-Table Routing System

#### **neighbors_table.csv** - Physical Connectivity
```csv
node_id,node_role,neighbor_count,neighbors
81,ROOT,5,"73(CLUSTER_HEAD,1,89.5);82(ROUTER,2,95.2);..."
```

**Contains:**
- Direct 1-hop neighbors
- Physical distances
- Neighbor roles
- Hop counts to ROOT

**Used For:**
- Direct mesh routing
- Yellow node selection of greens
- Network topology understanding

---

#### **members_table.csv** - Cluster Membership
```csv
node_id,node_role,member_count,members
81,ROOT,6,"73(CLUSTER_HEAD);82(ROUTER);92(CLUSTER_HEAD);..."
```

**Contains:**
- Nodes belonging to this CH
- Routers bridging to child CHs
- Direct registered members

**Used For:**
- Intra-cluster routing
- Cluster size management
- Member tracking

---

#### **child_networks_table.csv** - Network Hierarchy
```csv
node_id,node_role,child_count,children
81,ROOT,3,"73(CLUSTER_HEAD)[73];92(CLUSTER_HEAD)[92];..."
```

**Contains:**
- Child CHs and their network IDs
- Hierarchical tree structure
- Network depth information

**Used For:**
- Downward tree routing
- Network ID assignment
- Hierarchy visualization

---

### 4. Router Layer - Enhanced

**Key Improvements:**
- Boolean lock system (simple, effective)
- Timeout-based lock release (2 seconds)
- Distance-based green selection
- Direct yellow-to-green messaging
- Duplicate prevention with sets

**Router Promotion Flow:**

```
1. Yellow selects closest green from neighbors_table
2. Yellow sends JOIN_REQUEST directly to green
3. Green sends NETWORK_REQUEST to parent CH
4. CH checks lock (active_router_promotion)
5. CH approves if lock available
6. CH sets lock + 2-second timeout
7. Green becomes ROUTER
8. Router sends BECOME_CH to yellow
9. Yellow becomes CH
10. Lock auto-releases after 2 seconds
```

**Lock Management:**
```python
# Set lock with timeout
self.active_router_promotion = True
self.yellows_being_promoted.add(yellow_id)
self.set_timer('TIMER_PROMOTION_LOCK_TIMEOUT', 2.0)

# Auto-release after 2 seconds
elif name == 'TIMER_PROMOTION_LOCK_TIMEOUT':
    self.active_router_promotion = False
    self.yellows_being_promoted.clear()
```

---

### 5. Network Maintenance (4000s)

**Automatic cleanup of invalid network states:**

#### **Phase 1: Kill Stuck Yellows**
- Criteria: UNREGISTERED > 1000 seconds
- Action: Set to UNDISCOVERED
- Example: Node 85 stuck for 3936s

#### **Phase 1b: Kill Greens Outside Network**
- Criteria: REGISTERED with parent_gui = None
- Action: Set to UNDISCOVERED
- Example: Node 84 (no parent)

#### **Phase 1c: Kill Greens Connected to Routers**
- Criteria: REGISTERED with parent = ROUTER
- Action: Set to UNDISCOVERED
- Example: Node 17 → Router 27

#### **Phase 1d: Kill Greens Connected to Greens**
- Criteria: REGISTERED with parent = REGISTERED
- Action: Set to UNDISCOVERED
- Example: Node 8 → Node 17 (both greens)

#### **Phase 2: Demote Orphaned Routers**
- Criteria: ROUTER with no child CH
- Action: Demote to REGISTERED
- Example: Router 89 (no child)

#### **Phase 3: Clean Up Tables**
- Remove killed nodes from members_table
- Ensure CHs don't reference dead nodes

**Expected Log Output:**
```
======================================================================
[MAINTENANCE] Starting network maintenance at 4000.0s
======================================================================

[MAINTENANCE] Phase 1: Identifying stuck yellows...
[MAINTENANCE] Killed stuck yellow 85

[MAINTENANCE] Phase 1b: Identifying greens outside network...
[MAINTENANCE] Killed green 84 (outside network)

[MAINTENANCE] Phase 1c: Identifying greens connected to routers...
[MAINTENANCE] Killed green 17 (connected to router 27)

[MAINTENANCE] Phase 2: Identifying orphaned routers...
[MAINTENANCE] Demoted orphaned router 89 to REGISTERED

======================================================================
[MAINTENANCE] Summary:
  - Killed yellows: 1 nodes [85]
  - Killed greens: 2 nodes [84, 17]
  - Demoted routers: 1 nodes [89]
  - Total nodes cleaned: 4
======================================================================
```

---

### 6. Prevention Logic

**Prevent Invalid Connections at Source:**

#### **JOIN_REPLY Validation**
```python
# Reject JOIN_REPLY from routers
if pck['type'] == 'JOIN_REPLY':
    sender_gui = pck['gui']
    # Check if sender is a ROUTER
    if sender.role == Roles.ROUTER:
        self.log(f"[JOIN] REJECTED JOIN_REPLY from ROUTER {sender_gui}")
        return  # Ignore invalid JOIN_REPLY
```

**Why This Matters:**
- Stops greens from connecting to routers
- Prevents invalid hierarchy at source
- Reduces maintenance workload

---

### 7. Energy Model (NEW)

**Comprehensive energy consumption tracking and node lifetime simulation:**

#### **Energy Consumption Sources**

1. **Transmission (TX)** - Energy per byte transmitted
   - Configurable: `TX_ENERGY_PER_BYTE = 0.0001 J/byte`
   - Tracks: Packet size × energy rate
   - Includes: All broadcasts and unicasts

2. **Reception (RX)** - Energy per byte received
   - Configurable: `RX_ENERGY_PER_BYTE = 0.00005 J/byte`
   - Tracks: Received packet size × energy rate
   - Includes: All incoming packets

3. **Idle/Listening** - Energy while waiting for packets
   - Configurable: `IDLE_ENERGY_PER_SECOND = 0.001 J/s`
   - Tracks: Time spent in active listening state
   - Applied: When node is awake but not TX/RX

4. **Sleep** - Energy while undiscovered
   - Configurable: `SLEEP_ENERGY_PER_SECOND = 0.0001 J/s`
   - Tracks: Time before node joins network
   - Applied: UNDISCOVERED state only

#### **Node Death Handling**

When a node's energy reaches zero:
```python
def die_from_energy_depletion(self):
    self.is_alive = False
    self.log(f"[ENERGY] Node {self.id} DIED - Energy depleted!")
    # Dead nodes:
    # - Cannot send packets
    # - Cannot receive packets
    # - Are removed from routing tables
```

#### **Packet Loss Simulation**

Optional packet loss for realistic network conditions:
```python
ENABLE_PACKET_LOSS = True
PACKET_LOSS_PROBABILITY = 0.05  # 5% loss rate
```

**Features:**
- Random packet drops before transmission
- Lost packets don't consume TX energy
- Tracks packet loss statistics per node

#### **Energy Sampling**

Periodic energy snapshots for analysis:
- **Frequency:** Every 100 seconds (configurable)
- **Trigger:** ROOT node timer
- **Scope:** All nodes in network
- **Output:** `energy_timeline.csv`

#### **Energy Statistics**

At simulation end, displays:
```
Energy Statistics:
  Alive nodes: 95/100 (95.0%)
  Energy samples collected: 500
```

---

## Network Roles

| Role | Color | Description |
|------|-------|-------------|
| **ROOT** | Black | Network coordinator, root of tree |
| **CLUSTER_HEAD** | Blue | Cluster coordinators, manage members |
| **ROUTER** | Orange | Bridge nodes connecting distant CHs |
| **REGISTERED** | Green | Nodes successfully joined a cluster |
| **UNREGISTERED** | Yellow | Nodes searching for network |
| **UNDISCOVERED** | White | Nodes not yet awake |

---

## Configuration

Edit `wsnlab/source/config.py`:

### Network Settings
```python
SIM_NODE_COUNT = 100                    # Number of nodes
NODE_TX_RANGE = 100                     # Transmission range (meters)
NODE_STARTUP_DELAY = 5                  # Delay before nodes wake up
SIMULATION_DURATION = 5000              # Total simulation time (seconds)
```

### Cluster Management
```python
MAX_CLUSTER_SIZE = 0                    # 0 = unlimited
MIN_CLUSTER_SIZE = 3                    # Min nodes before CH promotion
YELLOW_NODE_CH_TIMEOUT = 60             # Seconds before becoming CH
YELLOW_NODE_CH_TIMEOUT_VARIANCE = 30    # Random variance
```

### Router Layer
```python
ENABLE_ROUTER_LAYER = True              # Enable router-based expansion
ROUTER_HEARTBEAT_INTERVAL = 60          # Router heartbeat interval
```

### Routing
```python
ENABLE_HYBRID_ROUTING = True            # CTM-AdHoc hybrid routing
ENABLE_MULTIHOP_NEIGHBORS = True        # Multi-hop neighbor discovery
NEIGHBOR_TIMEOUT = 30                   # Remove stale neighbors (seconds)
NEIGHBOR_SHARE_INTERVAL = 30            # Share neighbor table interval
MAX_HOP_COUNT = 2                       # Maximum hop count for multi-hop
```

### Energy Model (NEW)
```python
ENABLE_ENERGY_MODEL = True              # Enable energy consumption tracking
INITIAL_ENERGY_JOULES = 10000           # Initial energy per node (Joules)
TX_ENERGY_PER_BYTE = 0.0001            # Energy per byte transmitted (J/byte)
RX_ENERGY_PER_BYTE = 0.00005           # Energy per byte received (J/byte)
IDLE_ENERGY_PER_SECOND = 0.001         # Energy while idle/listening (J/s)
SLEEP_ENERGY_PER_SECOND = 0.0001       # Energy while sleeping (J/s)
ENERGY_SAMPLE_INTERVAL = 100            # Sample energy every N seconds
```

### Packet Loss Simulation (NEW)
```python
ENABLE_PACKET_LOSS = False              # Enable packet loss simulation
PACKET_LOSS_PROBABILITY = 0.05          # 5% packet loss rate
```

### Maintenance
```python
# Maintenance runs at 4000s automatically
# No configuration needed - hardcoded in ROOT initialization
```

---

## Running the Simulation

### Start Simulation
```bash
cd wsnlab
python3 data_collection_tree_v3.py
```

### What Happens:
1. **0-5s:** Nodes appear on visualization (white)
2. **5s:** Nodes wake up, one becomes ROOT (black)
3. **5-100s:** Initial cluster formation (yellow → green)
4. **100-1000s:** Router promotions (green → orange, yellow → blue)
5. **1000-4000s:** Network stabilization, hierarchical growth
6. **4000s:** Maintenance runs (cleanup invalid nodes)
7. **4000-5000s:** Final network operation
8. **5000s:** Simulation ends, CSV files exported

### Watch For:
- **Color changes:** white → yellow → green → blue/orange
- **Arrows:** Show parent-child relationships
- **Log messages:** Real-time network events
- **Maintenance at 4000s:** Cleanup messages

---

## Output Files

### Core Tables (3 Essential Files)

**1. neighbors_table.csv** - Physical connectivity
```csv
node_id,node_role,neighbor_count,neighbors
81,ROOT,5,"73(CLUSTER_HEAD,1,89.5);82(ROUTER,2,95.2)"
```

**2. members_table.csv** - Cluster membership
```csv
node_id,node_role,member_count,members
81,ROOT,6,"73(CLUSTER_HEAD);82(ROUTER);92(CLUSTER_HEAD)"
```

**3. child_networks_table.csv** - Network hierarchy
```csv
node_id,node_role,child_count,children
81,ROOT,3,"73(CLUSTER_HEAD)[73];92(CLUSTER_HEAD)[92]"
```

### Energy Model Output (NEW - if ENABLE_ENERGY_MODEL = True)

**4. energy_timeline.csv** - Time-series energy data
```csv
timestamp,node_id,role,remaining_energy,energy_consumed,energy_tx,energy_rx,energy_idle,energy_sleep,is_alive,packets_sent,packets_received,packets_lost,bytes_sent,bytes_received
100.0,1,ROOT,9950.5,49.5,30.2,15.3,4.0,0.0,True,150,200,5,15000,20000
200.0,1,ROOT,9901.2,98.8,60.5,30.1,8.2,0.0,True,300,400,8,30000,40000
```

**Contains:**
- Energy snapshots every 100 seconds (configurable)
- Per-node energy breakdown (TX, RX, idle, sleep)
- Packet statistics (sent, received, lost)
- Node alive status

**Use For:**
- Plotting energy consumption over time
- Identifying energy-hungry nodes
- Analyzing network lifetime
- Detecting node failures

**5. energy_summary.csv** - Per-node final statistics
```csv
node_id,final_role,initial_energy,remaining_energy,total_consumed,energy_tx,energy_rx,energy_idle,energy_sleep,time_tx,time_rx,time_idle,time_sleep,packets_sent,packets_received,packets_lost,bytes_sent,bytes_received,is_alive,death_time
1,ROOT,10000,8500.5,1499.5,800.2,400.3,250.0,49.0,120.5,180.2,2500.0,1199.3,1500,2000,25,150000,200000,True,
5,CLUSTER_HEAD,10000,0.0,10000,5000.2,3000.1,1800.0,199.7,250.3,350.1,1800.0,2599.6,2500,3500,50,250000,350000,False,3456.7
```

**Contains:**
- Final energy state of all nodes
- Total energy consumed by category
- Time spent in each state
- Complete packet statistics
- Node death time (if depleted)

**Use For:**
- Network lifetime analysis
- Energy efficiency comparison
- Identifying bottleneck nodes
- Role-based energy consumption analysis

### Log File

**simulation_log.txt** - Complete event log
- All node state changes
- Router promotions
- Maintenance actions
- Routing decisions
- Energy depletion events (if enabled)

---

## Expected Results (100 nodes)

### Network Composition
```
ROOT            :   1 node  (black)
CLUSTER_HEAD    :   5-10 nodes (blue)
ROUTER          :   2-5 nodes (orange)
REGISTERED      :   85-92 nodes (green)
UNREGISTERED    :   0-2 nodes (yellow) - killed at 4000s
UNDISCOVERED    :   0-5 nodes (white) - killed at 4000s
```

### Network Depth
```
ROOT (depth 0)
  ├── CH (depth 1)
  │   ├── ROUTER → CH (depth 2)
  │   │   └── ROUTER → CH (depth 3)
  │   └── REGISTERED
  └── REGISTERED

Typical depth: 2-4 hops
```

### Coverage
```
Before maintenance: ~95% nodes connected
After maintenance:  ~95% nodes connected (cleaner)
```

---

## Verification Commands

### Check Network Structure
```bash
# View neighbors table
cat neighbors_table.csv

# Count nodes by role
cut -d',' -f2 neighbors_table.csv | sort | uniq -c

# Find nodes with most neighbors
sort -t',' -k3 -rn neighbors_table.csv | head -5
```

### Check Cluster Membership
```bash
# View all CHs and their members
cat members_table.csv

# Count total members
awk -F',' 'NR>1 {sum+=$3} END {print sum}' members_table.csv
```

### Check Network Hierarchy
```bash
# View tree structure
cat child_networks_table.csv

# Count network depth
# (manually trace from ROOT to deepest CH)
```

### Check Energy Statistics (NEW)
```bash
# View energy timeline
cat energy_timeline.csv

# Find nodes that died
awk -F',' '$10=="False" {print $2}' energy_summary.csv

# Calculate average energy consumption
awk -F',' 'NR>1 {sum+=$5; count++} END {print sum/count}' energy_summary.csv

# Find most energy-consuming node
sort -t',' -k5 -rn energy_summary.csv | head -2

# Count alive vs dead nodes
awk -F',' 'NR>1 {if($19=="True") alive++; else dead++} END {print "Alive:",alive,"Dead:",dead}' energy_summary.csv

# Plot energy over time (requires gnuplot)
gnuplot -e "set datafile separator ','; set xlabel 'Time (s)'; set ylabel 'Energy (J)'; plot 'energy_timeline.csv' using 1:4 with lines title 'Node Energy'"
```

### Check Maintenance Actions
```bash
# Search for maintenance in log
grep "MAINTENANCE" simulation_log.txt

# Count killed nodes
grep "Killed" simulation_log.txt | wc -l

# Count demoted routers
grep "Demoted" simulation_log.txt | wc -l

# Check energy depletion events
grep "DIED - Energy depleted" simulation_log.txt
```

---

## Troubleshooting

### Issue: Too Many Yellows After 4000s
**Cause:** Maintenance not running  
**Fix:** Check if ROOT is alive, maintenance only runs on ROOT

### Issue: Greens Connected to Routers
**Cause:** JOIN_REPLY validation not working  
**Fix:** Check logs for "REJECTED JOIN_REPLY" messages

### Issue: Empty CSV Tables
**Cause:** Simulation ended too early  
**Fix:** Run for full 5000 seconds

### Issue: No Routers Formed
**Cause:** ENABLE_ROUTER_LAYER = False  
**Fix:** Set to True in config.py

### Issue: Network Not Growing
**Cause:** Lock stuck, timeout not working  
**Fix:** Check for "Promotion lock timeout" messages at 2-second intervals

### Issue: No Energy Data Generated (NEW)
**Cause:** ENABLE_ENERGY_MODEL = False  
**Fix:** Set to True in config.py

### Issue: All Nodes Die Too Quickly (NEW)
**Cause:** Energy parameters too aggressive  
**Fix:** Increase INITIAL_ENERGY_JOULES or decrease energy consumption rates

### Issue: No Nodes Die (NEW)
**Cause:** Energy parameters too conservative  
**Fix:** Decrease INITIAL_ENERGY_JOULES or increase energy consumption rates

### Issue: Energy Timeline CSV Empty (NEW)
**Cause:** Simulation ended before first sample  
**Fix:** Check ENERGY_SAMPLE_INTERVAL (default 100s), run simulation longer

---

## Key Algorithms

### Routing Decision (route_and_forward_package)
```python
def route_and_forward_package(self, pck):
    # 1. Direct Mesh - Check neighbors_table
    if dest in neighbors_table:
        send directly
        return
    
    # 2. Intra-Cluster - Check members_table
    if dest in members_table:
        forward to member
        return
    
    # 3. Downward Tree - Check child_networks_table
    if dest.network in child_networks_table:
        forward to child CH
        return
    
    # 4. Multi-Hop - Check multihop_neighbors
    if dest in multihop_neighbors:
        forward via intermediate
        return
    
    # 5. Upward Tree - Forward to parent
    forward to parent
```

### Yellow Selection of Green
```python
def select_and_join():
    # Calculate distances to all greens
    for green in registered_candidates:
        distance = neighbors_table[green]['distance']
        if distance < min_distance:
            min_distance = distance
            closest_green = green
    
    # Send JOIN_REQUEST to closest green only
    send_join_request(closest_green)
```

### Router Promotion Lock
```python
def approve_promotion(yellow_id, green_id):
    # Check lock
    if active_router_promotion:
        reject("Promotion in progress")
        return
    
    # Check duplicate
    if yellow_id in yellows_being_promoted:
        reject("Already promoting this yellow")
        return
    
    # Approve and lock
    active_router_promotion = True
    yellows_being_promoted.add(yellow_id)
    set_timer('TIMER_PROMOTION_LOCK_TIMEOUT', 2.0)
    
    send_approval()
```

### Network Maintenance
```python
def run_network_maintenance():
    # Phase 1: Kill stuck yellows
    for yellow in yellows:
        if stuck_time > 1000:
            kill(yellow)
    
    # Phase 1b: Kill greens outside network
    for green in greens:
        if parent_gui is None:
            kill(green)
    
    # Phase 1c: Kill greens → routers
    for green in greens:
        if parent.role == ROUTER:
            kill(green)
    
    # Phase 1d: Kill greens → greens
    for green in greens:
        if parent.role == REGISTERED:
            kill(green)
    
    # Phase 2: Demote orphaned routers
    for router in routers:
        if no child CH:
            demote(router)
    
    # Phase 3: Clean up tables
    remove killed nodes from members_table
```

---

## Documentation Files

- **README_V3.md** - This file (main documentation)
- **V3_COMPREHENSIVE_SUMMARY.md** - Complete V3 changes summary
- **MAINTENANCE_COMPLETE_GUIDE.md** - Maintenance algorithm details
- **PREVENT_GREEN_TO_ROUTER.md** - Prevention logic explanation
- **PHASE_1C_ENHANCED.md** - Enhanced green-to-router detection

---

## Research Context

This simulation implements the **CTM-AdHoc protocol** for wireless sensor networks, combining:
- Tree-based hierarchical routing
- Mesh-based direct routing
- Automatic router layer for network extension
- Self-healing maintenance mechanisms

**Use Cases:**
- Environmental monitoring
- Smart agriculture
- Industrial IoT
- Disaster response networks

---

## Status

**Version:** 3.1  
**Status:** Production Ready  
**Last Updated:** December 2024  
**Tested:** 100 nodes, 5000 seconds, multiple runs  
**Coverage:** ~95% nodes connected  
**Stability:** Self-healing with maintenance  
**New Features:** Energy model with node lifetime simulation

---

## Quick Start

```bash
# 1. Navigate to directory
cd wsnlab

# 2. Run simulation
python3 data_collection_tree_v3.py

# 3. Wait for completion (5000 seconds simulated)

# 4. Check results
cat neighbors_table.csv
cat members_table.csv
cat child_networks_table.csv

# 5. Search maintenance actions
grep "MAINTENANCE" simulation_log.txt
```

---

## Support

For issues or questions:
1. Check troubleshooting section
2. Review log files (simulation_log.txt)
3. Verify configuration (config.py)
4. Check documentation files

---

## Comparing CH vs V3 Protocols

### Running Both Simulations

**1. Run Baseline (CH) Protocol:**
```bash
cd wsnlab
python3 data_collection_tree_CH.py
```

**Output Files:**
- `clusterhead_distances.csv`
- `neighbor_distances.csv`
- `energy_timeline_CH.csv` ← Energy data
- `energy_summary_CH.csv` ← Energy summary

**2. Run Advanced (V3) Protocol:**
```bash
cd wsnlab
python3 data_collection_tree_v3.py
```

**Output Files:**
- `child_networks_table.csv`
- `members_table.csv`
- `neighbors_table.csv`
- `energy_timeline.csv` ← Energy data
- `energy_summary.csv` ← Energy summary
- `data_packets.csv` (if data generation enabled)
- `data_summary.csv` (if data generation enabled)

---

### Comparison Metrics

#### 1. Energy Efficiency

**Files to Compare:**
- `energy_timeline_CH.csv` vs `energy_timeline.csv`
- `energy_summary_CH.csv` vs `energy_summary.csv`

**Metrics:**
```python
# Average energy consumption
CH_avg = mean(energy_summary_CH['total_consumed'])
V3_avg = mean(energy_summary['total_consumed'])

# Network lifetime (time until first node dies)
CH_lifetime = min(energy_summary_CH['death_time'])
V3_lifetime = min(energy_summary['death_time'])

# Energy per packet
CH_efficiency = CH_avg / total_packets
V3_efficiency = V3_avg / total_packets
```

**Expected Results:**
- V3 should have **lower average energy consumption** (mesh routing reduces hops)
- V3 should have **longer network lifetime** (better load distribution)
- V3 should have **better energy efficiency** (fewer retransmissions)

---

#### 2. Routing Efficiency

**Metrics:**
```python
# Average hop count (from data_packets.csv in V3)
V3_avg_hops = mean(data_packets[data_packets['event']=='DELIVERED']['hop_count'])

# For CH, estimate from tree depth
CH_avg_hops = average_tree_depth * 2  # up and down

# Packet delivery ratio (V3 only with data generation)
PDR = delivered_packets / generated_packets * 100
```

**Expected Results:**
- V3 should have **lower average hop count** (direct mesh routing)
- V3 should have **higher PDR** (multiple routing options)

---

#### 3. Network Structure

**CH Protocol:**
```
ROOT
  ├── CH1
  │   ├── Node A
  │   └── Node B
  └── CH2
      ├── Node C
      └── Node D

Simple tree, fixed paths
```

**V3 Protocol:**
```
ROOT
  ├── CH1 ←→ CH2 (mesh)
  │   ├── Router → CH3
  │   ├── Node A ←→ Node B (mesh)
  │   └── Node C
  └── CH2
      └── Node D

Hybrid tree + mesh, flexible paths
```

---

### Analysis Scripts

**Python Analysis Example:**

```python
import pandas as pd
import matplotlib.pyplot as plt

# Load energy data
ch_timeline = pd.read_csv('energy_timeline_CH.csv')
v3_timeline = pd.read_csv('energy_timeline.csv')

# Plot average remaining energy over time
ch_avg = ch_timeline.groupby('timestamp')['remaining_energy'].mean()
v3_avg = v3_timeline.groupby('timestamp')['remaining_energy'].mean()

plt.figure(figsize=(10, 6))
plt.plot(ch_avg.index, ch_avg.values, label='CH Protocol (Baseline)', marker='o')
plt.plot(v3_avg.index, v3_avg.values, label='V3 Protocol (CTM-AdHoc)', marker='s')
plt.xlabel('Time (seconds)')
plt.ylabel('Average Remaining Energy (Joules)')
plt.title('Energy Consumption Comparison')
plt.legend()
plt.grid(True)
plt.savefig('energy_comparison.png')
plt.show()

# Calculate improvement
ch_final = ch_avg.iloc[-1]
v3_final = v3_avg.iloc[-1]
improvement = (v3_final - ch_final) / ch_final * 100
print(f"V3 has {improvement:.2f}% more remaining energy than CH")
```

**Energy Efficiency Comparison:**

```python
# Load summary data
ch_summary = pd.read_csv('energy_summary_CH.csv')
v3_summary = pd.read_csv('energy_summary.csv')

# Compare by role
roles = ['ROOT', 'CLUSTER_HEAD', 'REGISTERED']
for role in roles:
    ch_role = ch_summary[ch_summary['final_role'] == role]['total_consumed'].mean()
    v3_role = v3_summary[v3_summary['final_role'] == role]['total_consumed'].mean()
    
    print(f"{role}:")
    print(f"  CH: {ch_role:.2f} J")
    print(f"  V3: {v3_role:.2f} J")
    print(f"  Improvement: {(ch_role - v3_role) / ch_role * 100:.2f}%")
```

**Network Lifetime Comparison:**

```python
# Count alive nodes over time
ch_alive = ch_timeline.groupby('timestamp')['is_alive'].sum()
v3_alive = v3_timeline.groupby('timestamp')['is_alive'].sum()

plt.figure(figsize=(10, 6))
plt.plot(ch_alive.index, ch_alive.values, label='CH Protocol', marker='o')
plt.plot(v3_alive.index, v3_alive.values, label='V3 Protocol', marker='s')
plt.xlabel('Time (seconds)')
plt.ylabel('Number of Alive Nodes')
plt.title('Network Lifetime Comparison')
plt.legend()
plt.grid(True)
plt.savefig('lifetime_comparison.png')
plt.show()
```

---

### Expected Comparison Results

| Metric | CH Protocol | V3 Protocol | Improvement |
|--------|-------------|-------------|-------------|
| Avg Energy Consumption | Higher | Lower | 15-25% |
| Network Lifetime | Shorter | Longer | 20-30% |
| Avg Hop Count | 3-4 hops | 2-3 hops | 25-35% |
| Routing Flexibility | Low (1 path) | High (5 methods) | N/A |
| Packet Delivery Ratio | ~85% | ~95% | +10% |
| Network Resilience | Low | High | N/A |

---

### Configuration for Fair Comparison

**Ensure same settings in config.py:**

```python
# Network
SIM_NODE_COUNT = 100
NODE_TX_RANGE = 100
SIMULATION_DURATION = 2000

# Energy Model (MUST BE SAME)
ENABLE_ENERGY_MODEL = True
INITIAL_ENERGY_JOULES = 10000
TX_ENERGY_PER_BYTE = 0.10
RX_ENERGY_PER_BYTE = 0.05
IDLE_ENERGY_PER_SECOND = 0.00001
SLEEP_ENERGY_PER_SECOND = 0.000001

# For V3 only
ENABLE_DATA_GENERATION = False  # Disable for fair comparison
ENABLE_NODE_FAILURE = False     # Disable for fair comparison
```

---

### Research Questions

1. **Energy Efficiency:** Does hybrid routing reduce energy consumption?
2. **Scalability:** How do protocols perform with 50, 100, 200 nodes?
3. **Network Lifetime:** Which protocol keeps more nodes alive longer?
4. **Traffic Load:** How does performance change with different data generation rates?
5. **Resilience:** How do protocols handle node failures?

---

## Support

For issues or questions:
1. Check troubleshooting section
2. Review log files (simulation_log.txt)
3. Verify configuration (config.py)
4. Check documentation files

---

**Happy Simulating!**

