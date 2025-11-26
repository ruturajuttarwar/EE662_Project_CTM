"""
Compare pure tree routing vs CTM-AdHoc hybrid routing
Runs both modes and compares statistics
"""
import sys
sys.path.insert(1, '.')
from source import config

# Save original settings
original_viz = config.SIM_VISUALIZATION
original_duration = config.SIM_DURATION
original_node_count = config.SIM_NODE_COUNT

# Test configuration
config.SIM_NODE_COUNT = 50
config.SIM_DURATION = 500
config.SIM_VISUALIZATION = False  # Disable for faster comparison

print("=" * 70)
print("CTM-AdHoc Hybrid Routing Comparison")
print("=" * 70)
print(f"Configuration: {config.SIM_NODE_COUNT} nodes, {config.SIM_DURATION}s duration")
print()

results = {}

for mode in ['tree', 'hybrid']:
    print(f"\n{'='*70}")
    print(f"Running: {mode.upper()} MODE")
    print('='*70)
    
    # Set mode
    config.ENABLE_HYBRID_ROUTING = (mode == 'hybrid')
    
    # Import fresh simulation
    import importlib
    if 'data_collection_tree' in sys.modules:
        del sys.modules['data_collection_tree']
    
    from data_collection_tree import SensorNode, create_network, write_routing_statistics_csv, NODE_POS
    from source import wsnlab_vis as wsn
    
    # Create simulator
    sim = wsn.Simulator(
        duration=config.SIM_DURATION,
        timescale=0,  # Run as fast as possible
        visual=False,
        terrain_size=config.SIM_TERRAIN_SIZE,
        title=f"{mode.upper()} Routing")
    
    # Create network
    create_network(SensorNode, config.SIM_NODE_COUNT)
    
    # Run simulation
    sim.run()
    
    # Collect statistics
    stats = {
        'direct_mesh': 0,
        'intra_cluster': 0,
        'downward_tree': 0,
        'upward_tree': 0,
        'route_failures': 0
    }
    
    for node in sim.nodes:
        if hasattr(node, 'routing_stats'):
            for key in stats:
                stats[key] += node.routing_stats[key]
    
    total = sum(stats.values())
    stats['total'] = total
    results[mode] = stats
    
    # Export
    write_routing_statistics_csv(f"routing_statistics_{mode}.csv")
    
    print(f"\n{mode.upper()} Results:")
    print(f"  Total Routes: {total}")
    if total > 0:
        print(f"    Direct Mesh:    {stats['direct_mesh']:6d} ({100*stats['direct_mesh']/total:5.1f}%)")
        print(f"    Intra-Cluster:  {stats['intra_cluster']:6d} ({100*stats['intra_cluster']/total:5.1f}%)")
        print(f"    Downward Tree:  {stats['downward_tree']:6d} ({100*stats['downward_tree']/total:5.1f}%)")
        print(f"    Upward Tree:    {stats['upward_tree']:6d} ({100*stats['upward_tree']/total:5.1f}%)")
        print(f"    Failures:       {stats['route_failures']:6d} ({100*stats['route_failures']/total:5.1f}%)")

# Comparison
print("\n" + "=" * 70)
print("COMPARISON SUMMARY")
print("=" * 70)

if results['tree']['total'] > 0 and results['hybrid']['total'] > 0:
    tree_total = results['tree']['total']
    hybrid_total = results['hybrid']['total']
    
    print(f"\nTotal Routing Operations:")
    print(f"  Tree Mode:   {tree_total}")
    print(f"  Hybrid Mode: {hybrid_total}")
    
    print(f"\nDirect Mesh Routes (Hybrid advantage):")
    print(f"  Tree:   {results['tree']['direct_mesh']} ({100*results['tree']['direct_mesh']/tree_total:.1f}%)")
    print(f"  Hybrid: {results['hybrid']['direct_mesh']} ({100*results['hybrid']['direct_mesh']/hybrid_total:.1f}%)")
    
    print(f"\nUpward Tree Routes (Load on hierarchy):")
    print(f"  Tree:   {results['tree']['upward_tree']} ({100*results['tree']['upward_tree']/tree_total:.1f}%)")
    print(f"  Hybrid: {results['hybrid']['upward_tree']} ({100*results['hybrid']['upward_tree']/hybrid_total:.1f}%)")
    
    if results['hybrid']['direct_mesh'] > 0:
        reduction = 100 * (results['tree']['upward_tree'] - results['hybrid']['upward_tree']) / tree_total
        print(f"\nHierarchy Load Reduction: {reduction:.1f}%")
    
    print(f"\nRoute Failures:")
    print(f"  Tree:   {results['tree']['route_failures']}")
    print(f"  Hybrid: {results['hybrid']['route_failures']}")
else:
    print("\nInsufficient routing activity for comparison")
    print("Try increasing SIM_DURATION or enabling sensor data transmission")

print("\n" + "=" * 70)
print("Detailed statistics exported to:")
print("  - routing_statistics_tree.csv")
print("  - routing_statistics_hybrid.csv")
print("=" * 70)

# Restore original settings
config.SIM_VISUALIZATION = original_viz
config.SIM_DURATION = original_duration
config.SIM_NODE_COUNT = original_node_count
