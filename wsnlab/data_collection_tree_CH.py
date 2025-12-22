import random
from enum import Enum
import sys
sys.path.insert(1, '.')
from source import wsnlab_vis as wsn
import math
from source import config
from collections import Counter


import csv  # <— add this near your other imports

# Track where each node is placed
NODE_POS = {}  # {node_id: (x, y)}

# --- tracking containers ---
ALL_NODES = []              # node objects
CLUSTER_HEADS = []
ROLE_COUNTS = Counter()     # live tally per Roles enum

# Energy tracking (global list for CSV export)
ENERGY_SAMPLES = []  # Stores energy samples over time

def _addr_str(a): return "" if a is None else str(a)
def _role_name(r): return r.name if hasattr(r, "name") else str(r)


Roles = Enum('Roles', 'UNDISCOVERED UNREGISTERED ROOT REGISTERED CLUSTER_HEAD')
"""Enumeration of roles"""

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
    It will run data collection tree construction algorithms.

    Attributes:
        role (Roles): role of node
        is_root_eligible (bool): keeps eligibility to be root
        c_probe (int): probe message counter
        th_probe (int): probe message threshold
        neighbors_table (Dict): keeps the neighbor information with received heart beat messages
    """

    ###################
    def init(self):
        """Initialization of node. Setting all attributes of node.
        At the beginning node needs to be sleeping and its role should be UNDISCOVERED.

        Args:

        Returns:

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
        self.candidate_parents_table = []
        self.child_networks_table = {}
        self.members_table = []
        self.received_JR_guis = []  # keeps received Join Request global unique ids
        
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
            self.last_energy_update = 0.0
            
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
        
        # Join time tracking
        self.wakeup_time = None      # When node became UNREGISTERED
        self.join_time = None         # When node joined network (REGISTERED/CH)
        self.join_duration = None     # Time to join (join_time - wakeup_time)

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
        
        # Track wakeup time (when node becomes UNREGISTERED)
        if new_role == Roles.UNREGISTERED and self.wakeup_time is None:
            self.wakeup_time = self.now
        
        # Track join time (when node joins network)
        if new_role in [Roles.REGISTERED, Roles.CLUSTER_HEAD]:
            if self.join_time is None and self.wakeup_time is not None:
                self.join_time = self.now
                self.join_duration = self.join_time - self.wakeup_time

        if recolor:
            if new_role == Roles.UNDISCOVERED:
                self.scene.nodecolor(self.id, 1, 1, 1)
            elif new_role == Roles.UNREGISTERED:
                self.scene.nodecolor(self.id, 1, 1, 0)
            elif new_role == Roles.REGISTERED:
                self.scene.nodecolor(self.id, 0, 1, 0)
            elif new_role == Roles.CLUSTER_HEAD:
                self.scene.nodecolor(self.id, 0, 0, 1)
                self.draw_tx_range()
            elif new_role == Roles.ROOT:
                self.scene.nodecolor(self.id, 0, 0, 0)
                self.set_timer('TIMER_EXPORT_CH_CSV', config.EXPORT_CH_CSV_INTERVAL)
                self.set_timer('TIMER_EXPORT_NEIGHBOR_CSV', config.EXPORT_NEIGHBOR_CSV_INTERVAL)
                if ENABLE_ENERGY_MODEL:
                    self.set_timer('TIMER_ENERGY_SAMPLE', ENERGY_SAMPLE_INTERVAL)




    ###################
    # Energy Model Methods
    ###################
    
    def calculate_packet_size(self, packet):
        """Calculate packet size in bytes for energy consumption"""
        if not ENABLE_ENERGY_MODEL:
            return 0
        
        # Base packet overhead
        size = 50  # bytes (headers, etc.)
        
        # Add payload based on packet type
        if isinstance(packet, dict):
            pck_type = packet.get('type', '')
            if pck_type in ['PROBE', 'HEART_BEAT']:
                size += 20
            elif pck_type in ['JOIN_REQUEST', 'JOIN_REPLY', 'JOIN_ACK']:
                size += 30
            elif pck_type in ['NETWORK_REQUEST', 'NETWORK_REPLY']:
                size += 40
            elif pck_type == 'DATA':
                size += packet.get('size', 100)
            else:
                size += 25
        
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
        
        # Check if node died
        if self.remaining_energy <= 0:
            self.remaining_energy = 0
            self.die_from_energy_depletion()
    
    def die_from_energy_depletion(self):
        """Handle node death from energy depletion"""
        if not hasattr(self, 'is_alive') or not self.is_alive:
            return
        
        self.is_alive = False
        self.log(f"[ENERGY] Node {self.id} DIED - Energy depleted!")
        
        # Become undiscovered
        self.set_role(Roles.UNDISCOVERED)
        self.kill_all_timers()
    
    def update_idle_energy(self):
        """Update idle/sleep energy consumption based on time elapsed"""
        if not ENABLE_ENERGY_MODEL or not hasattr(self, 'is_alive') or not self.is_alive:
            return
        
        if not hasattr(self, 'last_energy_update') or self.last_energy_update == 0:
            self.last_energy_update = self.now
            return
        
        time_elapsed = self.now - self.last_energy_update
        self.last_energy_update = self.now
        
        if time_elapsed <= 0:
            return
        
        # Calculate energy based on current role
        if self.role == Roles.UNDISCOVERED:
            # Sleeping
            energy = time_elapsed * SLEEP_ENERGY_PER_SECOND
            self.consume_energy(energy, 'SLEEP')
            self.time_in_sleep += time_elapsed
        else:
            # Idle (listening)
            energy = time_elapsed * IDLE_ENERGY_PER_SECOND
            self.consume_energy(energy, 'IDLE')
            self.time_in_idle += time_elapsed

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

    
    def become_unregistered(self):
        if self.role != Roles.UNDISCOVERED:
            self.kill_all_timers()
            self.log('I became UNREGISTERED')
        self.scene.nodecolor(self.id, 1, 1, 0)
        self.erase_parent()
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
        self.send_probe()
        self.set_timer('TIMER_JOIN_REQUEST', 20)

    ###################
    def update_neighbor(self, pck):
        pck['arrival_time'] = self.now
        # compute Euclidean distance between self and neighbor
        if pck['gui'] in NODE_POS and self.id in NODE_POS:
            x1, y1 = NODE_POS[self.id]
            x2, y2 = NODE_POS[pck['gui']]
            pck['distance'] = math.hypot(x1 - x2, y1 - y2)
        self.neighbors_table[pck['gui']] = pck

        if pck['gui'] not in self.child_networks_table.keys() or pck['gui'] not in self.members_table:
            if pck['gui'] not in self.candidate_parents_table:
                self.candidate_parents_table.append(pck['gui'])

    ###################
    def select_and_join(self):
        min_hop = 99999
        min_hop_gui = 99999
        for gui in self.candidate_parents_table:
            if self.neighbors_table[gui]['hop_count'] < min_hop or (self.neighbors_table[gui]['hop_count'] == min_hop and gui < min_hop_gui):
                min_hop = self.neighbors_table[gui]['hop_count']
                min_hop_gui = gui
        selected_addr = self.neighbors_table[min_hop_gui]['source']
        self.send_join_request(selected_addr)
        self.set_timer('TIMER_JOIN_REQUEST', 5)


    ###################
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
        self.send({'dest': wsn.BROADCAST_ADDR,
                   'type': 'HEART_BEAT',
                   'source': self.ch_addr if self.ch_addr is not None else self.addr,
                   'gui': self.id,
                   'role': self.role,
                   'addr': self.addr,
                   'ch_addr': self.ch_addr,
                   'hop_count': self.hop_count})

    ###################
    def send_join_request(self, dest):
        """Sending join request message to given destination address to join destination network

        Args:
            dest (Addr): Address of destination node
        Returns:

        """
        self.send({'dest': dest, 'type': 'JOIN_REQUEST', 'gui': self.id})

    ###################
    def send_join_reply(self, gui, addr):
        """Sending join reply message to register the node requested to join.
        The message includes a gui to determine which node will take this reply, an addr to be assigned to the node
        and a root_addr.

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
        """Routing and forwarding given package

        Args:
            pck (Dict): package to route and forward it should contain dest, source and type.
        Returns:

        """
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
        child_networks = [self.ch_addr.net_addr]
        for networks in self.child_networks_table.values():
            child_networks.extend(networks)

        self.send({'dest': self.neighbors_table[self.parent_gui]['ch_addr'], 'type': 'NETWORK_UPDATE', 'source': self.addr,
                   'gui': self.id, 'child_networks': child_networks})

    ###################
    def on_receive(self, pck):
        """Executes when a package received.

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
        
        if self.role == Roles.ROOT or self.role == Roles.CLUSTER_HEAD:  # if the node is root or cluster head
            if 'next_hop' in pck.keys() and pck['dest'] != self.addr and pck['dest'] != self.ch_addr:  # forwards message if destination is not itself
                self.route_and_forward_package(pck)
                return
            if pck['type'] == 'HEART_BEAT':
                self.update_neighbor(pck)
            if pck['type'] == 'PROBE':  # it waits and sends heart beat message once received probe message
                # yield self.timeout(.5)
                self.send_heart_beat()
            if pck['type'] == 'JOIN_REQUEST':  # it waits and sends join reply message once received join request
                # yield self.timeout(.5)
                self.send_join_reply(pck['gui'], wsn.Addr(self.ch_addr.net_addr, pck['gui']))
            if pck['type'] == 'NETWORK_REQUEST':  # it sends a network reply to requested node
                # yield self.timeout(.5)
                if self.role == Roles.ROOT:
                    new_addr = wsn.Addr(pck['source'].node_addr,254)
                    self.send_network_reply(pck['source'],new_addr)
            if pck['type'] == 'JOIN_ACK':
                self.members_table.append(pck['gui'])
            if pck['type'] == 'NETWORK_UPDATE':
                self.child_networks_table[pck['gui']] = pck['child_networks']
                if self.role != Roles.ROOT:
                    self.send_network_update()
            if pck['type'] == 'SENSOR':
                pass
                # self.log(str(pck['source'])+'--'+str(pck['sensor_value']))

        elif self.role == Roles.REGISTERED:  # if the node is registered
            if pck['type'] == 'HEART_BEAT':
                self.update_neighbor(pck)
            if pck['type'] == 'PROBE':
                # yield self.timeout(.5)
                self.send_heart_beat()
            if pck['type'] == 'JOIN_REQUEST':  # it sends a network request to the root
                self.received_JR_guis.append(pck['gui'])
                # yield self.timeout(.5)
                self.send_network_request()
            if pck['type'] == 'NETWORK_REPLY':  # it becomes cluster head and send join reply to the candidates
                self.set_role(Roles.CLUSTER_HEAD)
                try:
                    write_clusterhead_distances_csv("clusterhead_distances.csv")
                except Exception as e:
                    self.log(f"CH CSV export error: {e}")
                self.scene.nodecolor(self.id, 0, 0, 1)
                self.ch_addr = pck['addr']
                self.send_network_update()
                # yield self.timeout(.5)
                self.send_heart_beat()
                for gui in self.received_JR_guis:
                    # yield self.timeout(random.uniform(.1,.5))
                    self.send_join_reply(gui, wsn.Addr(self.ch_addr.net_addr,gui))

        elif self.role == Roles.UNDISCOVERED:  # if the node is undiscovered
            if pck['type'] == 'HEART_BEAT':  # it kills probe timer, becomes unregistered and sets join request timer once received heart beat
                self.update_neighbor(pck)
                self.kill_timer('TIMER_PROBE')
                self.become_unregistered()

        if self.role == Roles.UNREGISTERED:  # if the node is unregistered
            if pck['type'] == 'HEART_BEAT':
                self.update_neighbor(pck)
            if pck['type'] == 'JOIN_REPLY':  # it becomes registered and sends join ack if the message is sent to itself once received join reply
                if pck['dest_gui'] == self.id:
                    self.addr = pck['addr']
                    self.parent_gui = pck['gui']
                    self.root_addr = pck['root_addr']
                    self.hop_count = pck['hop_count']
                    self.draw_parent()
                    self.kill_timer('TIMER_JOIN_REQUEST')
                    self.send_heart_beat()
                    self.set_timer('TIMER_HEART_BEAT', config.HEARTH_BEAT_TIME_INTERVAL)
                    self.send_join_ack(pck['source'])
                    if self.ch_addr is not None: # it could be a cluster head which lost its parent
                        self.set_role(Roles.CLUSTER_HEAD)
                        self.send_network_update()
                    else:
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
                    self.set_timer('TIMER_HEART_BEAT', config.HEARTH_BEAT_TIME_INTERVAL)
                else:  # otherwise it keeps trying to sending probe after a long time
                    self.c_probe = 0
                    self.set_timer('TIMER_PROBE', 30)

        elif name == 'TIMER_HEART_BEAT':  # it sends heart beat message once heart beat timer fired
            self.send_heart_beat()
            self.set_timer('TIMER_HEART_BEAT', config.HEARTH_BEAT_TIME_INTERVAL)
            #print(self.id)

        elif name == 'TIMER_JOIN_REQUEST':  # if it has not received heart beat messages before, it sets timer again and wait heart beat messages once join request timer fired.
            if len(self.candidate_parents_table) == 0:
                self.become_unregistered()
            else:  # otherwise it chose one of them and sends join request
                self.select_and_join()

        elif name == 'TIMER_SENSOR':
            self.route_and_forward_package({'dest': self.root_addr, 'type': 'SENSOR', 'source': self.addr, 'sensor_value': random.uniform(10,50)})
            timer_duration =  self.id % 20
            if timer_duration == 0: timer_duration = 1
            self.set_timer('TIMER_SENSOR', timer_duration)
        elif name == 'TIMER_EXPORT_CH_CSV':
            # Only root should drive exports (cheap guard)
            if self.role == Roles.ROOT:
                write_clusterhead_distances_csv("clusterhead_distances.csv")
                # reschedule
                self.set_timer('TIMER_EXPORT_CH_CSV', config.EXPORT_CH_CSV_INTERVAL)
        elif name == 'TIMER_EXPORT_NEIGHBOR_CSV':
            if self.role == Roles.ROOT:
                write_neighbor_distances_csv("neighbor_distances.csv")
                self.set_timer('TIMER_EXPORT_NEIGHBOR_CSV', config.EXPORT_NEIGHBOR_CSV_INTERVAL)
        elif name == 'TIMER_ENERGY_SAMPLE':
            # Energy sampling (ROOT only)
            if self.role == Roles.ROOT and ENABLE_ENERGY_MODEL:
                self.sample_all_nodes_energy()
                self.set_timer('TIMER_ENERGY_SAMPLE', ENERGY_SAMPLE_INTERVAL)
    
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



