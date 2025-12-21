import random
from enum import Enum
import sys
sys.path.insert(1, '.')
from source import wsnlab_vis as wsn
import math
from source import config
from collections import Counter
import signal
import atexit
import csv
import numpy as np



# Track where each node is placed
NODE_POS = {}  # {node_id: (x, y)}

# Role tracking
ROLE_COUNTS = Counter()  # live tally per Roles enum

# Energy tracking (global list for CSV export)
ENERGY_SAMPLES = []  # Stores energy samples over time


Roles = Enum('Roles', 'UNDISCOVERED UNREGISTERED ROOT REGISTERED CLUSTER_HEAD ROUTER')
"""Enumeration of roles"""

# CTM-AdHoc Hybrid Routing Configuration (from config)
NEIGHBOR_TIMEOUT = getattr(config, 'NEIGHBOR_TIMEOUT', 30)  # seconds - remove stale neighbors
ENABLE_HYBRID_ROUTING = getattr(config, 'ENABLE_HYBRID_ROUTING', True)  # Toggle CTM-AdHoc hybrid routing

# Multi-Hop Neighbor Discovery Configuration (from config)
ENABLE_MULTIHOP_NEIGHBORS = getattr(config, 'ENABLE_MULTIHOP_NEIGHBORS', True)  # Toggle multi-hop discovery
NEIGHBOR_SHARE_INTERVAL = getattr(config, 'NEIGHBOR_SHARE_INTERVAL', 30)  # seconds - share neighbor table interval
MAX_HOP_COUNT = getattr(config, 'MAX_HOP_COUNT', 2)  # Maximum hop count for multi-hop neighbors

# Cluster Management Configuration (from config)
MIN_CLUSTER_SIZE = getattr(config, 'MIN_CLUSTER_SIZE', 3)
YELLOW_NODE_CH_TIMEOUT = getattr(config, 'YELLOW_NODE_CH_TIMEOUT', 60)
YELLOW_NODE_CH_TIMEOUT_VARIANCE = getattr(config, 'YELLOW_NODE_CH_TIMEOUT_VARIANCE', 30)

# Router Layer Configuration (from config)
ENABLE_ROUTER_LAYER = getattr(config, 'ENABLE_ROUTER_LAYER', True)
ROUTER_HEARTBEAT_INTERVAL = getattr(config, 'ROUTER_HEARTBEAT_INTERVAL', 60)

# Energy Model Configuration (from config)
ENABLE_ENERGY_MODEL = getattr(config, 'ENABLE_ENERGY_MODEL', False)
INITIAL_ENERGY_JOULES = getattr(config, 'INITIAL_ENERGY_JOULES', 10000)
TX_ENERGY_PER_BYTE = getattr(config, 'TX_ENERGY_PER_BYTE', 0.0001)
RX_ENERGY_PER_BYTE = getattr(config, 'RX_ENERGY_PER_BYTE', 0.00005)
IDLE_ENERGY_PER_SECOND = getattr(config, 'IDLE_ENERGY_PER_SECOND', 0.00001)
SLEEP_ENERGY_PER_SECOND = getattr(config, 'SLEEP_ENERGY_PER_SECOND', 0.000001)
ENABLE_PACKET_LOSS = getattr(config, 'ENABLE_PACKET_LOSS', False)
PACKET_LOSS_PROBABILITY = getattr(config, 'PACKET_LOSS_PROBABILITY', 0.1)
ENERGY_SAMPLE_INTERVAL = getattr(config, 'ENERGY_SAMPLE_INTERVAL', 100)




