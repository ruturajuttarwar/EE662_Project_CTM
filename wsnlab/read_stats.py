#!/usr/bin/env python3
"""
Simple script to read and display routing statistics
"""
import csv
import sys

def read_routing_stats(filename='routing_statistics.csv'):
    """Read and display routing statistics from CSV file"""
    
    try:
        with open(filename, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
        if not rows:
            print(f"No data found in {filename}")
            return
        
        print("=" * 80)
        print(f"ROUTING STATISTICS - {len(rows)} nodes")
        print("=" * 80)
        
        # Calculate totals
        totals = {
            'direct_mesh': 0,
            'intra_cluster': 0,
            'downward_tree': 0,
            'upward_tree': 0,
            'multihop_routes': 0,
            'route_failures': 0,
            'total_routes': 0,
            'neighbors_1hop': 0,
            'neighbors_multihop': 0
        }
        
        # Count nodes by role
        role_counts = {}
        
        for row in rows:
            role = row['role']
            role_counts[role] = role_counts.get(role, 0) + 1
            
            for key in totals:
                if key in row:
                    totals[key] += int(row[key])
        
        # Print network summary
        print("\nNetwork Summary:")
        print("-" * 80)
        for role, count in sorted(role_counts.items()):
            print(f"  {role:20s}: {count:3d} nodes")
        
        # Print routing totals
        print("\nRouting Totals:")
        print("-" * 80)
        total = totals['total_routes']
        
        if total > 0:
            print(f"  Total Routes:        {total:6d}")
            print(f"  Direct Mesh:         {totals['direct_mesh']:6d} ({100*totals['direct_mesh']/total:5.1f}%)")
            print(f"  Intra-Cluster:       {totals['intra_cluster']:6d} ({100*totals['intra_cluster']/total:5.1f}%)")
            print(f"  Downward Tree:       {totals['downward_tree']:6d} ({100*totals['downward_tree']/total:5.1f}%)")
            print(f"  Upward Tree:         {totals['upward_tree']:6d} ({100*totals['upward_tree']/total:5.1f}%)")
            if totals['multihop_routes'] > 0:
                print(f"  Multi-Hop Routes:    {totals['multihop_routes']:6d} ({100*totals['multihop_routes']/total:5.1f}%)")
            print(f"  Route Failures:      {totals['route_failures']:6d} ({100*totals['route_failures']/total:5.1f}%)")
        else:
            print("  No routing activity recorded")
        
        # Neighbor discovery stats
        if totals['neighbors_1hop'] > 0 or totals['neighbors_multihop'] > 0:
            print("\nNeighbor Discovery:")
            print("-" * 80)
            print(f"  1-Hop Neighbors:     {totals['neighbors_1hop']:6d}")
            print(f"  Multi-Hop Neighbors: {totals['neighbors_multihop']:6d}")
            if totals['neighbors_1hop'] > 0:
                avg_multihop = totals['neighbors_multihop'] / len(rows)
                print(f"  Avg Multi-Hop/Node:  {avg_multihop:6.1f}")
        
        # Print top 10 most active nodes
        print("\nTop 10 Most Active Nodes:")
        print("-" * 80)
        print(f"{'Node ID':>8} {'Role':15} {'Direct':>8} {'Intra':>8} {'Down':>8} {'Up':>8} {'Fail':>8} {'Total':>8}")
        print("-" * 80)
        
        sorted_rows = sorted(rows, key=lambda x: int(x['total_routes']), reverse=True)[:10]
        for row in sorted_rows:
            print(f"{row['node_id']:>8} {row['role']:15} "
                  f"{row['direct_mesh']:>8} {row['intra_cluster']:>8} "
                  f"{row['downward_tree']:>8} {row['upward_tree']:>8} "
                  f"{row['route_failures']:>8} {row['total_routes']:>8}")
        
        # Print nodes with failures
        failed_nodes = [row for row in rows if int(row['route_failures']) > 0]
        if failed_nodes:
            print(f"\nNodes with Route Failures: {len(failed_nodes)}")
            print("-" * 80)
            print(f"{'Node ID':>8} {'Role':15} {'Failures':>10} {'Total Routes':>15}")
            print("-" * 80)
            for row in sorted(failed_nodes, key=lambda x: int(x['route_failures']), reverse=True)[:10]:
                print(f"{row['node_id']:>8} {row['role']:15} "
                      f"{row['route_failures']:>10} {row['total_routes']:>15}")
        
        # Hybrid routing effectiveness
        if total > 0:
            direct_routes = totals['direct_mesh'] + totals['intra_cluster']
            tree_routes = totals['upward_tree'] + totals['downward_tree']
            
            print("\nHybrid Routing Effectiveness:")
            print("-" * 80)
            print(f"  Direct/Mesh Routes:  {direct_routes:6d} ({100*direct_routes/total:5.1f}%) ← Lower latency")
            print(f"  Tree Routes:         {tree_routes:6d} ({100*tree_routes/total:5.1f}%) ← Traditional")
            
            if direct_routes > tree_routes:
                print(f"  ✓ Hybrid routing is effective! {100*direct_routes/total:.1f}% of routes use direct paths")
            else:
                print(f"  ⚠ Most routes still use tree ({100*tree_routes/total:.1f}%)")
        
        print("\n" + "=" * 80)
        
    except FileNotFoundError:
        print(f"Error: {filename} not found!")
        print("Run the simulation first: python data_collection_tree.py")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)

if __name__ == '__main__':
    filename = sys.argv[1] if len(sys.argv) > 1 else 'routing_statistics.csv'
    read_routing_stats(filename)