ROOT_ID = random.randrange(config.SIM_NODE_COUNT)  # 0..count-1



def write_node_distances_csv(path="node_distances.csv"):
    """Write pairwise node-to-node Euclidean distances as an edge list."""
    ids = sorted(NODE_POS.keys())
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["source_id", "target_id", "distance"])
        for i, sid in enumerate(ids):
            x1, y1 = NODE_POS[sid]
            for tid in ids[i+1:]:  # i+1 to avoid duplicates and self-pairs
                x2, y2 = NODE_POS[tid]
                dist = math.hypot(x1 - x2, y1 - y2)
                w.writerow([sid, tid, f"{dist:.6f}"])


def write_node_distance_matrix_csv(path="node_distance_matrix.csv"):
    ids = sorted(NODE_POS.keys())
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["node_id"] + ids)
        for sid in ids:
            x1, y1 = NODE_POS[sid]
            row = [sid]
            for tid in ids:
                x2, y2 = NODE_POS[tid]
                dist = math.hypot(x1 - x2, y1 - y2)
                row.append(f"{dist:.6f}")
            w.writerow(row)


def write_clusterhead_distances_csv(path="clusterhead_distances.csv"):
    """Write pairwise distances between current cluster heads."""
    clusterheads = []
    for node in sim.nodes:
        # Only collect nodes that are cluster heads and have recorded positions
        if hasattr(node, "role") and node.role == Roles.CLUSTER_HEAD and node.id in NODE_POS:
            x, y = NODE_POS[node.id]
            clusterheads.append((node.id, x, y))

    if len(clusterheads) < 2:
        # Still write the header so the file exists/is refreshed
        with open(path, "w", newline="") as f:
            csv.writer(f).writerow(["clusterhead_1", "clusterhead_2", "distance"])
        return

    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["clusterhead_1", "clusterhead_2", "distance"])
        for i, (id1, x1, y1) in enumerate(clusterheads):
            for id2, x2, y2 in clusterheads[i+1:]:
                dist = math.hypot(x1 - x2, y1 - y2)
                w.writerow([id1, id2, f"{dist:.6f}"])