###########################################################
class SensorNode(wsn.Node):
    """SensorNode class is inherited from Node class in wsnlab.py.
    It will run data collection tree construction algorithms with CTM-AdHoc hybrid routing.

    Attributes:
        role (Roles): role of node
        is_root_eligible (bool): keeps eligibility to be root
        c_probe (int): probe message counter
        th_probe (int): probe message threshold
        neighbors_table (Dict): keeps the neighbor information with received heart beat messages
        neighbor_last_seen (Dict): timestamp of last heartbeat from each neighbor (for timeout)
    """

    ###################
    def init(self):
        """Initialization of node. Setting all attributes of node.
        At the beginning node needs to be sleeping and its role should be UNDISCOVERED.:

        """
        self.scene.nodecolor(self.id, 1, 1, 1) # sets self color to white
        self.sleep()
        self.addr = None
        self.ch_addr = None
        self.parent_gui = None
        self.root_addr = None
        self.set_role(Roles.UNDISCOVERED)
        self.is_root_eligible = True if self.id == ROOT_ID else False
        self.c_probe = 0  # c means counter and probe is the name of counter
        self.th_probe = 10  # th means threshold and probe is the name of threshold
        self.hop_count = 99999
        self.neighbors_table = {}  # keeps neighbor information with received HB messages
        self.neighbor_last_seen = {}  # CTM-AdHoc: timestamp of last contact with each neighbor
        self.candidate_parents_table = []
        self.child_networks_table = {}
        self.members_table = []
        self.received_JR_guis = []  # keeps received Join Request global unique ids
        
        # CTM-AdHoc routing statistics
        self.routing_stats = {
            'direct_mesh': 0,
            'intra_cluster': 0,
            'downward_tree': 0,
            'upward_tree': 0,
            'multihop_routes': 0,
            'route_failures': 0
        }
        
        # Cluster Management
        self.cluster_size = 0
        self.unregistered_since = None
        
        # Router Layer
        self.connected_CHs = []
        self.router_links = {}
        self.adaptive_ch_timeout = self._calculate_adaptive_ch_timeout()
        
        # Router Nomination System
        self.pending_nominations = {}
        self.nomination_timers = {}
        self.active_router_promotion = False
        self.yellows_being_promoted = set()  # Track which yellows are currently in promotion
        self.cancelled_promotions = set()  # Track cancelled promotions (for greens)
        
        # Multi-Hop Neighbor Discovery
        self.multihop_neighbors = {}  # 2-hop and beyond neighbors
        self.neighbor_share_sequence = 0  # Sequence number for neighbor table updates
        
        # Energy Model
        if ENABLE_ENERGY_MODEL:
            self.initial_energy = INITIAL_ENERGY_JOULES
            self.remaining_energy = INITIAL_ENERGY_JOULES
            self.is_alive = True
            
            # Time tracking per state
            self.time_in_tx = 0.0
            self.time_in_rx = 0.0
            self.time_in_idle = 0.0
            self.time_in_sleep = 0.0
            self.last_energy_update = 0.0  # Will be set to self.now on first use
            
            # Energy consumption by source
            self.energy_tx = 0.0
            self.energy_rx = 0.0
            self.energy_idle = 0.0
            self.energy_sleep = 0.0
            
            # Packet statistics
            self.packets_sent = 0
            self.packets_received = 0
            self.packets_lost = 0
            self.bytes_sent = 0
            self.bytes_received = 0

    ###################
    def run(self):
        """Setting the arrival timer to wake up after firing.

        Args:

        Returns:

        """
        self.set_timer('TIMER_ARRIVAL', self.arrival)

    ###################

    def set_role(self, new_role, *, recolor=True):
        """Central place to switch roles, keep tallies, and (optionally) recolor."""
        old_role = getattr(self, "role", None)
        if old_role is not None:
            ROLE_COUNTS[old_role] -= 1
            if ROLE_COUNTS[old_role] <= 0:
                ROLE_COUNTS.pop(old_role, None)
        ROLE_COUNTS[new_role] += 1
        self.role = new_role

        if recolor:
            if new_role == Roles.UNDISCOVERED:
                self.scene.nodecolor(self.id, 1, 1, 1)
            elif new_role == Roles.UNREGISTERED:
                self.scene.nodecolor(self.id, 1, 1, 0)
            elif new_role == Roles.REGISTERED:
                self.scene.nodecolor(self.id, 0, 1, 0)
                # Start neighbor sharing timer for multi-hop discovery
                if ENABLE_MULTIHOP_NEIGHBORS:
                    self.set_timer('TIMER_NEIGHBOR_SHARE', NEIGHBOR_SHARE_INTERVAL)
            elif new_role == Roles.CLUSTER_HEAD:
                self.scene.nodecolor(self.id, 0, 0, 1)
                self.draw_tx_range()
            elif new_role == Roles.ROUTER:
                self.scene.nodecolor(self.id, 1, 0.5, 0)  # Bright orange
            elif new_role == Roles.ROOT:
                self.scene.nodecolor(self.id, 0, 0, 0)
                self.set_timer('TIMER_EXPORT_CH_CSV', config.EXPORT_CH_CSV_INTERVAL)
                self.set_timer('TIMER_EXPORT_NEIGHBOR_CSV', config.EXPORT_NEIGHBOR_CSV_INTERVAL)
                self.set_timer('TIMER_EXPORT_ROUTING_STATS', 2000)  # Export routing stats periodically
                self.set_timer('TIMER_MAINTENANCE', 1000)  # Network maintenance
                if ENABLE_ENERGY_MODEL:
                    self.set_timer('TIMER_ENERGY_SAMPLE', ENERGY_SAMPLE_INTERVAL)  # Energy sampling 

    ###################
    # Energy Model Methods
    ###################
    
    def calculate_packet_size(self, packet):
        """Calculate packet size in bytes for energy consumption"""
        if not ENABLE_ENERGY_MODEL:
            return 0
        
        size = 20  # Base header (type, source, dest, etc.)
        
        msg_type = packet.get('type', '')
        if msg_type == 'HEART_BEAT':
            size += 50  # Position, role, hop count, network info
        elif msg_type in ['JOIN_REQUEST', 'JOIN_REPLY', 'JOIN_ACK']:
            size += 35
        elif msg_type in ['NETWORK_REQUEST', 'NETWORK_REPLY']:
            size += 40
        elif msg_type == 'BECOME_CH':
            size += 45
        elif msg_type == 'DATA':
            size += packet.get('payload_size', 100)
        elif msg_type == 'ROUTER_NOMINATION':
            size += 30
        elif msg_type == 'NEIGHBOR_SHARE':
            size += 60  # Neighbor table data
        else:
            size += 30  # Default for other message types
        
        return size
    
    def consume_energy(self, amount, source):
        """Consume energy and track by source (TX/RX/IDLE/SLEEP)"""
        if not ENABLE_ENERGY_MODEL or not hasattr(self, 'is_alive') or not self.is_alive:
            return
        
        self.remaining_energy -= amount
        
        # Track by source
        if source == 'TX':
            self.energy_tx += amount
        elif source == 'RX':
            self.energy_rx += amount
        elif source == 'IDLE':
            self.energy_idle += amount
        elif source == 'SLEEP':
            self.energy_sleep += amount
        
        # Check if node dies from energy depletion
        if self.remaining_energy <= 0:
            self.die_from_energy_depletion()
    
    def die_from_energy_depletion(self):
        """Node runs out of energy and dies permanently"""
        if not hasattr(self, 'is_alive'):
            return
        
        self.is_alive = False
        self.remaining_energy = 0
        
        # Turn off radio - set to UNDISCOVERED
        self.set_role(Roles.UNDISCOVERED, recolor=False)
        
        # Stop all timers
        self.kill_timer('TIMER_HEART_BEAT')
        self.kill_timer('TIMER_JOIN_REQUEST')
        self.kill_timer('TIMER_YELLOW_CH')
        self.kill_timer('TIMER_ROUTER_HB')
        self.kill_timer('TIMER_NEIGHBOR_SHARE')
        
        # Log death
        self.log(f"[ENERGY] Node {self.id} DIED (energy depleted) at {self.now:.2f}s")
        
        # Visual indication - gray for dead
        self.scene.nodecolor(self.id, 0.5, 0.5, 0.5)
    
    def update_idle_energy(self):
        """Update idle/sleep energy consumption based on time elapsed"""
        if not ENABLE_ENERGY_MODEL or not hasattr(self, 'is_alive') or not self.is_alive:
            return
        
        # Initialize last_energy_update if not set
        if self.last_energy_update == 0.0:
            self.last_energy_update = self.now
            return
        
        time_delta = self.now - self.last_energy_update
        self.last_energy_update = self.now
        
        if time_delta <= 0:
            return
        
        # Determine state (sleep or idle)
        if self.role == Roles.UNDISCOVERED:
            # Sleeping
            energy = time_delta * SLEEP_ENERGY_PER_SECOND
            self.consume_energy(energy, 'SLEEP')
            self.time_in_sleep += time_delta
        else:
            # Idle listening
            energy = time_delta * IDLE_ENERGY_PER_SECOND
            self.consume_energy(energy, 'IDLE')
            self.time_in_idle += time_delta


    
    def become_unregistered(self):
        if self.role != Roles.UNDISCOVERED:
            self.kill_all_timers()
            self.log('I became UNREGISTERED')
        self.scene.nodecolor(self.id, 1, 1, 0)
        # Safely erase parent link if it exists
        if self.parent_gui is not None:
            try:
                self.erase_parent()
            except (KeyError, ValueError):
                # Link doesn't exist in visualization, that's okay
                pass
        self.addr = None
        self.ch_addr = None
        self.parent_gui = None
        self.root_addr = None
        self.set_role(Roles.UNREGISTERED)
        self.c_probe = 0
        self.th_probe = 10
        self.hop_count = 99999
        self.neighbors_table = {}
        self.candidate_parents_table = []
        self.child_networks_table = {}
        self.members_table = []
        self.received_JR_guis = []  # keeps received Join Request global unique ids
        self.unregistered_since = self.now  # Track when became yellow
        self.send_probe()
        # Set to 15s to give router promotion time to complete (takes ~7-10s)
        self.set_timer('TIMER_JOIN_REQUEST', 30)
        
        # Recalculate adaptive timeout and adjust for density
        self.adaptive_ch_timeout = self._calculate_adaptive_ch_timeout()
        
        # Set adaptive timer to become CH if stuck yellow too long
        self.set_timer('TIMER_YELLOW_CH', self.adaptive_ch_timeout)
    
    ###################
    # Override send() to track TX energy
    ###################
    
    def send(self, pck):
        """Override send to track TX energy consumption"""
        # Check if node is alive
        if ENABLE_ENERGY_MODEL and hasattr(self, 'is_alive') and not self.is_alive:
            return  # Dead nodes can't send
        
        # Update idle energy before TX
        if ENABLE_ENERGY_MODEL:
            self.update_idle_energy()
        
        # Check packet loss
        if ENABLE_PACKET_LOSS and hasattr(self, 'packets_lost'):
            if random.random() < PACKET_LOSS_PROBABILITY:
                self.packets_lost += 1
                return  # Packet lost
        
        # Calculate TX energy
        if ENABLE_ENERGY_MODEL and hasattr(self, 'bytes_sent'):
            packet_size = self.calculate_packet_size(pck)
            tx_energy = packet_size * TX_ENERGY_PER_BYTE
            self.consume_energy(tx_energy, 'TX')
            self.bytes_sent += packet_size
            self.packets_sent += 1
            tx_time = packet_size / 250000  # 250 kbps data rate
            self.time_in_tx += tx_time
        
        # Call parent send
        super().send(pck)

    ###################
    def update_neighbor(self, pck):
        pck['arrival_time'] = self.now
        # compute Euclidean distance between self and neighbor
        if pck['gui'] in NODE_POS and self.id in NODE_POS:
            x1, y1 = NODE_POS[self.id]
            x2, y2 = NODE_POS[pck['gui']]
            pck['distance'] = math.hypot(x1 - x2, y1 - y2)
        self.neighbors_table[pck['gui']] = pck
        
        # CTM-AdHoc: Update last seen timestamp for neighbor timeout
        self.neighbor_last_seen[pck['gui']] = self.now
        
        # Track CH heartbeats for adaptive promotion
        if pck.get('role') == Roles.CLUSTER_HEAD:
            self.last_ch_heartbeat_time = self.now

        if pck['gui'] not in self.child_networks_table.keys() or pck['gui'] not in self.members_table:
            if pck['gui'] not in self.candidate_parents_table:
                self.candidate_parents_table.append(pck['gui'])
    
    def clean_stale_neighbors(self):
        """CTM-AdHoc: Remove neighbors that haven't sent heartbeat within NEIGHBOR_TIMEOUT"""
        stale_neighbors = []
        for gui, last_seen in self.neighbor_last_seen.items():
            if self.now - last_seen > NEIGHBOR_TIMEOUT:
                stale_neighbors.append(gui)
        
        for gui in stale_neighbors:
            if gui in self.neighbors_table:
                del self.neighbors_table[gui]
            if gui in self.neighbor_last_seen:
                del self.neighbor_last_seen[gui]
            if gui in self.candidate_parents_table:
                self.candidate_parents_table.remove(gui)
            self.log(f"Removed stale neighbor {gui}")
        
        # Multi-Hop: Clean stale 2-hop neighbors
        if ENABLE_MULTIHOP_NEIGHBORS:
            stale_multihop = []
            for gui, info in self.multihop_neighbors.items():
                if self.now - info['last_seen'] > NEIGHBOR_TIMEOUT * 2:  # 2x timeout for multi-hop
                    stale_multihop.append(gui)
            
            for gui in stale_multihop:
                del self.multihop_neighbors[gui]
            
            if len(stale_multihop) > 0:
                self.log(f"[MultiHop] Removed {len(stale_multihop)} stale 2-hop neighbors")
    


    def select_and_join(self):
        """Join logic - prefer REGISTERED/ROUTER nodes to trigger router nomination"""
        # Safety check: if no candidates, shouldn't be called
        if len(self.candidate_parents_table) == 0:
            self.log(f"[JOIN] select_and_join called with no candidates - waiting for responses")
            return
        
        registered_candidates = []
        router_candidates = []
        ch_candidates = []
        
        for gui in self.candidate_parents_table:
            if gui in self.neighbors_table:
                role = self.neighbors_table[gui].get('role')
                if role == Roles.REGISTERED:
                    registered_candidates.append(gui)
                elif role == Roles.ROUTER:
                    router_candidates.append(gui)
                elif role in [Roles.CLUSTER_HEAD, Roles.ROOT]:
                    ch_candidates.append(gui)
        
        if ch_candidates:
            min_hop = 99999
            min_hop_gui = None
            for gui in ch_candidates:
                if gui in self.neighbors_table:
                    hop = self.neighbors_table[gui]['hop_count']
                    if hop < min_hop or (hop == min_hop and (min_hop_gui is None or gui < min_hop_gui)):
                        min_hop = hop
                        min_hop_gui = gui
            
            if min_hop_gui is not None:
                selected_addr = self.neighbors_table[min_hop_gui]['source']
                role = self.neighbors_table[min_hop_gui].get('role')
                self.log(f"[JOIN] Selecting {role.name} {min_hop_gui} (hop={min_hop}) - no greens available")
                self.send_join_request(selected_addr)
                self.set_timer('TIMER_JOIN_REQUEST', 15)
                return
            
        # Try REGISTERED nodes first ( router nomination)
        if registered_candidates:
            min_distance = 999999
            closest_green = None
            
            for gui in registered_candidates:
                if gui in self.neighbors_table:
                    distance = self.neighbors_table[gui]['distance']
                    if distance < min_distance:
                        min_distance = distance
                        closest_green = gui
            
            if closest_green is not None:
                selected_addr = self.neighbors_table[closest_green]['source']
                self.log(f"[JOIN] Selecting REGISTERED {closest_green} (dist={min_distance:.1f}m) - direct to green")
                self.send_join_request(selected_addr)
                self.set_timer('TIMER_JOIN_REQUEST', 15)
                return
        
        # Try ROUTER nodes second
        if router_candidates:
            min_hop = 99999
            min_hop_gui = None
            for gui in router_candidates:
                if gui in self.neighbors_table:
                    hop = self.neighbors_table[gui]['hop_count']
                    if hop < min_hop or (hop == min_hop and (min_hop_gui is None or gui < min_hop_gui)):
                        min_hop = hop
                        min_hop_gui = gui
            
            if min_hop_gui is not None:
                selected_addr = self.neighbors_table[min_hop_gui]['source']
                self.log(f"[JOIN] Selecting ROUTER {min_hop_gui} (hop={min_hop})")
                self.send_join_request(selected_addr)
                self.set_timer('TIMER_JOIN_REQUEST', 15)
                return
        # Fallback: Use CH/ROOT only if no REGISTERED or ROUTER available
        
        
        # No valid candidates in neighbor table yet
        self.log(f"[JOIN] Candidates in table but not in neighbors yet - waiting for next cycle")
    
    ###################
    def _calculate_adaptive_ch_timeout(self):
        """Calculate adaptive CH promotion timeout based on node density"""
        base_timeout = YELLOW_NODE_CH_TIMEOUT
        variance = random.uniform(0, YELLOW_NODE_CH_TIMEOUT_VARIANCE)
        
        # Add density-based adjustment (calculated later when neighbors are known)
        return base_timeout + variance
    
    def has_ch_in_range(self):
        """Check if there's a cluster head in communication range"""
        for gui, neighbor_info in self.neighbors_table.items():
            if neighbor_info.get('role') == Roles.CLUSTER_HEAD:
                return True
        return False
    
   
    def time_since_last_ch_heartbeat(self):
        """Calculate time since last CH heartbeat was received"""
        if self.last_ch_heartbeat_time is None:
            return float('inf')
        return self.now - self.last_ch_heartbeat_time
    

    def calculate_distance_to_node(self, target_id):
        """Calculate Euclidean distance to another node"""
        if self.id not in NODE_POS or target_id not in NODE_POS:
            return 999999  # Unknown distance
        
        my_pos = NODE_POS[self.id]
        target_pos = NODE_POS[target_id]
        distance = math.hypot(my_pos[0] - target_pos[0], my_pos[1] - target_pos[1])
        return distance
    

    
    def send_probe(self):
        """Sending probe message to be discovered and registered.

        Args:

        Returns:

        """
        self.send({'dest': wsn.BROADCAST_ADDR, 'type': 'PROBE'})

    ###################
    def send_heart_beat(self):
        """Sending heart beat message

        Args:

        Returns:

        """
        pck = {'dest': wsn.BROADCAST_ADDR,
               'type': 'HEART_BEAT',
               'source': self.ch_addr if self.ch_addr is not None else self.addr,
               'gui': self.id,
               'role': self.role,
               'addr': self.addr,
               'ch_addr': self.ch_addr,
               'hop_count': self.hop_count}
        
        # Include cluster size if we're a CH
        if self.role == Roles.CLUSTER_HEAD:
            pck['cluster_size'] = self.cluster_size
        
        self.send(pck)

    ###################
    def send_join_request(self, dest):
        """Sending join request message to join destination network
        
        ROUTER LOGIC: Broadcasts JOIN_REQUEST so multiple greens can receive it,
         CH selects closest green based on distance.

        Args:
            dest (Addr): Address of destination node (ignored, using broadcast)
        Returns:

        """
        # Broadcast so ALL greens
        if dest is None:
            dest = wsn.BROADCAST_ADDR
    
        self.send({'dest': dest, 'type': 'JOIN_REQUEST', 'gui': self.id})

    ###################
    def send_join_reply(self, gui, addr):
        """Sending join reply message to register the node requested to join.

        Args:
            gui (int): Global unique ID
            addr (Addr): Address that will be assigned to new registered node
        Returns:

        """
        self.send({'dest': wsn.BROADCAST_ADDR, 'type': 'JOIN_REPLY', 'source': self.ch_addr,
                   'gui': self.id, 'dest_gui': gui, 'addr': addr, 'root_addr': self.root_addr,
                   'hop_count': self.hop_count+1})

    ###################
    def send_join_ack(self, dest):
        """Sending join acknowledgement message to given destination address.

        Args:
            dest (Addr): Address of destination node
        Returns:

        """
        self.send({'dest': dest, 'type': 'JOIN_ACK', 'source': self.addr,
                   'gui': self.id})

    ###################
    def route_and_forward_package(self, pck):
        """mesh Routing: 3-step routing decision
        
        Step 1: if dest is a direct neighbor
        Step 2: if dest is in same cluster
        Step 3:  if dest cluster is in child networks
        Fallback: Upward Tree Forwarding - forward to parent

        """
        dest_addr = pck.get('dest')
        
        # If no destination or broadcast, use original logic
        if dest_addr is None or dest_addr == wsn.BROADCAST_ADDR:
            self.send(pck)
            return
        
        if not ENABLE_HYBRID_ROUTING:
            # Original tree-based routing
            if self.role != Roles.ROOT:
                pck['next_hop'] = self.neighbors_table[self.parent_gui]['ch_addr']
            if self.ch_addr is not None:
                if pck['dest'].net_addr == self.ch_addr.net_addr:
                    pck['next_hop'] = pck['dest']
                else:
                    for child_gui, child_networks in self.child_networks_table.items():
                        if pck['dest'].net_addr in child_networks:
                            pck['next_hop'] = self.neighbors_table[child_gui]['addr']
                            break
            self.send(pck)
            return
        
        # CTM-AdHoc Hybrid Routing Logic
        routed = False
        
        #Direct  check if destination is a direct neighbor
        for neighbor_gui, neighbor_info in self.neighbors_table.items():
            neighbor_addr = neighbor_info.get('addr')
            if neighbor_addr == dest_addr:
                pck['next_hop'] = dest_addr
                self.routing_stats['direct_mesh'] += 1
                self.log(f"[CTM-AdHoc] Direct mesh to neighbor {neighbor_gui}")
                self.send(pck)
                routed = True
                break
        
        if routed:
            return
        
        # Step 2: if we're a cluster head and dest is in our cluster
        if self.role == Roles.CLUSTER_HEAD and self.ch_addr is not None:
            if hasattr(dest_addr, 'net_addr') and dest_addr.net_addr == self.ch_addr.net_addr:
                # Destination is in our cluster
                for member_gui in self.members_table:
                    if member_gui in self.neighbors_table:
                        member_addr = self.neighbors_table[member_gui].get('addr')
                        if member_addr == dest_addr:
                            pck['next_hop'] = dest_addr
                            self.routing_stats['intra_cluster'] += 1
                            self.log(f"[CTM-AdHoc] Intra-cluster to member {member_gui}")
                            self.send(pck)
                            routed = True
                            break
        
        if routed:
            return
        
        # Step 2.5: Multi-Hop Mesh Forwarding - check if destination is a 2-hop neighbor
        if ENABLE_MULTIHOP_NEIGHBORS:
            for neighbor_id, neighbor_info in self.multihop_neighbors.items():
                neighbor_addr = neighbor_info.get('addr')
                if neighbor_addr == dest_addr:
                    # Route through intermediate node
                    via_node = neighbor_info['via']
                    if via_node in self.neighbors_table:
                        pck['next_hop'] = self.neighbors_table[via_node]['addr']
                        self.routing_stats['multihop_routes'] += 1
                        self.log(f"[CTM-AdHoc] Multi-hop to {neighbor_id} via {via_node}")
                        self.send(pck)
                        routed = True
                        break
        
        if routed:
            return
        
        # STEP 3: Downward Tree Forwarding - check if dest cluster is in child networks
        if self.ch_addr is not None and hasattr(dest_addr, 'net_addr'):
            for child_gui, child_networks in self.child_networks_table.items():
                if dest_addr.net_addr in child_networks:
                    if child_gui in self.neighbors_table:
                        pck['next_hop'] = self.neighbors_table[child_gui]['addr']
                        self.routing_stats['downward_tree'] += 1
                        self.log(f"[CTM-AdHoc] Downward tree via child {child_gui}")
                        self.send(pck)
                        routed = True
                        break
        
        if routed:
            return
        
        # FALLBACK: Upward Tree Forwarding - forward to parent
        if self.role != Roles.ROOT and self.parent_gui is not None:
            if self.parent_gui in self.neighbors_table:
                pck['next_hop'] = self.neighbors_table[self.parent_gui]['ch_addr']
                self.routing_stats['upward_tree'] += 1
                self.log(f"[CTM-AdHoc] Upward tree to parent {self.parent_gui}")
                self.send(pck)
                routed = True
        
        if not routed:
            # Route failure - trigger re-probe and neighbor share
            self.routing_stats['route_failures'] += 1
            self.log(f"[CTM-AdHoc] Route failure to {dest_addr}, triggering re-probe")
            self.send_probe()
            if ENABLE_MULTIHOP_NEIGHBORS:
                self.send_neighbor_table_share()  # Share neighbors to help discover routes
    

    ###################
    def send_network_request(self):
        """Sending network request message to root address to be cluster head

        Args:

        Returns:

        """
        self.route_and_forward_package({'dest': self.root_addr, 'type': 'NETWORK_REQUEST', 'source': self.addr})

    ###################
    def send_network_reply(self, dest, addr):
        """Sending network reply message to dest address to be cluster head with a new adress

        Args:
            dest (Addr): destination address
            addr (Addr): cluster head address of new network

        Returns:

        """
        self.route_and_forward_package({'dest': dest, 'type': 'NETWORK_REPLY', 'source': self.addr, 'addr': addr})

    ###################
    def send_network_update(self):
        """Sending network update message to parent

        Args:

        Returns:

        """
        if self.ch_addr is None:
            return
        
        if self.parent_gui not in self.neighbors_table:
            return
        
        parent_ch_addr = self.neighbors_table[self.parent_gui].get('ch_addr')
        if not parent_ch_addr:
            return
        
        child_networks = [self.ch_addr.net_addr]
        for networks in self.child_networks_table.values():
            child_networks.extend(networks)
        
        self.send({
            'dest': parent_ch_addr,
            'type': 'NETWORK_UPDATE',
            'source': self.addr,
            'gui': self.id,
            'child_networks': child_networks
        })
    
    ###################
    def send_neighbor_table_share(self):
        """Share neighbor table with direct neighbors for multi-hop discovery
        
         neighbors to learn about 2-hop nodes and build alternative routes.
        Only shares 1-hop neighbors to prevent exponential growth.
        """
        if not ENABLE_MULTIHOP_NEIGHBORS:
            return
        
        # Only share if we have neighbors
        if len(self.neighbors_table) == 0:
            return
        
        # Build list of neighbors to share (only 1-hop, not multi-hop)
        neighbors_to_share = []
        for gui, info in self.neighbors_table.items():
            neighbors_to_share.append({
                'gui': gui,
                'addr': info.get('addr'),
                'role': info.get('role'),
                'hop_count': info.get('hop_count'),
                'distance': info.get('distance', 999)
            })
        
        # Broadcast neighbor table
        self.send({
            'dest': wsn.BROADCAST_ADDR,
            'type': 'NEIGHBOR_SHARE',
            'source': self.addr,
            'gui': self.id,
            'neighbors': neighbors_to_share,
            'sequence': self.neighbor_share_sequence
        })
        
        self.neighbor_share_sequence += 1
        self.log(f"[MultiHop] Shared {len(neighbors_to_share)} neighbors")
    
    ###################
    def process_neighbor_share(self, pck):
        """Process neighbor table shared by another node
        
        Learns about 2-hop neighbors and updates multi-hop routing table.
        """
        if not ENABLE_MULTIHOP_NEIGHBORS:
            return
        
        sender_id = pck.get('gui')
        neighbors = pck.get('neighbors', [])
        
        # Only process if sender is our direct neighbor
        if sender_id not in self.neighbors_table:
            return
        
        # Process each neighbor in the shared table
        for neighbor_info in neighbors:
            neighbor_id = neighbor_info.get('gui')
            
            # Skip if it's ourselves
            if neighbor_id == self.id:
                continue
            
            # Skip if it's already a direct neighbor (1-hop)
            if neighbor_id in self.neighbors_table:
                continue
            
            # Add as 2-hop neighbor
            self.multihop_neighbors[neighbor_id] = {
                'via': sender_id,  # Route through this node
                'hops': 2,
                'distance': neighbor_info.get('distance', 999),
                'addr': neighbor_info.get('addr'),
                'role': neighbor_info.get('role'),
                'last_seen': self.now
            }
        
        if len(neighbors) > 0:
            self.log(f"[MultiHop] Learned {len(neighbors)} 2-hop neighbors via {sender_id}")

    ###################
    def on_receive(self, pck):
        """Executes when a package received. Enhanced with CTM-AdHoc neighbor maintenance.

        Args:
            pck (Dict): received package
        Returns:

        """
        # Energy Model: Check if node is alive
        if ENABLE_ENERGY_MODEL and hasattr(self, 'is_alive') and not self.is_alive:
            return  # Dead nodes can't receive
        
        # Energy Model: Update idle energy before RX
        if ENABLE_ENERGY_MODEL:
            self.update_idle_energy()
        
        # Energy Model: Calculate RX energy
        if ENABLE_ENERGY_MODEL and hasattr(self, 'bytes_received'):
            packet_size = self.calculate_packet_size(pck)
            rx_energy = packet_size * RX_ENERGY_PER_BYTE
            self.consume_energy(rx_energy, 'RX')
            self.bytes_received += packet_size
            self.packets_received += 1
            rx_time = packet_size / 250000  # 250 kbps data rate
            self.time_in_rx += rx_time
        
        # Multi-Hop: Process neighbor table sharing
        if pck.get('type') == 'NEIGHBOR_SHARE':
            self.process_neighbor_share(pck)
            return
        
        # CH Handoff: Process cluster head role transfer
        if pck.get('type') == 'CH_HANDOFF':
            if pck.get('dest_gui') == self.id and self.role == Roles.REGISTERED:
                self.log(f"Receiving CH handoff from {pck.get('source')}")
                # Take over as cluster head
                self.ch_addr = pck.get('ch_addr')
                self.members_table = pck.get('members', [])
                self.cluster_size = len(self.members_table)
                self.set_role(Roles.CLUSTER_HEAD)
                self.scene.nodecolor(self.id, 0, 0, 1)
                self.send_heart_beat()
                self.log(f"Became CH via handoff, managing {self.cluster_size} members")
            return
        
        # CTM-AdHoc: Update neighbor info on ANY packet reception (not just heartbeats)
        if 'gui' in pck and pck['gui'] != self.id:
            if pck['gui'] in self.neighbors_table:
                self.neighbor_last_seen[pck['gui']] = self.now
        
        if self.role in [Roles.ROOT, Roles.CLUSTER_HEAD, Roles.ROUTER]:
            if 'next_hop' in pck.keys() and pck['dest'] != self.addr:
                if self.role == Roles.ROUTER or pck['dest'] != self.ch_addr:
                    self.route_and_forward_package(pck)
                    return
            if pck['type'] == 'HEART_BEAT':
                self.update_neighbor(pck)
            if pck['type'] == 'PROBE':  # it waits and sends heart beat message once received probe message
                # yield self.timeout(.5)
                self.send_heart_beat()
            if pck['type'] == 'JOIN_REQUEST':  # it waits and sends join reply message once received join request
                yellow_id = pck['gui']
                forwarded_by_router = pck.get('forwarded_by_router')
                
                if not self.ch_addr:
                    self.log(f"[ERROR] {self.role.name} {self.id} has no ch_addr, cannot accept JOIN_REQUEST from {yellow_id}")
                    return

                # Normal join
                new_yellow_addr = wsn.Addr(self.ch_addr.net_addr, yellow_id)
                self.send_join_reply(yellow_id, new_yellow_addr)
                
                # Populate members_table (but NOT if yellow is already a CH!)
                # Check if yellow is a CH before adding
                yellow_node = next((n for n in sim.nodes if n.id == yellow_id), None)
                if yellow_node and hasattr(yellow_node, 'role'):
                    if yellow_node.role == Roles.CLUSTER_HEAD:
                        self.log(f"[CH] WARNING: Yellow {yellow_id} is already a CH, NOT adding to members_table")
                    elif yellow_id not in self.members_table:
                        self.members_table.append(yellow_id)
                        self.log(f"[CH] Added {yellow_id} to members_table (direct join)")
                elif yellow_id not in self.members_table:
                    # Node not found or no role, add anyway
                    self.members_table.append(yellow_id)
                    self.log(f"[CH] Added {yellow_id} to members_table (direct join)")


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
            
            if pck['type'] == 'NETWORK_REQUEST':  # it sends a network reply to requested node
                # yield self.timeout(.5)
                if (self.role == Roles.ROOT or self.role == Roles.CLUSTER_HEAD) and ENABLE_ROUTER_LAYER:
                    yellow_id = pck['yellow_id']
                    green_id = pck['green_id']
                    green_addr = pck['green_addr']
                    if yellow_id in self.yellows_being_promoted:
                        self.log(f"[CH] Yellow {yellow_id} already in promotion, ignoring duplicate from green {green_id}")
                        return
                        
                    # Check lock - only ONE promotion at a time
                    if self.active_router_promotion:
                        self.log(f"[CH] Promotion in progress, rejecting yellow {yellow_id}")
                        # Send rejection
                        self.send({
                            'dest': pck['green_addr'],
                            'type': 'NETWORK_REQUEST_REJECTED',
                            'yellow_id': yellow_id,
                            'reason': 'busy',
                            'gui': self.id
                        })
                        return
                    
                    # Approve immediately!
                    self.yellows_being_promoted.add(yellow_id)
                    self.active_router_promotion = True
                    self.set_timer('TIMER_PROMOTION_LOCK_TIMEOUT', 2)
                    self.log(f"[CH] Approving: yellow {yellow_id} → CH, green {green_id}")
                    
                    # Allocate address
                    new_ch_addr = wsn.Addr(yellow_id, 254)
                    
                    # Send approval
                    self.send({
                        'dest': pck['green_addr'],
                        'type': 'NETWORK_REPLY',
                        'new_ch_addr': new_ch_addr,
                        'yellow_id': yellow_id,
                        'router_id': green_id,
                        'source': self.addr,
                        'root_addr': self.root_addr,
                        'hop_count': self.hop_count + 1,
                        'gui': self.id
                    })
                    
                    # Track the child CH and router
                    # Add green router to members (router is a member of this CH)
                    if green_id not in self.members_table:
                        self.members_table.append(green_id)
                        self.log(f"[CH] Added router {green_id} to members_table")
                    
                    # Do NOT add yellow to members_table - it will become a child CH, not a member
                    # Pre-populate child_networks_table (yellow will become CH with this network)
                    if yellow_id not in self.child_networks_table:
                        self.child_networks_table[yellow_id] = []
                    new_network_id = yellow_id  # Network ID is same as CH ID
                    if new_network_id not in self.child_networks_table[yellow_id]:
                        self.child_networks_table[yellow_id].append(new_network_id)
                        self.log(f"[CH] Pre-added child CH {yellow_id} with network {new_network_id}")
                return

            

        elif self.role == Roles.REGISTERED:  # if the node is registered
            if pck['type'] == 'HEART_BEAT':
                self.update_neighbor(pck)
            if pck['type'] == 'PROBE':
                self.log(f"[HEARTBEAT] Received PROBE, sending HEARTBEAT response")
                self.send_heart_beat()
            if pck['type'] == 'PROMOTION_COMPLETE_EARLY':
                # Yellow became CH and notified us early
                yellow_id = pck.get('yellow_id')
                
                if yellow_id in self.yellows_being_promoted:
                    self.yellows_being_promoted.discard(yellow_id)
                    self.log(f"[CH] Yellow {yellow_id} became CH, releasing lock early")
                
                # Release lock and cancel timeout
                self.active_router_promotion = False
                self.kill_timer('TIMER_PROMOTION_LOCK_TIMEOUT')
                return
            if pck['type'] == 'JOIN_REQUEST':  # REGISTERED node receives JOIN_REQUEST
                yellow_id = pck['gui']
                # Calculate distance to yellow
                parent_addr = None
                if self.parent_gui is not None and self.parent_gui in self.neighbors_table:
                    parent_addr = self.neighbors_table[self.parent_gui].get('ch_addr') or self.neighbors_table[self.parent_gui].get('addr')
                elif self.ch_addr is not None:
                    parent_addr = self.ch_addr
                
                if parent_addr:
                    self.send({
                        'dest': parent_addr,
                        'type': 'NETWORK_REQUEST',  
                        'yellow_id': yellow_id,
                        'green_id': self.id,
                        'green_addr': self.addr,
                        'gui': self.id
                    })
                    self.log(f"[GREEN] Requesting promotion for yellow {yellow_id}")
                return
            
            if pck['type'] == 'NETWORK_REPLY':  # it becomes cluster head or router based on context
                # Check if this is a router promotion reply
                yellow_id = pck.get('yellow_id')
                router_id = pck.get('router_id')
                new_ch_addr = pck.get('new_ch_addr')
                
                # Check if this promotion was cancelled
                if yellow_id in self.cancelled_promotions:
                    self.log(f"[ROUTER] Ignoring NETWORK_REPLY for cancelled promotion of yellow {yellow_id}")
                    self.cancelled_promotions.remove(yellow_id)
                    return
                
                if yellow_id and router_id and router_id == self.id:
                    # This is a router promotion - I should become ROUTER, not CH
                    new_ch_addr = pck.get('new_ch_addr')
                    
                    self.log(f"[ROUTER] Received router promotion approval for yellow {yellow_id}")
                    
                    # Promote self to ROUTER
                    self.set_role(Roles.ROUTER)
                    #self.ch_addr = self.addr
                    self.connected_CHs = [self.ch_addr, yellow_id]
                    self.set_timer('TIMER_ROUTER_HB', ROUTER_HEARTBEAT_INTERVAL)
                    
                    
                    
                    # Send BECOME_CH to yellow
                    self.send({
                        'dest': wsn.BROADCAST_ADDR,
                        'type': 'BECOME_CH',
                        'dest_gui': yellow_id,
                        'new_ch_addr': new_ch_addr,
                        'root_addr': self.root_addr,
                        'router_id': self.id,
                        'router_addr': self.addr,
                        'hop_count': self.hop_count + 1,  # Yellow CH will be one hop further
                        'gui': self.id
                    })
                    
                    self.log(f"[ROUTER] Promoted to ROUTER, bridging CHs {self.ch_addr} and {yellow_id}")
                else:
                    # Normal CH promotion (existing logic)
                    self.set_role(Roles.CLUSTER_HEAD)
                    self.scene.nodecolor(self.id, 0, 0, 1)
                    self.ch_addr = pck['new_ch_addr']
                    self.cluster_size = 0  # Initialize cluster size
                    # hop_count stays the same as when REGISTERED (already set from JOIN_REPLY)
                    self.send_network_update()
                    # yield self.timeout(.5)
                    self.send_heart_beat()
                    
                    # Send join replies to all waiting nodes
                    for gui in self.received_JR_guis:
                        # yield self.timeout(random.uniform(.1,.5))
                        self.send_join_reply(gui, wsn.Addr(self.ch_addr.net_addr,gui))
                    
                    self.log(f"Became CH: sent {len(self.received_JR_guis)} join replies")
        
        elif self.role == Roles.ROUTER:  # if the node is a router
            if pck['type'] == 'HEART_BEAT':
                self.update_neighbor(pck)
            if pck['type'] == 'PROBE':
                # ROUTER answers PROBE to help yellows discover it
                self.send_heart_beat()
            if pck['type'] == 'JOIN_REQUEST':
                # ROUTER receives JOIN_REQUEST from yellow
                yellow_id = pck['gui']
                
                # Check if any connected CH has space (based on MIN_CLUSTER_SIZE)
                has_space = False
                for ch_item in self.connected_CHs:
                    # Check if this CH has space
                    for node in sim.nodes:
                        # Compare by node ID
                        node_matches = False
                        if isinstance(ch_item, int):
                            node_matches = (node.id == ch_item)
                        elif hasattr(ch_item, 'node_addr'):
                            node_matches = (node.id == ch_item.node_addr)
                        
                        if node_matches and hasattr(node, 'cluster_size'):
                            # CH has space if under MIN_CLUSTER_SIZE (still forming)
                            if node.cluster_size < MIN_CLUSTER_SIZE:
                                has_space = True
                                self.log(f"[ROUTER] CH {node.id} has space ({node.cluster_size}/{MIN_CLUSTER_SIZE} min)")
                                break
                    if has_space:
                        break
                
                if has_space:
                    # At least one connected CH has space - ignore request
                    # Yellow should join CH directly
                    self.log(f"[ROUTER] Ignoring JOIN_REQUEST from {yellow_id} (connected CH has space)")
                else:
                    # All connected CHs are full or no CHs - accept and forward to parent
                    self.log(f"[ROUTER] Accepting JOIN_REQUEST from {yellow_id} (all CHs full), forwarding to parent")
                    
                    # Forward to parent with router_id marker
                    parent_addr = None
                    if self.parent_gui is not None and self.parent_gui in self.neighbors_table:
                        parent_addr = self.neighbors_table[self.parent_gui].get('ch_addr') or self.neighbors_table[self.parent_gui].get('addr')
                    elif self.ch_addr is not None:
                        parent_addr = self.ch_addr
                    
                    if parent_addr:
                        self.send({
                            'dest': parent_addr,
                            'type': 'JOIN_REQUEST',
                            'gui': yellow_id,
                            'source': self.addr,
                            'forwarded_by_router': self.id  # Mark that this came through router
                        })
                
        elif self.role == Roles.UNDISCOVERED:  # if the node is undiscovered
            if pck['type'] == 'HEART_BEAT':  # it kills probe timer, becomes unregistered and sets join request timer once received heart beat
                self.update_neighbor(pck)
                self.kill_timer('TIMER_PROBE')
                self.become_unregistered()

        if self.role == Roles.UNREGISTERED:  # if the node is unregistered
            if pck['type'] == 'HEART_BEAT':
                self.update_neighbor(pck)
            if pck['type'] == 'BECOME_CH':  # ROUTER tells yellow to become CH
                if pck.get('dest_gui') == self.id and ENABLE_ROUTER_LAYER:
                    router_id = pck.get('router_id')
                    new_ch_addr = pck.get('new_ch_addr')
                    root_addr = pck.get('root_addr')
                    router_addr = pck.get('router_addr')
                    # Validate new_ch_addr
                    
                    
                    self.log(f"[ROUTER] Received BECOME_CH from router {router_id}, promoting to CH")
                    
                    # Kill join timers
                    self.kill_timer('TIMER_JOIN_REQUEST')
                    self.kill_timer('TIMER_YELLOW_CH')
                    
                    # Become CH
                    self.set_role(Roles.CLUSTER_HEAD)
                    self.scene.nodecolor(self.id, 0, 0, 1)
                    self.root_addr = root_addr
                    self.ch_addr = new_ch_addr
                    self.addr = new_ch_addr  # CH's addr is same as ch_addr
                    self.cluster_size = 0
                    
                    # Set router as parent for tree structure
                    self.parent_gui = router_id
                    
                    # Set hop_count from BECOME_CH message
                    self.hop_count = pck.get('hop_count', 2)  # Default to 2 if not provided
                    
                    # Draw connection to router (will be orange because router is orange)
                    if router_id in self.neighbors_table:
                        self.draw_parent()
                    
                    # Start heartbeat
                    self.send_heart_beat()
                    self.set_timer('TIMER_HEART_BEAT', config.HEARTH_BEAT_TIME_INTERVAL)
                    
                    self.log(f"[ROUTER] Became CH (promoted by router {router_id})")
                    self.send_network_update()
                    
                    # Notify parent CH that we became a CH
                    if self.parent_gui is not None:
                        ch_created_notice = {
                            'type': 'CHILD_CH_CREATED',
                            'child_ch_id': self.id,
                            'child_network_id': self.ch_addr.net_addr if hasattr(self.ch_addr, 'net_addr') else self.id,
                            'via_router': router_id,
                            'dest_gui': self.parent_gui,
                            'dest': wsn.BROADCAST_ADDR,
                            'gui': self.id
                        }
                        self.send(ch_created_notice)
                        self.log(f"[CH] Notified parent {self.parent_gui} about CH creation")
        
                    
            if pck['type'] == 'JOIN_REPLY':  # it becomes registered and sends join ack if the message is sent to itself once received join reply
                if pck['dest_gui'] == self.id:
                    # VALIDATION: Check if sender is a ROUTER (invalid - greens should only join CHs)
                    sender_gui = pck['gui']
                    sender_is_router = False
                    for node in sim.nodes:
                        if node.id == sender_gui and hasattr(node, 'role'):
                            if node.role == Roles.ROUTER:
                                sender_is_router = True
                                self.log(f"[JOIN] REJECTED JOIN_REPLY from ROUTER {sender_gui} - greens cannot join routers!")
                                break
                    
                    # Reject JOIN_REPLY from routers
                    if sender_is_router:
                        return  # Ignore this JOIN_REPLY
                    
                    self.addr = pck['addr']
                    self.parent_gui = pck['gui']
                    self.root_addr = pck['root_addr']
                    self.hop_count = pck['hop_count']
                    self.ch_addr = pck['source']  # Set CH address from JOIN_REPLY source
                    self.unregistered_since = None  # Clear yellow timer
                    self.draw_parent()
                    self.kill_timer('TIMER_JOIN_REQUEST')
                    self.kill_timer('TIMER_YELLOW_CH')  # Cancel yellow CH timer
                    self.send_heart_beat()
                    # REGISTERED nodes MUST send heartbeats to help yellows discover them
                    self.set_timer('TIMER_HEART_BEAT', config.HEARTH_BEAT_TIME_INTERVAL)
                    self.send_join_ack(pck['source'])
                    # Check if this node was already a CH (lost parent scenario)
                    if self.role == Roles.CLUSTER_HEAD:
                        # Already a CH, stay as CH and update parent
                        self.send_network_update()
                    else:
                        # Become REGISTERED
                        self.set_role(Roles.REGISTERED)
                    
                    
                    # # sensor implementation
                    # timer_duration =  self.id % 20
                    # if timer_duration == 0: timer_duration = 1
                    # self.set_timer('TIMER_SENSOR', timer_duration)

    ###################
    def on_timer_fired(self, name, *args, **kwargs):
        """Executes when a timer fired.

        Args:
            name (string): Name of timer.
            *args (string): Additional args.
            **kwargs (string): Additional key word args.
        Returns:

        """
        if name == 'TIMER_ARRIVAL':  # it wakes up and set timer probe once time arrival timer fired
            self.scene.nodecolor(self.id, 1, 0, 0)  # sets self color to red
            self.wake_up()
            self.set_timer('TIMER_PROBE', 1)

        elif name == 'TIMER_PROBE':  # it sends probe if counter didn't reach the threshold once timer probe fired.
            if self.c_probe < self.th_probe:
                self.send_probe()
                self.c_probe += 1
                self.set_timer('TIMER_PROBE', 1)
            else:  # if the counter reached the threshold
                if self.is_root_eligible:  # if the node is root eligible, it becomes root
                    self.set_role(Roles.ROOT)
                    self.scene.nodecolor(self.id, 0, 0, 0)
                    self.addr = wsn.Addr(self.id, 254)
                    self.ch_addr = wsn.Addr(self.id, 254)
                    self.root_addr = self.addr
                    self.hop_count = 0
                    self.cluster_size = 0  # Initialize cluster size
                    self.set_timer('TIMER_HEART_BEAT', config.HEARTH_BEAT_TIME_INTERVAL)
                else:  # otherwise it keeps trying to sending probe after a long time
                    self.c_probe = 0
                    self.set_timer('TIMER_PROBE', 30)

        elif name == 'TIMER_PROMOTION_LOCK_TIMEOUT':
            # Auto-release promotion lock after timeout
            if self.active_router_promotion:
                self.log(f"[CH] Promotion lock timeout, releasing lock")
                self.active_router_promotion = False
                # Clear any stuck yellows from set
                if hasattr(self, 'yellows_being_promoted'):
                    if len(self.yellows_being_promoted) > 0:
                        self.log(f"[CH] Clearing stuck yellows: {self.yellows_being_promoted}")
                    self.yellows_being_promoted.clear()
        
        elif name == 'TIMER_MAINTENANCE':
            if self.role == Roles.ROOT:
                self.run_network_maintenance()
        
        elif name == 'TIMER_ENERGY_SAMPLE':
            # Energy sampling (ROOT only)
            if self.role == Roles.ROOT and ENABLE_ENERGY_MODEL:
                self.sample_all_nodes_energy()
                self.set_timer('TIMER_ENERGY_SAMPLE', ENERGY_SAMPLE_INTERVAL)

        elif name == 'TIMER_HEART_BEAT':  # it sends heart beat message once heart beat timer fired
            # Log heartbeat for REGISTERED nodes to debug yellow discovery issues
            #if self.role == Roles.REGISTERED:
                #self.log(f"[HEARTBEAT] Sending periodic heartbeat (role=REGISTERED)")
            self.send_heart_beat()
            # CTM-AdHoc: Clean stale neighbors periodically
            self.clean_stale_neighbors()
            self.set_timer('TIMER_HEART_BEAT', config.HEARTH_BEAT_TIME_INTERVAL)
        
        elif name == 'TIMER_NEIGHBOR_SHARE':  # Multi-Hop: Share neighbor table periodically
            if ENABLE_MULTIHOP_NEIGHBORS and self.role in [Roles.REGISTERED, Roles.CLUSTER_HEAD, Roles.ROOT, Roles.ROUTER]:
                self.send_neighbor_table_share()
                self.set_timer('TIMER_NEIGHBOR_SHARE', NEIGHBOR_SHARE_INTERVAL)

                if len(self.neighbors_table) > 0:
                    # Find a registered neighbor to get root address
                    for gui, info in self.neighbors_table.items():
                        if info.get('role') in [Roles.REGISTERED, Roles.CLUSTER_HEAD, Roles.ROOT]:
                            # Temporarily set parent to send network request
                            self.parent_gui = gui
                            self.root_addr = info.get('root_addr')
                            if self.root_addr:
                                self.addr = wsn.Addr(gui, self.id)  # Temporary address
                                self.send_network_request()
                                self.log("[YELLOW_CH] Requested to become CH after timeout")
                                break
        
        elif name == 'TIMER_JOIN_REQUEST':  # Periodic join attempt cycle
            # Check if we have any neighbors at all
            if len(self.neighbors_table) == 0:
                # No neighbors discovered yet - send PROBE and wait
                self.log(f"[JOIN] No neighbors yet, sending PROBE")
                self.send_probe()
                self.set_timer('TIMER_JOIN_REQUEST', 15)
                return
            
            # We have neighbors - check if any are valid candidates
            if len(self.candidate_parents_table) == 0:
                # Have neighbors but none are candidates - send PROBE to refresh
                self.log(f"[JOIN] Have {len(self.neighbors_table)} neighbors but no candidates, probing")
                self.send_probe()
                self.set_timer('TIMER_JOIN_REQUEST', 15)
                return
            
            # Have candidates - try to join
            self.select_and_join()
        
    
    ###################
    def is_node_registered(self, node_id):
        """Check if a node is still REGISTERED (not promoted to router/CH)"""
        for node in sim.nodes:
            if node.id == node_id:
                return hasattr(node, 'role') and node.role == Roles.REGISTERED
        return False

    ###################
    def run_network_maintenance(self):
        """
        Network maintenance
        - Kill stuck yellow/green pairs that are in infinite retry loops
        - Demote orphaned routers that aren't bridging any CHs
        - Clean up invalid entries in tables
        """
        now = self.now
        self.log(f"\n{'='*70}")
        self.log(f"[MAINTENANCE] Starting network maintenance at {now:.1f}s")
        self.log(f"{'='*70}\n")
        
        killed_yellows = []
        killed_greens = []
        demoted_routers = []
        
        # Diagnostic: Log all registered nodes and their parents
        self.log(f"[MAINTENANCE] Diagnostic: Current registered nodes and their parents:")
        for green in [n for n in sim.nodes if hasattr(n, 'role') and n.role == Roles.REGISTERED]:
            parent_info = "None"
            if hasattr(green, 'parent_gui') and green.parent_gui is not None:
                parent = next((n for n in sim.nodes if n.id == green.parent_gui), None)
                if parent and hasattr(parent, 'role'):
                    parent_info = f"{green.parent_gui} ({parent.role.name})"
                else:
                    parent_info = f"{green.parent_gui} (NOT FOUND)"
            self.log(f"  Green {green.id}: parent_gui={parent_info}")
        self.log("")
        
        # Phase 1: Find and kill stuck yellows (any yellow stuck > 1000s)
        self.log(f"[MAINTENANCE] Phase 1: Identifying stuck yellows...")
        
        for yellow in [n for n in sim.nodes if hasattr(n, 'role') and n.role == Roles.UNREGISTERED]:
            # Check if yellow has been stuck for > 1000 seconds
            if hasattr(yellow, 'unregistered_since') and yellow.unregistered_since:
                stuck_time = now - yellow.unregistered_since
                if stuck_time > 1000:
                    # Yellow stuck for > 1000 seconds - KILL IT
                    self.log(f"[MAINTENANCE] Found stuck yellow {yellow.id} (stuck for {stuck_time:.1f}s)")
                    killed_yellows.append(yellow.id)
                    
                    # Mark node as killed
                    yellow.set_role(Roles.UNDISCOVERED)
                    
                    # Stop timers
                    yellow.kill_timer('TIMER_JOIN_REQUEST')
                    yellow.kill_timer('TIMER_YELLOW_CH')
                    yellow.kill_timer('TIMER_HEART_BEAT')
                    
                    self.log(f"[MAINTENANCE] Killed stuck yellow {yellow.id}")
        
        # Phase 1b: Find and kill greens outside network (no parent)
        self.log(f"\n[MAINTENANCE] Phase 1b: Identifying greens outside network...")
        
        for green in [n for n in sim.nodes if hasattr(n, 'role') and n.role == Roles.REGISTERED]:
            # Check if green is outside network (no parent CH)
            if hasattr(green, 'parent_gui') and green.parent_gui is None:
                self.log(f"[MAINTENANCE] Found green {green.id} outside network (no parent)")
                killed_greens.append(green.id)
                
                # Mark node as killed
                green.set_role(Roles.UNDISCOVERED)
                
                # Stop timers
                green.kill_timer('TIMER_HEART_BEAT')
                
                self.log(f"[MAINTENANCE] Killed green {green.id} (outside network)")
        
        # Phase 1c: Find and kill greens connected to routers (orphaned greens)
        self.log(f"\n[MAINTENANCE] Phase 1c: Identifying greens connected to routers...")
        
        for green in [n for n in sim.nodes if hasattr(n, 'role') and n.role == Roles.REGISTERED]:
            should_kill = False
            router_id = None
            
            # Method 1: Check if green's parent_gui is a ROUTER
            if hasattr(green, 'parent_gui') and green.parent_gui is not None:
                parent = next((n for n in sim.nodes if n.id == green.parent_gui), None)
                if parent and hasattr(parent, 'role') and parent.role == Roles.ROUTER:
                    should_kill = True
                    router_id = parent.id
                    self.log(f"[MAINTENANCE] Found green {green.id} with parent_gui={router_id} (ROUTER)")
            
            # Method 2: Check if green is in any router's members (shouldn't be)
            if not should_kill:
                for router in [n for n in sim.nodes if hasattr(n, 'role') and n.role == Roles.ROUTER]:
                    # Check if this green is connected to this router
                    if hasattr(router, 'neighbors_table') and green.id in router.neighbors_table:
                        # Check if green considers router as parent
                        if hasattr(green, 'ch_addr') and hasattr(router, 'addr'):
                            if green.ch_addr == router.addr:
                                should_kill = True
                                router_id = router.id
                                self.log(f"[MAINTENANCE] Found green {green.id} with ch_addr pointing to router {router_id}")
                                break
            
            if should_kill and green.id not in killed_greens:
                killed_greens.append(green.id)
                
                # Mark node as killed
                green.set_role(Roles.UNDISCOVERED)
                
                # Stop timers
                green.kill_timer('TIMER_HEART_BEAT')
                
                self.log(f"[MAINTENANCE] Killed green {green.id} (connected to router {router_id})")
        
        #  Find and kill greens connected to other greens (invalid green-to-green)
        self.log(f"\n[MAINTENANCE] Phase 1d: Identifying greens connected to other greens...")
        
        for green in [n for n in sim.nodes if hasattr(n, 'role') and n.role == Roles.REGISTERED]:
            # Check if green's parent is another REGISTERED node (not a CH)
            if hasattr(green, 'parent_gui') and green.parent_gui is not None:
                parent = next((n for n in sim.nodes if n.id == green.parent_gui), None)
                if parent and hasattr(parent, 'role') and parent.role == Roles.REGISTERED:
                    # Green is connected to another green - this is invalid
                    # Greens should only connect to CHs, not other greens
                    self.log(f"[MAINTENANCE] Found green {green.id} connected to green {parent.id}")
                    
                    if green.id not in killed_greens:  # Don't double-kill
                        killed_greens.append(green.id)
                        
                        # Mark node as killed
                        green.set_role(Roles.UNDISCOVERED)
                        
                        # Stop timers
                        green.kill_timer('TIMER_HEART_BEAT')
                        
                        self.log(f"[MAINTENANCE] Killed green {green.id} (connected to green)")
        
        # Phase 1e: Find and kill CHs that are members of other CHs (overlapping CHs)
        self.log(f"\n[MAINTENANCE] Phase 1e: Identifying overlapping CHs (CH inside another CH)...")
        
        killed_overlapping_chs = []
        killed_orphaned_members = []
        
        for parent_ch in [n for n in sim.nodes if hasattr(n, 'role') and n.role in [Roles.CLUSTER_HEAD, Roles.ROOT]]:
            if hasattr(parent_ch, 'members_table') and parent_ch.members_table:
                for member_id in parent_ch.members_table:
                    # Check if this member is actually a CH
                    member_node = next((n for n in sim.nodes if n.id == member_id), None)
                    if member_node and hasattr(member_node, 'role'):
                        if member_node.role == Roles.CLUSTER_HEAD:
                            # Found a CH in members_table - this is invalid!
                            # CHs should only be in child_networks_table, not members_table
                            self.log(f"[MAINTENANCE] Found overlapping CH {member_id} inside CH {parent_ch.id}'s members")
                            
                            if member_id not in killed_overlapping_chs:
                                killed_overlapping_chs.append(member_id)
                                
                                # FIRST: Kill all members of this overlapping CH
                                if hasattr(member_node, 'members_table') and member_node.members_table:
                                    self.log(f"[MAINTENANCE] Killing {len(member_node.members_table)} members of overlapping CH {member_id}")
                                    
                                    for orphaned_member_id in list(member_node.members_table):
                                        orphaned_node = next((n for n in sim.nodes if n.id == orphaned_member_id), None)
                                        if orphaned_node and hasattr(orphaned_node, 'role'):
                                            if orphaned_member_id not in killed_orphaned_members:
                                                killed_orphaned_members.append(orphaned_member_id)
                                                
                                                # Kill the orphaned member
                                                orphaned_node.set_role(Roles.UNDISCOVERED)
                                                
                                                # Clear parent connection
                                                if hasattr(orphaned_node, 'parent_gui'):
                                                    orphaned_node.parent_gui = None
                                                if hasattr(orphaned_node, 'ch_addr'):
                                                    orphaned_node.ch_addr = None
                                                
                                                # Stop timers
                                                orphaned_node.kill_timer('TIMER_HEART_BEAT')
                                                
                                                self.log(f"[MAINTENANCE] Killed orphaned member {orphaned_member_id} (was connected to overlapping CH {member_id})")
                                
                                # THEN: Kill the overlapping CH itself
                                member_node.set_role(Roles.UNDISCOVERED)
                                
                                # Clear its CH state
                                if hasattr(member_node, 'ch_addr'):
                                    member_node.ch_addr = None
                                if hasattr(member_node, 'members_table'):
                                    member_node.members_table = []
                                if hasattr(member_node, 'child_networks_table'):
                                    member_node.child_networks_table = {}
                                
                                # Stop timers
                                member_node.kill_timer('TIMER_HEART_BEAT')
                                
                                self.log(f"[MAINTENANCE] Killed overlapping CH {member_id} (will reconnect as REGISTERED)")
                                
                                # Remove from parent's members_table
                                parent_ch.members_table.remove(member_id)
        
        # Phase 2: Demote orphaned routers
        self.log(f"\n[MAINTENANCE] Phase 2: Identifying orphaned routers...")
        
        for node in sim.nodes:
            if hasattr(node, 'role') and node.role == Roles.ROUTER:
                # Check if router is actually bridging two CHs
                has_valid_child = False
                
                if hasattr(node, 'connected_CHs') and len(node.connected_CHs) > 1:
                    child_ch_id = node.connected_CHs[1]
                    
                    # Verify child is actually a CH
                    for other in sim.nodes:
                        if other.id == child_ch_id and hasattr(other, 'role'):
                            if other.role in [Roles.CLUSTER_HEAD, Roles.ROOT]:
                                has_valid_child = True
                                break
                
                if not has_valid_child:
                    # Orphaned router - demote to REGISTERED
                    self.log(f"[MAINTENANCE] Found orphaned router {node.id} (no child CH)")
                    demoted_routers.append(node.id)
                    
                    # Demote to REGISTERED
                    node.set_role(Roles.REGISTERED)
                    if hasattr(node, 'connected_CHs'):
                        node.connected_CHs = []
                    
                    # Stop router heartbeat timer
                    node.kill_timer('TIMER_ROUTER_HB')
                    
                    # Start regular heartbeat
                    node.set_timer('TIMER_HEART_BEAT', config.HEARTH_BEAT_TIME_INTERVAL)
                    
                    self.log(f"[MAINTENANCE] Demoted orphaned router {node.id} to REGISTERED")
        
        # Phase 3: Clean up members_table entries for killed nodes
        self.log(f"\n[MAINTENANCE] Phase 3: Cleaning up tables...")
        
        all_killed = killed_yellows + killed_greens + killed_overlapping_chs + killed_orphaned_members
        for node in sim.nodes:
            if hasattr(node, 'role') and node.role in [Roles.CLUSTER_HEAD, Roles.ROOT]:
                if hasattr(node, 'members_table'):
                    original_count = len(node.members_table)
                    node.members_table = [m for m in node.members_table if m not in all_killed]
                    removed = original_count - len(node.members_table)
                    if removed > 0:
                        self.log(f"[MAINTENANCE] Removed {removed} killed nodes from CH {node.id} members_table")
        
        # Summary
        self.log(f"\n{'='*70}")
        self.log(f"[MAINTENANCE] Summary:")
        self.log(f"  - Killed yellows: {len(killed_yellows)} nodes {killed_yellows}")
        self.log(f"  - Killed greens: {len(killed_greens)} nodes {killed_greens}")
        self.log(f"  - Killed overlapping CHs: {len(killed_overlapping_chs)} nodes {killed_overlapping_chs}")
        self.log(f"  - Killed orphaned members: {len(killed_orphaned_members)} nodes {killed_orphaned_members}")
        self.log(f"  - Demoted routers: {len(demoted_routers)} nodes {demoted_routers}")
        self.log(f"  - Total nodes cleaned: {len(all_killed) + len(demoted_routers)}")
        self.log(f"{'='*70}\n")

    ###################
    def sample_all_nodes_energy(self):
        """Sample energy state of all nodes for CSV export (ROOT only)"""
        if not ENABLE_ENERGY_MODEL:
            return
        
        for node in sim.nodes:
            if hasattr(node, 'remaining_energy'):
                # Update idle energy before sampling
                node.update_idle_energy()
                
                sample = {
                    'timestamp': self.now,
                    'node_id': node.id,
                    'role': node.role.name if hasattr(node, 'role') else 'UNKNOWN',
                    'remaining_energy': node.remaining_energy,
                    'energy_consumed': node.initial_energy - node.remaining_energy,
                    'energy_tx': node.energy_tx,
                    'energy_rx': node.energy_rx,
                    'energy_idle': node.energy_idle,
                    'energy_sleep': node.energy_sleep,
                    'is_alive': node.is_alive,
                    'packets_sent': node.packets_sent,
                    'packets_received': node.packets_received,
                    'packets_lost': node.packets_lost,
                    'bytes_sent': node.bytes_sent,
                    'bytes_received': node.bytes_received
                }
                ENERGY_SAMPLES.append(sample)

    ###################
    def finish(self):
        """Called at end of simulation - print CTM-AdHoc routing statistics"""
        if ENABLE_HYBRID_ROUTING and sum(self.routing_stats.values()) > 0:
            stats_msg = (f"[CTM-AdHoc Stats] Direct:{self.routing_stats['direct_mesh']} "
                        f"IntraCluster:{self.routing_stats['intra_cluster']} "
                        f"Downward:{self.routing_stats['downward_tree']} "
                        f"Upward:{self.routing_stats['upward_tree']} ")
            
            if ENABLE_MULTIHOP_NEIGHBORS:
                stats_msg += f"MultiHop:{self.routing_stats['multihop_routes']} "
            
            stats_msg += f"Failures:{self.routing_stats['route_failures']}"
            self.log(stats_msg)
        
        # Multi-Hop: Log neighbor discovery stats
        if ENABLE_MULTIHOP_NEIGHBORS:
            direct_neighbors = len(self.neighbors_table)
            multihop_neighbors = len(self.multihop_neighbors)
            if direct_neighbors > 0 or multihop_neighbors > 0:
                self.log(f"[Neighbor Discovery] 1-hop:{direct_neighbors} Multi-hop:{multihop_neighbors}")


