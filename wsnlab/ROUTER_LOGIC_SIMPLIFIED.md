# Router Logic Simplified - V2

## Problem
- Simulation stuck at 20 seconds
- Outer nodes not joining network
- Complex router promotion logic causing deadlocks

## Solution: Simplified Router/CH Logic

### Core Design
**Simple flag-based approach:**
1. Yellow receives CH/ROOT heartbeat → Join directly (no router logic)
2. Yellow receives GREEN heartbeat → Enable router logic flag
3. Timer fires → Yellow broadcasts JOIN_REQUEST → Greens respond → Yellow becomes CH
4. After becoming CH → Disable flag

---

## Implementation

### 1. Heartbeat Handler (UNREGISTERED)
**Location:** Line ~1077

```python
if self.role == Roles.UNREGISTERED:
    if pck['type'] == 'HEART_BEAT':
        sender_role = pck.get('role')
        sender_id = pck.get('gui')
        
        # Update neighbor first
        self.update_neighbor(pck)
        
        # CASE 1: CH/ROOT heartbeat → Direct join
        if sender_role in [Roles.CLUSTER_HEAD, Roles.ROOT]:
            if self.addr is None:  # Not joined yet
                self.log(f"[YELLOW] CH/ROOT {sender_id} heartbeat - direct join")
                # Disable router logic
                self.router_logic_enabled = False
                self.processing_nominations = False
                self.waiting_for_router_promotion = False
                if hasattr(self, 'available_greens'):
                    del self.available_greens
                self.kill_timer('TIMER_SELECT_GREEN')
                # Join immediately
                if len(self.candidate_parents_table) > 0:
                    self.select_and_join()
            return
        
        # CASE 2: GREEN heartbeat → Enable router logic
        elif sender_role == Roles.REGISTERED:
            if self.addr is None and not self.router_logic_enabled:
                self.log(f"[YELLOW] GREEN {sender_id} heartbeat - router logic enabled")
                self.router_logic_enabled = True  # Enable flag
            return
```

**Logic:**
- CH/ROOT heartbeat → Disable router logic, join immediately
- GREEN heartbeat → Enable router logic flag (timer will handle rest)

---

### 2. Select and Join Function
**Location:** Line ~252

```python
def select_and_join(self):
    """
    SIMPLIFIED JOIN LOGIC:
    1. If router_logic_enabled = False → Join CH/ROOT directly
    2. If router_logic_enabled = True → Broadcast to trigger router/CH creation
    """
    # Prevent duplicate JOIN_REQUEST
    if self.addr is not None:
        return
    
    # Safety check
    if len(self.candidate_parents_table) == 0:
        return
    
    # Categorize candidates
    ch_candidates = []
    green_candidates = []
    router_candidates = []
    
    for gui in self.candidate_parents_table:
        if gui in self.neighbors_table:
            role = self.neighbors_table[gui].get('role')
            if role in [Roles.CLUSTER_HEAD, Roles.ROOT]:
                ch_candidates.append(gui)
            elif role == Roles.REGISTERED:
                green_candidates.append(gui)
            elif role == Roles.ROUTER:
                router_candidates.append(gui)
    
    # CASE 1: Router logic NOT enabled → Direct join
    if not self.router_logic_enabled:
        # Try CH/ROOT first
        if ch_candidates:
            selected = select_closest_by_hop(ch_candidates)
            self.send_join_request(selected_addr)
            return
        
        # Fallback: ROUTER
        if router_candidates:
            selected = select_closest_by_hop(router_candidates)
            self.send_join_request(selected_addr)
            return
    
    # CASE 2: Router logic ENABLED → Broadcast
    if green_candidates:
        self.log(f"[JOIN] Router logic enabled - broadcasting")
        self.send_join_request(wsn.BROADCAST_ADDR)
        self.waiting_for_router_promotion = True
        return
    
    # No greens, fallback to CH
    if ch_candidates:
        selected = select_closest_by_hop(ch_candidates)
        self.send_join_request(selected_addr)
        self.router_logic_enabled = False  # Disable flag
```

**Logic:**
- `router_logic_enabled = False` → Join CH/ROOT/ROUTER directly
- `router_logic_enabled = True` → Broadcast JOIN_REQUEST to greens

---

### 3. JOIN_REPLY Handler
**Location:** Line ~1200

```python
if pck['type'] == 'JOIN_REPLY':
    if pck['dest_gui'] == self.id:
        # ... join logic ...
        
        # Reset router logic flags after successful join
        self.router_logic_enabled = False
        self.waiting_for_router_promotion = False
        self.processing_nominations = False
        if hasattr(self, 'available_greens'):
            del self.available_greens
        self.kill_timer('TIMER_SELECT_GREEN')
```

**Logic:**
- After becoming CH/REGISTERED → Disable all router logic flags

---

### 4. Flag Initialization
**Location:** Line ~120 (init method)

```python
self.router_logic_enabled = False  # Yellow: flag to enable router/CH creation logic
```

---

## Flow Diagram

### Scenario 1: Yellow Near CH
```
Yellow (UNREGISTERED)
  ↓
Receives CH heartbeat
  ↓
router_logic_enabled = False
  ↓
select_and_join() → Direct join to CH
  ↓
Becomes REGISTERED
```

### Scenario 2: Yellow Near Greens (Outer Yellow)
```
Yellow (UNREGISTERED)
  ↓
Receives GREEN heartbeat
  ↓
router_logic_enabled = True
  ↓
Timer fires → select_and_join()
  ↓
Broadcast JOIN_REQUEST
  ↓
Greens respond → Yellow selects best green
  ↓
Yellow sends ROUTER_REQUEST to green
  ↓
Green becomes ROUTER or CH
  ↓
Yellow receives JOIN_REPLY
  ↓
Yellow becomes CH
  ↓
router_logic_enabled = False (reset)
```

---

## Key Changes

1. **Single flag:** `router_logic_enabled` controls behavior
2. **Heartbeat-driven:** CH/ROOT disables flag, GREEN enables flag
3. **Simple select_and_join:** Check flag → Direct join OR Broadcast
4. **Clean reset:** All flags reset after successful join

---

## Benefits

1. **No deadlocks:** Clear state transitions
2. **Fast joins:** CH/ROOT joins are immediate
3. **Router logic only when needed:** Only for outer yellows
4. **Simple debugging:** Single flag to check

---

## Testing

Run simulation and check logs for:
- `[YELLOW] CH/ROOT X heartbeat - direct join` → Direct joins working
- `[YELLOW] GREEN X heartbeat - router logic enabled` → Router logic triggered
- `[JOIN] Router logic enabled - broadcasting` → Broadcast working
- Outer nodes joining network within 30 seconds
