# Fix: Duplicate Router Promotion Issue

## Problem

Multiple greens were becoming ROUTER for the same yellow node:

**Example from logs:**
```
Node #51 [196.29249] [GREEN] Requesting promotion for yellow 60
Node #61 [196.29250] [GREEN] Requesting promotion for yellow 60
Node #62 [196.29255] [CH] Approving: yellow 60 → CH, green 61
Node #62 [196.29259] [CH] Approving: yellow 60 → CH, green 51  ← DUPLICATE!
Node #61 [196.29259] [ROUTER] Promoted to ROUTER
Node #51 [196.29268] [ROUTER] Promoted to ROUTER  ← BOTH BECAME ROUTER!
```

**Result:** Two routers for same yellow, wasting resources

---

## Root Cause

Requests arrived within milliseconds of each other:
1. Green 61 sends NETWORK_REQUEST for yellow 60
2. CH approves green 61, sets lock = True
3. CH releases lock = False immediately
4. Green 51 sends NETWORK_REQUEST (0.001s later)
5. Lock is already False, so CH approves green 51 too!

**Boolean lock alone wasn't enough** because it was released too early.

---

## Solution: Track Yellows Being Promoted

Added a **set** to track which specific yellows are in promotion:

### Change 1: Added Set in init()
```python
self.yellows_being_promoted = set()  # Track which yellows are currently in promotion
```

### Change 2: Check Set in NETWORK_REQUEST Handler
```python
if pck['type'] == 'NETWORK_REQUEST':
    yellow_id = pck['yellow_id']
    green_id = pck['green_id']
    
    # Check if this yellow is already being promoted
    if yellow_id in self.yellows_being_promoted:
        self.log(f"[CH] Yellow {yellow_id} already in promotion, ignoring duplicate from green {green_id}")
        return
    
    # Check global lock
    if self.active_router_promotion:
        self.log(f"[CH] Promotion in progress, rejecting yellow {yellow_id}")
        return
    
    # Add yellow to set and approve
    self.yellows_being_promoted.add(yellow_id)
    self.active_router_promotion = True
    # ... send NETWORK_REPLY ...
    # Don't release lock here!
```

### Change 3: Yellow Sends ROUTER_PROMOTION_COMPLETE
```python
# In BECOME_CH handler:
self.send({
    'dest': self.root_addr,
    'type': 'ROUTER_PROMOTION_COMPLETE',
    'yellow_id': self.id,
    'router_id': router_id,
    'gui': self.id
})
```

### Change 4: CH Releases Lock on Completion
```python
if pck['type'] == 'ROUTER_PROMOTION_COMPLETE':
    yellow_id = pck.get('yellow_id')
    
    # Remove from set
    self.yellows_being_promoted.discard(yellow_id)
    self.log(f"[CH] Promotion complete for yellow {yellow_id}")
    
    # Release lock
    self.active_router_promotion = False
```

---

## How It Works Now

**Scenario: Two greens (51 and 61) request for same yellow (60)**

1. Green 61 sends NETWORK_REQUEST for yellow 60
2. CH receives: 
   - `60 not in yellows_being_promoted` ✓
   - `active_router_promotion = False` ✓
   - Add 60 to set, set lock = True
   - Approve green 61
3. Green 51 sends NETWORK_REQUEST for yellow 60 (0.001s later)
4. CH receives:
   - `60 in yellows_being_promoted` ✗
   - **Ignore duplicate!**
5. Only green 61 becomes ROUTER
6. Green 51 stays REGISTERED
7. Yellow 60 becomes CH
8. Yellow 60 sends ROUTER_PROMOTION_COMPLETE
9. CH removes 60 from set, releases lock
10. Green 51 can now join CH 60 as member!

---

## Expected Logs After Fix

**Before (duplicate routers):**
```
Node #62 [196.29255] [CH] Approving: yellow 60 → CH, green 61
Node #62 [196.29259] [CH] Approving: yellow 60 → CH, green 51  ← BAD
Node #61 [196.29259] [ROUTER] Promoted to ROUTER
Node #51 [196.29268] [ROUTER] Promoted to ROUTER  ← BAD
```

**After (single router):**
```
Node #62 [196.29255] [CH] Approving: yellow 60 → CH, green 61
Node #62 [196.29259] [CH] Yellow 60 already in promotion, ignoring duplicate from green 51
Node #61 [196.29259] [ROUTER] Promoted to ROUTER
Node #51 stays REGISTERED
Node #60 [196.29267] [ROUTER] Became CH
Node #60 [196.29267] [ROUTER] Sent promotion complete to parent
Node #62 [196.29270] [CH] Promotion complete for yellow 60
Node #51 [226.29xxx] [JOIN] Selecting CLUSTER_HEAD 60 - joining as member
```

---

## Benefits

1. **No duplicate routers** - Only one green becomes router per yellow
2. **Other greens stay REGISTERED** - Can join the newly created CH
3. **Better resource usage** - No wasted router nodes
4. **Cleaner network structure** - Each yellow has exactly one router bridge

---

## Summary

- **Added:** `yellows_being_promoted` set to track specific yellows
- **Kept:** Boolean `active_router_promotion` for global lock
- **Result:** Duplicate router promotions prevented!