ROOT_ID = random.randrange(config.SIM_NODE_COUNT)  # 0..count-1


def write_child_networks_table_csv(path="child_networks_table.csv"):
    """Write hierarchical tree structure showing parent-child CH relationships"""
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["node_id", "node_role", "child_count", "children"])
        
        for node in sim.nodes:
            if hasattr(node, "role") and node.role in [Roles.ROOT, Roles.CLUSTER_HEAD]:
                if hasattr(node, "child_networks_table") and node.child_networks_table:
                    # Format children with their networks
                    children_list = []
                    for child_gui, child_networks in node.child_networks_table.items():
                        # Get child node to determine role
                        child_role = "UNKNOWN"
                        for n in sim.nodes:
                            if n.id == child_gui and hasattr(n, 'role'):
                                child_role = n.role.name
                                break
                        # Format: "child_id(role)[net1,net2,...]"
                        networks_str = ",".join(str(net) for net in child_networks)
                        children_list.append(f"{child_gui}({child_role})[{networks_str}]")
                    
                    children_str = ";".join(children_list)
                    child_count = len(node.child_networks_table)
                    w.writerow([node.id, node.role.name, child_count, children_str])


def write_members_table_csv(path="members_table.csv"):
    """Write cluster membership showing which nodes belong to each CH"""
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["node_id", "node_role", "member_count", "members"])
        
        for node in sim.nodes:
            if hasattr(node, "role") and node.role in [Roles.ROOT, Roles.CLUSTER_HEAD]:
                if hasattr(node, "members_table") and node.members_table:  # Check if not empty
                    # Format members
                    members_list = []
                    for member_gui in node.members_table:
                        # Get member node to determine role
                        member_role = "UNKNOWN"
                        for n in sim.nodes:
                            if n.id == member_gui and hasattr(n, 'role'):
                                member_role = n.role.name
                                break
                        members_list.append(f"{member_gui}({member_role})")
                    
                    members_str = ";".join(members_list)
                    member_count = len(node.members_table)
                    w.writerow([node.id, node.role.name, member_count, members_str])


