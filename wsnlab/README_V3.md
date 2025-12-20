# Data Collection Tree V3 - CTM-AdHoc Hybrid Routing Protocol

## Overview

**Data Collection Tree V3** is an advanced Wireless Sensor Network simulation implementing the **CTM-AdHoc Hybrid Routing Protocol** with automatic router layer, intelligent network maintenance, and multi-table routing decisions.

### Evolution from Previous Version

**Previous (data_collection_tree_CH.py):**
- Basic cluster head formation
- Simple tree structure
- Direct join only
- No router layer
- Single routing method

**V3 (data_collection_tree_v3.py) - CURRENT:**
- **CTM-AdHoc Hybrid Routing** - 5 routing methods
- **3-Table Routing System** - neighbors, members, child_networks
- **Router Layer** - Boolean lock with timeout recovery
- **Network Maintenance** - Automatic cleanup at 4000s
- **Prevention Logic** - Stops invalid connections at source
- **Enhanced Diagnostics** - Comprehensive logging

---

## Key Features

### 1. CTM-AdHoc Hybrid Routing Protocol

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

### 2. Three-Table Routing System

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

### 3. Router Layer - Enhanced

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

### 4. Network Maintenance (4000s)

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

### 5. Prevention Logic

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

### Log File

**simulation_log.txt** - Complete event log
- All node state changes
- Router promotions
- Maintenance actions
- Routing decisions

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

### Check Maintenance Actions
```bash
# Search for maintenance in log
grep "MAINTENANCE" simulation_log.txt

# Count killed nodes
grep "Killed" simulation_log.txt | wc -l

# Count demoted routers
grep "Demoted" simulation_log.txt | wc -l
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

**Version:** 3.0  
**Status:** Production Ready  
**Last Updated:** December 2024  
**Tested:** 100 nodes, 5000 seconds, multiple runs  
**Coverage:** ~95% nodes connected  
**Stability:** Self-healing with maintenance  

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

**Happy Simulating!**
