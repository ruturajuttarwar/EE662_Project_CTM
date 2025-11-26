"""
Test script to demonstrate CTM-AdHoc hybrid routing
This sends test packets through the network to exercise different routing paths
"""
import random
from enum import Enum
import sys
sys.path.insert(1, '.')
from source import wsnlab_vis as wsn
import math
from source import config

# Import the main simulation
from data_collection_tree import SensorNode, create_network, write_routing_statistics_csv, NODE_POS, ENABLE_HYBRID_ROUTING

# Override config for testing
config.SIM_NODE_COUNT = 50
config.SIM_DURATION = 1000
config.ENABLE_HYBRID_ROUTING = True
config.SIM_VISUALIZATION = True

print(f"Starting CTM-AdHoc Hybrid Routing Test")
print(f"Hybrid Routing Enabled: {config.ENABLE_HYBRID_ROUTING}")
print(f"Node Count: {config.SIM_NODE_COUNT}")
print(f"Duration: {config.SIM_DURATION}s")
print("-" * 60)

# Create simulator
sim = wsn.Simulator(
    duration=config.SIM_DURATION,
    timescale=config.SIM_TIME_SCALE,
    visual=config.SIM_VISUALIZATION,
    terrain_size=config.SIM_TERRAIN_SIZE,
    title="CTM-AdHoc Hybrid Routing Test")

# Create network
create_network(SensorNode, config.SIM_NODE_COUNT)

# Run simulation
sim.run()

print("\n" + "=" * 60)
print("Simulation Complete!")
print("=" * 60)

# Export statistics
if ENABLE_HYBRID_ROUTING:
    write_routing_statistics_csv("routing_statistics.csv")
    print("\nRouting Statistics Summary:")
    print("-" * 60)
    
    total_stats = {
        'direct_mesh': 0,
        'intra_cluster': 0,
        'downward_tree': 0,
        'upward_tree': 0,
        'route_failures': 0
    }
    
    for node in sim.nodes:
        if hasattr(node, 'routing_stats'):
            for key in total_stats:
                total_stats[key] += node.routing_stats[key]
    
    total_routes = sum(total_stats.values())
    
    if total_routes > 0:
        print(f"Total Routes: {total_routes}")
        print(f"  Direct Mesh:      {total_stats['direct_mesh']:6d} ({100*total_stats['direct_mesh']/total_routes:5.1f}%)")
        print(f"  Intra-Cluster:    {total_stats['intra_cluster']:6d} ({100*total_stats['intra_cluster']/total_routes:5.1f}%)")
        print(f"  Downward Tree:    {total_stats['downward_tree']:6d} ({100*total_stats['downward_tree']/total_routes:5.1f}%)")
        print(f"  Upward Tree:      {total_stats['upward_tree']:6d} ({100*total_stats['upward_tree']/total_routes:5.1f}%)")
        print(f"  Route Failures:   {total_stats['route_failures']:6d} ({100*total_stats['route_failures']/total_routes:5.1f}%)")
    else:
        print("No routing activity recorded")
    
    print("\nDetailed statistics exported to: routing_statistics.csv")

print("\nTest complete!")