def write_neighbors_table_csv(path="neighbors_table.csv"):
    """Write direct 1-hop neighbors for each node"""
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["node_id", "node_role", "neighbor_count", "neighbors"])
        
        for node in sim.nodes:
            if hasattr(node, "neighbors_table") and node.neighbors_table:
                # Format neighbors with role, hop count, and distance
                neighbors_list = []
                for neighbor_gui, neighbor_info in node.neighbors_table.items():
                    role = neighbor_info.get('role')
                    role_name = role.name if hasattr(role, 'name') else str(role)
                    hop_count = neighbor_info.get('hop_count', '?')
                    distance = neighbor_info.get('distance', 0)
                    neighbors_list.append(f"{neighbor_gui}({role_name},{hop_count},{distance:.1f})")
                
                neighbors_str = ";".join(neighbors_list)
                neighbor_count = len(node.neighbors_table)
                role_name = node.role.name if hasattr(node, "role") else "UNKNOWN"
                w.writerow([node.id, role_name, neighbor_count, neighbors_str])


def write_energy_timeline_csv(path="energy_timeline.csv"):
    """Export energy timeline data for plotting"""
    if not ENABLE_ENERGY_MODEL or not ENERGY_SAMPLES:
        return
    
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "timestamp", "node_id", "role", "remaining_energy", "energy_consumed",
            "energy_tx", "energy_rx", "energy_idle", "energy_sleep",
            "is_alive", "packets_sent", "packets_received", "packets_lost",
            "bytes_sent", "bytes_received"
        ])
        
        for sample in ENERGY_SAMPLES:
            w.writerow([
                sample['timestamp'],
                sample['node_id'],
                sample['role'],
                sample['remaining_energy'],
                sample['energy_consumed'],
                sample['energy_tx'],
                sample['energy_rx'],
                sample['energy_idle'],
                sample['energy_sleep'],
                sample['is_alive'],
                sample['packets_sent'],
                sample['packets_received'],
                sample['packets_lost'],
                sample['bytes_sent'],
                sample['bytes_received']
            ])


