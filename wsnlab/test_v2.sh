#!/bin/bash

# Test script for data_collection_tree_v2.py

echo "=========================================="
echo "Testing Data Collection Tree V2"
echo "=========================================="
echo ""

# Check if file exists
if [ ! -f "data_collection_tree_v2.py" ]; then
    echo "❌ ERROR: data_collection_tree_v2.py not found!"
    exit 1
fi

echo "✓ File exists: data_collection_tree_v2.py"
echo ""

# Check Python syntax
echo "Checking Python syntax..."
python3 -m py_compile data_collection_tree_v2.py
if [ $? -eq 0 ]; then
    echo "✓ Syntax check passed"
else
    echo "❌ Syntax errors found!"
    exit 1
fi
echo ""

# Run simulation for 100 seconds (quick test)
echo "Running quick simulation (100s)..."
echo "Press Ctrl+C to stop early"
echo ""

# Backup existing stats
if [ -f "routing_statistics.csv" ]; then
    mv routing_statistics.csv routing_statistics_backup.csv
    echo "✓ Backed up existing stats"
fi

# Run simulation
timeout 110 python3 data_collection_tree_v2.py

# Check if stats were generated
echo ""
echo "Checking generated files..."

if [ -f "routing_statistics.csv" ]; then
    echo "✓ routing_statistics.csv generated"
    lines=$(wc -l < routing_statistics.csv)
    echo "  → $lines lines"
else
    echo "❌ routing_statistics.csv not found"
fi

if [ -f "child_networks_table.csv" ]; then
    echo "✓ child_networks_table.csv generated"
fi

if [ -f "members_table.csv" ]; then
    echo "✓ members_table.csv generated"
fi

if [ -f "neighbors_table.csv" ]; then
    echo "✓ neighbors_table.csv generated"
fi

echo ""
echo "=========================================="
echo "Test Complete!"
echo "=========================================="
echo ""
echo "To view stats:"
echo "  python3 read_stats.py"
echo ""
echo "To run full simulation:"
echo "  python3 data_collection_tree_v2.py"
