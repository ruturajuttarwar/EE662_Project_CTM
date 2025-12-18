# CSV Table Population Fix - V3

## Problem
The `child_networks_table.csv` and `members_table.csv` were empty after simulation because the tables were initialized but never populated during network formation.

## Root Cause
- `members_table` and `child_networks_table` were created in `__init__` but no code was adding entries when:
  - Nodes joined CHs (direct or via router)
  - Yellows became CHs
  - Router promotions occurred

## Solution Implemented

### 1. Populate `members_table` on Direct Join
**Location:** Line ~745, when CH accepts JOIN_REQUEST

```python
# Normal join
new_yellow_addr = wsn.Addr(self.ch_addr.net_addr, yellow_id)
self.send_join_reply(yellow_id, new_yellow_addr)

# Populate members_table
if yellow_id not in self.members_table:
    self.members_table.append(yellow_id)
    self.log(f"[CH] Added {yellow_id} to members_table (direct join)")
```

**Effect:** When a yellow directly joins a CH, it's added to the CH's members_table.

---

### 2. Populate Tables on Router Promotion Approval
**Location:** Line ~780, when ROOT/CH approves NETWORK_REQUEST

```python
# Track the child CH and member
# Add yellow to members (it will become a CH)
if yellow_id not in self.members_table:
    self.members_table.append(yellow_id)

# Add green router to members
if green_id not in self.members_table:
    self.members_table.append(green_id)

# Pre-populate child_networks_table (yellow will become CH with this network)
if yellow_id not in self.child_networks_table:
    self.child_networks_table[yellow_id] = []
new_network_id = yellow_id  # Network ID is same as CH ID
if new_network_id not in self.child_networks_table[yellow_id]:
    self.child_networks_table[yellow_id].append(new_network_id)
    self.log(f"[CH] Pre-added child CH {yellow_id} with network {new_network_id}")
```

**Effect:** When ROOT/CH approves a router promotion:
- Yellow (future CH) is added to members_table
- Green (future router) is added to members_table
- Yellow is pre-added to child_networks_table with its network ID

---

### 3. Router Notifies Parent About New Member
**Location:** Line ~890, when router sends BECOME_CH to yellow

```python
# Router's parent CH should track this member
# The router needs to inform its parent CH about the new member
if self.parent_id is not None:
    member_notice = {
        'type': 'MEMBER_ADDED',
        'member_id': yellow_id,
        'via_router': self.id,
        'dest_gui': self.parent_id,
        'dest': wsn.BROADCAST_ADDR,
        'gui': self.id
    }
    self.send(member_notice, wsn.BROADCAST_ADDR)
```

**Effect:** Router informs its parent CH about the new member being promoted.

---

### 4. CH Handles MEMBER_ADDED Message
**Location:** Line ~755, new message handler in CH section

```python
if pck['type'] == 'MEMBER_ADDED':
    # Router notifying parent CH about new member
    if pck.get('dest_gui') == self.id:
        member_id = pck['member_id']
        router_id = pck['via_router']
        
        if member_id not in self.members_table:
            self.members_table.append(member_id)
            self.log(f"[CH] Added {member_id} to members_table (via router {router_id})")
```

**Effect:** CH receives notification and adds the member to its table (backup mechanism).

---

### 5. New CH Notifies Parent About Creation
**Location:** Line ~1030, when yellow becomes CH after BECOME_CH

```python
# Notify parent CH that we became a CH
if self.parent_id is not None:
    ch_created_notice = {
        'type': 'CHILD_CH_CREATED',
        'child_ch_id': self.id,
        'child_network_id': self.ch_addr.net_addr if hasattr(self.ch_addr, 'net_addr') else self.id,
        'via_router': router_id,
        'dest_gui': self.parent_id,
        'dest': wsn.BROADCAST_ADDR,
        'gui': self.id
    }
    self.send(ch_created_notice, wsn.BROADCAST_ADDR)
    self.log(f"[CH] Notified parent {self.parent_id} about CH creation")
```

**Effect:** Newly created CH notifies its parent about the creation.

---

### 6. Parent CH Handles CHILD_CH_CREATED Message
**Location:** Line ~765, new message handler in CH section

```python
if pck['type'] == 'CHILD_CH_CREATED':
    # Child notifying parent that it became a CH
    if pck.get('dest_gui') == self.id:
        child_ch_id = pck['child_ch_id']
        child_network_id = pck['child_network_id']
        router_id = pck.get('via_router')
        
        # Add to child_networks_table
        if child_ch_id not in self.child_networks_table:
            self.child_networks_table[child_ch_id] = []
        
        if child_network_id not in self.child_networks_table[child_ch_id]:
            self.child_networks_table[child_ch_id].append(child_network_id)
            self.log(f"[CH] Added child CH {child_ch_id} (network {child_network_id}) via router {router_id}")
```