def write_energy_summary_csv(path="energy_summary.csv"):
    """Export per-node energy summary at end of simulation"""
    if not ENABLE_ENERGY_MODEL:
        return
    
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "node_id", "final_role", "initial_energy", "remaining_energy",
            "total_consumed", "energy_tx", "energy_rx", "energy_idle", "energy_sleep",
            "time_tx", "time_rx", "time_idle", "time_sleep",
            "packets_sent", "packets_received", "packets_lost",
            "bytes_sent", "bytes_received", "is_alive", "death_time"
        ])
        
        for node in sim.nodes:
            if hasattr(node, 'remaining_energy'):
                # Update final idle energy
                node.update_idle_energy()
                
                death_time = ''
                if hasattr(node, 'is_alive') and not node.is_alive:
                    death_time = node.now
                
                w.writerow([
                    node.id,
                    node.role.name if hasattr(node, 'role') else 'UNKNOWN',
                    node.initial_energy,
                    node.remaining_energy,
                    node.initial_energy - node.remaining_energy,
                    node.energy_tx,
                    node.energy_rx,
                    node.energy_idle,
                    node.energy_sleep,
                    node.time_in_tx,
                    node.time_in_rx,
                    node.time_in_idle,
                    node.time_in_sleep,
                    node.packets_sent,
                    node.packets_received,
                    node.packets_lost,
                    node.bytes_sent,
                    node.bytes_received,
                    node.is_alive,
                    death_time
                ])