def write_neighbor_distances_csv(path="neighbor_distances.csv", dedupe_undirected=True):
    """
    Export neighbor distances per node.
    Each row is (node -> neighbor) with distance from NODE_POS.

    Args:
        path (str): output CSV path
        dedupe_undirected (bool): if True, writes each unordered pair once
                                  (min(node_id,neighbor_id), max(...)).
                                  If False, writes one row per direction.
    """
    # Safety: ensure we can compute distances
    if not globals().get("NODE_POS"):
        raise RuntimeError("NODE_POS is missing; record positions during create_network().")

    # Prepare a set to avoid duplicates if dedupe_undirected=True
    seen_pairs = set()

    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["node_id", "neighbor_id", "distance",
                    "neighbor_role", "neighbor_hop_count", "arrival_time"])

        for node in sim.nodes:
            # Skip nodes without any neighbor info yet
            if not hasattr(node, "neighbors_table"):
                continue

            x1, y1 = NODE_POS.get(node.id, (None, None))
            if x1 is None:
                continue  # no position → cannot compute distance

            # neighbors_table: key = neighbor GUI, value = heartbeat packet dict
            for n_gui, pck in getattr(node, "neighbors_table", {}).items():
                # Optional dedupe (unordered)
                if dedupe_undirected:
                    key = (min(node.id, n_gui), max(node.id, n_gui))
                    if key in seen_pairs:
                        continue
                    seen_pairs.add(key)

                # Position of neighbor
                x2, y2 = NODE_POS.get(n_gui, (None, None))
                if x2 is None:
                    continue

                # Distance (prefer pck['distance'] if you added it in update_neighbor)
                dist = pck.get("distance")
                if dist is None:
                    dist = math.hypot(x1 - x2, y1 - y2)

                # Extra fields (best-effort; may be missing)
                n_role = getattr(pck.get("role", None), "name", pck.get("role", None))
                hop = pck.get("hop_count", "")
                at  = pck.get("arrival_time", "")

                w.writerow([node.id, n_gui, f"{dist:.6f}", n_role, hop, at])

