import random
from enum import Enum
import sys
# insert at 1, 0 is the script path (or '' in REPL)
sys.path.insert(1, '..\source')
from source import wsnlab_vis as wsn
import math

Roles = Enum('Roles', 'UNDISCOVERED UNREGISTERED ROOT REGISTERED')

###########################################################
class SensorNode(wsn.Node):

    ###################
    def init(self):
        self.scene.nodecolor(self.id, 1, 1, 1) # sets self color to white
        self.sleep()
        self.addr = None
        self.role = Roles.UNDISCOVERED
        self.is_root_eligible = True if self.id == 0 else False
        self.c_probe = 0  # c means counter and probe is the name of counter
        self.th_probe = 10  # th means threshold and probe is the name of threshold
        self.received_HB_addresses = []  # keeps received HB message addresses

    ###################
    def run(self):
        self.set_timer('TIMER_ARRIVAL', self.arrival)

    ###################
    def send_probe(self):
        self.send({'dest': wsn.BROADCAST_ADDR, 'type': 'PROBE'})

    ###################
    def send_hearth_beat(self):
        self.send({'dest': wsn.BROADCAST_ADDR, 'type': 'HEARTH_BEAT', 'source': self.addr})

    ###################
    def send_join_request(self, dest):
        self.send({'dest': dest, 'type': 'JOIN_REQUEST', 'gui': self.id})

    ###################
    def send_join_reply(self, gui, addr):
        self.send({'dest': wsn.BROADCAST_ADDR, 'type': 'JOIN_REPLY', 'source': self.addr, 'gui': gui, 'addr': addr})

    ###################
    def send_join_ack(self, dest):
        self.send({'dest': dest, 'type': 'JOIN_ACK', 'source': self.addr})

    ###################
    def on_receive(self, pck):
        if self.role == Roles.ROOT:
            if pck['type'] == 'PROBE':
                yield self.timeout(.5)
                self.send_hearth_beat()
            if pck['type'] == 'JOIN_REQUEST':
                self.log(pck)
                yield self.timeout(.5)
                self.send_join_reply(pck['gui'], wsn.Addr(self.addr.net_addr, pck['gui']))

        elif self.role == Roles.UNDISCOVERED:
            if pck['type'] == 'HEARTH_BEAT':
                self.kill_timer('TIMER_PROBE')
                self.role = Roles.UNREGISTERED
                self.scene.nodecolor(self.id, 1, 1, 0)
                yield self.timeout(.5)
                self.send_probe()
                self.set_timer('TIMER_JOIN_REQUEST', 20)

        if self.role == Roles.UNREGISTERED:
            if pck['type'] == 'HEARTH_BEAT':
                self.log(pck)
                self.received_HB_addresses.append(pck['source'])
            if pck['type'] == 'JOIN_REPLY':
                self.log(pck)
                if pck['gui'] == self.id:
                    self.addr = pck['addr']
                    self.role = Roles.REGISTERED
                    self.scene.nodecolor(self.id, 0, 1, 0)
                    self.kill_timer('TIMER_JOIN_REQUEST')
                    yield self.timeout(.5)
                    self.send_join_ack(pck['source'])

    ###################
    def on_timer_fired(self, name, *args, **kwargs):
        if name == 'TIMER_ARRIVAL':
            self.scene.nodecolor(self.id, 1, 0, 0)  # sets self color to grey
            self.wake_up()
            self.set_timer('TIMER_PROBE', 1)

        elif name == 'TIMER_PROBE':
            if self.c_probe < self.th_probe:
                self.send_probe()
                self.c_probe += 1
                self.set_timer('TIMER_PROBE', 1)
            else:
                if self.is_root_eligible:
                    self.role = Roles.ROOT
                    self.scene.nodecolor(self.id, 0, 0, 1)
                    self.addr = wsn.Addr(1, 254)
                    self.set_timer('TIMER_HEARTH_BEAT', 15)
                else:
                    self.c_probe = 0
                    self.set_timer('TIMER_PROBE', 30)

        elif name == 'TIMER_HEARTH_BEAT':
            self.send_hearth_beat()
            self.set_timer('TIMER_HEARTH_BEAT', 15)

        elif name == 'TIMER_JOIN_REQUEST':
            if len(self.received_HB_addresses) == 0:
                self.send_probe()
                self.set_timer('TIMER_JOIN_REQUEST', 20)
            else:
                self.send_join_request(random.choice(self.received_HB_addresses))
                self.set_timer('TIMER_JOIN_REQUEST', 5)


###########################################################
def create_network(node_class, number_of_nodes=100):
    # Create number of nodes with random interarrival times
    edge = math.ceil(math.sqrt(number_of_nodes))
    for i in range(number_of_nodes):
        x = i / edge
        y = i % edge
        px = 50 + x * 60 + random.uniform(-20, 20)
        py = 50 + y * 60 + random.uniform(-20, 20)
        node = sim.add_node(node_class, (px, py))
        node.tx_range = 75
        node.logging = True
        node.arrival = random.uniform(0, 50)


sim = wsn.Simulator(
    duration=100, # simulation Duration in seconds
    timescale=0.1, #  The real time dureation of 1 second simualtion time
    visual=True,    # visualization active
    terrain_size=(700, 700),    #terrain size
    title="Data Collection Tree") 

# creating random network
create_network(SensorNode, 100)

# start the simulation
sim.run()

# TODO Create 100 nodes at random locations with random interarrival times.  You can create all nodes at the beginnning and activate nodes at random times
# When nodes are created they appear in white
# Activated nodes becomes red
# Discovered nodes will be yellow
# Registered nodes will be green.
# Root/Routers/Cluster Heads should be blue