###########################################################
def create_network(node_class, number_of_nodes=100):
    """Creates given number of nodes at random positions with random arrival times.

    Args:
        node_class (Class): Node class to be created.
        number_of_nodes (int): Number of nodes.
    Returns:

    """
    edge = math.ceil(math.sqrt(number_of_nodes))
    startup_delay = getattr(config, 'NODE_STARTUP_DELAY', 5)
    
    for i in range(number_of_nodes):
        x = i / edge
        y = i % edge
        px = 300 + config.SCALE*x * config.SIM_NODE_PLACING_CELL_SIZE + random.uniform(-1 * config.SIM_NODE_PLACING_CELL_SIZE / 3, config.SIM_NODE_PLACING_CELL_SIZE / 3)
        py = 200 + config.SCALE* y * config.SIM_NODE_PLACING_CELL_SIZE + random.uniform(-1 * config.SIM_NODE_PLACING_CELL_SIZE / 3, config.SIM_NODE_PLACING_CELL_SIZE / 3)
        node = sim.add_node(node_class, (px, py))
        NODE_POS[node.id] = (px, py)
        node.tx_range = config.NODE_TX_RANGE * config.SCALE
        node.logging = True
        # All nodes appear immediately (white), then wake up together after startup_delay
        node.arrival = startup_delay + random.uniform(0, 2)  # Small variance to prevent exact simultaneity
        if node.id == ROOT_ID:
            node.arrival = startup_delay  # Root starts first