**Effect:** Parent CH receives notification and updates child_networks_table (backup mechanism).

---

### 7. Fix CSV Export for Empty Tables
**Location:** Line ~1268, in write_members_table_csv()

```python
# Before:
if hasattr(node, "members_table"):

# After:
if hasattr(node, "members_table") and node.members_table:  # Check if not empty
```

**Effect:** Only export CHs that actually have members, avoiding empty rows.

---

## Data Flow Example

### Scenario: Yellow 60 becomes CH via Router 51

1. **Green 51 sends NETWORK_REQUEST to CH 62**
   - CH 62 receives request

2. **CH 62 approves promotion** (Line ~780)
   - Adds yellow 60 to `members_table`
   - Adds green 51 to `members_table`
   - Adds yellow 60 to `child_networks_table` with network ID 60

3. **Green 51 becomes ROUTER** (Line ~890)
   - Sends BECOME_CH to yellow 60
   - Sends MEMBER_ADDED to parent CH 62

4. **CH 62 receives MEMBER_ADDED** (Line ~755)
   - Confirms yellow 60 in members_table (already there from step 2)

5. **Yellow 60 becomes CH** (Line ~1030)
   - Sends CHILD_CH_CREATED to parent CH 62

6. **CH 62 receives CHILD_CH_CREATED** (Line ~765)
   - Confirms yellow 60 in child_networks_table (already there from step 2)

---

## Expected CSV Output

### child_networks_table.csv
```csv
node_id,node_role,child_count,children
81,ROOT,3,"73(CLUSTER_HEAD)[73];92(CLUSTER_HEAD)[92];90(CLUSTER_HEAD)[90]"
73,CLUSTER_HEAD,4,"62(CLUSTER_HEAD)[62];65(CLUSTER_HEAD)[65];84(CLUSTER_HEAD)[84];93(CLUSTER_HEAD)[93]"
62,CLUSTER_HEAD,1,"60(CLUSTER_HEAD)[60]"
19,CLUSTER_HEAD,2,"9(CLUSTER_HEAD)[9];8(CLUSTER_HEAD)[8]"
```

### members_table.csv
```csv
node_id,node_role,member_count,members
81,ROOT,6,"73(CLUSTER_HEAD);92(CLUSTER_HEAD);90(CLUSTER_HEAD);82(ROUTER);80(ROUTER);72(ROUTER)"
73,CLUSTER_HEAD,8,"62(CLUSTER_HEAD);65(REGISTERED);84(REGISTERED);93(REGISTERED);72(ROUTER);61(ROUTER);51(ROUTER);71(ROUTER)"
62,CLUSTER_HEAD,2,"60(CLUSTER_HEAD);51(ROUTER)"
19,CLUSTER_HEAD,4,"9(ROUTER);18(ROUTER);8(REGISTERED);7(REGISTERED)"
10,CLUSTER_HEAD,3,"0(REGISTERED);1(REGISTERED);11(ROUTER)"
```

---

## New Message Types Added

1. **MEMBER_ADDED**
   - Sent by: ROUTER
   - Received by: Parent CH
   - Purpose: Notify parent about new member via router

2. **CHILD_CH_CREATED**
   - Sent by: New CH
   - Received by: Parent CH
   - Purpose: Notify parent about CH creation

---

## Benefits

1. **Complete Network Visibility:** CHs now know all their members and child CHs
2. **Accurate CSV Export:** Tables are populated with real network structure
3. **Redundant Tracking:** Both pre-population and notification ensure data consistency
4. **Debugging Aid:** Logs show when members/children are added
5. **Network Analysis:** Can analyze cluster sizes, hierarchy depth, router usage

---

## Testing Validation

After running simulation, verify:

✅ **child_networks_table.csv** shows CH-to-CH hierarchy
✅ **members_table.csv** shows all cluster members (CHs, routers, registered nodes)
✅ **neighbors_table.csv** shows physical connectivity (already working)
✅ Log messages show table population: `[CH] Added X to members_table`
✅ Log messages show child tracking: `[CH] Pre-added child CH X with network Y`

---

## Status: ✅ IMPLEMENTED

All changes have been applied to `data_collection_tree_v3.py` and syntax validated.