###########################################################
def write_energy_timeline_csv(path="energy_timeline_CH.csv"):
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


def write_energy_summary_csv(path="energy_summary_CH.csv"):
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


def write_join_times_csv(path="join_times_CH.csv"):
    """Export join time data for each node"""
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["node_id", "wakeup_time", "join_time", "join_duration", "final_role", "network_size"])
        
        network_size = len(sim.nodes)
        
        for node in sim.nodes:
            if hasattr(node, 'wakeup_time'):
                # Include all nodes, even if they didn't join
                wakeup = node.wakeup_time if node.wakeup_time is not None else ''
                join = node.join_time if node.join_time is not None else ''
                duration = node.join_duration if node.join_duration is not None else ''
                role = node.role.name if hasattr(node, 'role') else 'UNKNOWN'
                
                w.writerow([
                    node.id,
                    wakeup,
                    join,
                    duration,
                    role,
                    network_size
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
    for i in range(number_of_nodes):
        x = i / edge
        y = i % edge
        px = 300 + config.SCALE*x * config.SIM_NODE_PLACING_CELL_SIZE + random.uniform(-1 * config.SIM_NODE_PLACING_CELL_SIZE / 3, config.SIM_NODE_PLACING_CELL_SIZE / 3)
        py = 200 + config.SCALE* y * config.SIM_NODE_PLACING_CELL_SIZE + random.uniform(-1 * config.SIM_NODE_PLACING_CELL_SIZE / 3, config.SIM_NODE_PLACING_CELL_SIZE / 3)
        node = sim.add_node(node_class, (px, py))
        NODE_POS[node.id] = (px, py)   # <— add this line
        node.tx_range = config.NODE_TX_RANGE * config.SCALE
        node.logging = True
        node.arrival = random.uniform(0, config.NODE_ARRIVAL_MAX)
        if node.id == ROOT_ID:
            node.arrival = 0.1


sim = wsn.Simulator(
    duration=config.SIM_DURATION,
    timescale=config.SIM_TIME_SCALE,
    visual=config.SIM_VISUALIZATION,
    terrain_size=config.SIM_TERRAIN_SIZE,
    title=config.SIM_TITLE)

# creating random network
create_network(SensorNode, config.SIM_NODE_COUNT)

write_node_distances_csv("node_distances.csv")
write_node_distance_matrix_csv("node_distance_matrix.csv")

# start the simulation
sim.run()
print("Simulation Finished")

# Export join times
write_join_times_csv("join_times_CH.csv")
print("Exported: join_times_CH.csv")

# Calculate and print join time statistics
join_times = [node.join_duration for node in sim.nodes 
             if hasattr(node, 'join_duration') and node.join_duration is not None]
if join_times:
    avg_join_time = sum(join_times) / len(join_times)
    min_join_time = min(join_times)
    max_join_time = max(join_times)
    print(f"\nJoin Time Statistics:")
    print(f"  Nodes joined: {len(join_times)}/{len(sim.nodes)}")
    print(f"  Average join time: {avg_join_time:.2f}s")
    print(f"  Min join time: {min_join_time:.2f}s")
    print(f"  Max join time: {max_join_time:.2f}s")

# Export energy data if enabled
if ENABLE_ENERGY_MODEL:
    write_energy_timeline_csv("energy_timeline_CH.csv")
    write_energy_summary_csv("energy_summary_CH.csv")
    print("Exported: energy_timeline_CH.csv")
    print("Exported: energy_summary_CH.csv")
    
    # Print energy statistics
    alive_nodes = sum(1 for node in sim.nodes if hasattr(node, 'is_alive') and node.is_alive)
    total_nodes = len(sim.nodes)
    print(f"\nEnergy Statistics:")
    print(f"  Alive nodes: {alive_nodes}/{total_nodes} ({alive_nodes/total_nodes*100:.1f}%)")
    print(f"  Energy samples collected: {len(ENERGY_SAMPLES)}")


# Created 100 nodes at random locations with random arrival times.
# When nodes are created they appear in white
# Activated nodes becomes red
# Discovered nodes will be yellow
# Registered nodes will be green.
# Root node will be black.
# Routers/Cluster Heads should be blue