sim = wsn.Simulator(
    duration=config.SIM_DURATION,
    timescale=config.SIM_TIME_SCALE,
    visual=config.SIM_VISUALIZATION,
    terrain_size=config.SIM_TERRAIN_SIZE,
    title=config.SIM_TITLE)

# creating random network
create_network(SensorNode, config.SIM_NODE_COUNT)

# Function to export 3 essential CSV tables (called on exit or Ctrl+C)
# Global flag to prevent duplicate exports
_stats_exported = False

def export_final_stats():
    """Export 3 essential network structure tables (only once)"""
    global _stats_exported
    
    # Prevent duplicate exports
    if _stats_exported:
        return
    
    _stats_exported = True
    
    try:
        print("\nExporting network structure...")
        write_child_networks_table_csv("child_networks_table.csv")
        write_members_table_csv("members_table.csv")
        write_neighbors_table_csv("neighbors_table.csv")
        print("Exported: child_networks_table.csv")
        print("Exported: members_table.csv")
        print("Exported: neighbors_table.csv")
        
        # Export energy data if enabled
        if ENABLE_ENERGY_MODEL:
            write_energy_timeline_csv("energy_timeline.csv")
            write_energy_summary_csv("energy_summary.csv")
            print("Exported: energy_timeline.csv")
            print("Exported: energy_summary.csv")
            
            # Print energy statistics
            alive_nodes = sum(1 for node in sim.nodes if hasattr(node, 'is_alive') and node.is_alive)
            total_nodes = len(sim.nodes)
            print(f"\nEnergy Statistics:")
            print(f"  Alive nodes: {alive_nodes}/{total_nodes} ({alive_nodes/total_nodes*100:.1f}%)")
            print(f"  Energy samples collected: {len(ENERGY_SAMPLES)}")
        
    except Exception as e:
        print(f"Error exporting tables: {e}")

# Register cleanup handlers
atexit.register(export_final_stats)

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\n\nSimulation stopped by user (Ctrl+C)")
    export_final_stats()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# Setup logging to file
import sys
class TeeLogger:
    """Write to both stdout and file"""
    def __init__(self, filename, mode='w'):
        self.terminal = sys.stdout
        self.log = open(filename, mode)
    
    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()  # Ensure immediate write
    
    def flush(self):
        self.terminal.flush()
        self.log.flush()
    
    def close(self):
        if self.log:
            self.log.close()

# Save original stdout
original_stdout = sys.stdout
original_stderr = sys.stderr

# Redirect stdout to both terminal and file (overwrite mode)
tee_logger = TeeLogger('simulation_log.txt', 'w')
sys.stdout = tee_logger
sys.stderr = tee_logger

# start the simulation
try:
    print("=" * 80)
    print("SIMULATION LOG")
    print(f"Duration: {config.SIM_DURATION}s, Nodes: {config.SIM_NODE_COUNT}")
    print(f"Log file: simulation_log.txt")
    print("=" * 80)
    sim.run()
    print("\nSimulation completed!")
    import time
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    export_final_stats()
    print("\nSimulation stopped by user (Ctrl+C)")
except Exception as e:
    print(f"\nSimulation error: {e}")
    import traceback
    traceback.print_exc()
finally:
    # Restore original stdout/stderr and close log
    sys.stdout = original_stdout
    sys.stderr = original_stderr
    tee_logger.close()
    print("Log saved to simulation_log.txt")
