#!/bin/bash

# Script to view simulation log

if [ ! -f "simulation_log.txt" ]; then
    echo "❌ No log file found. Run simulation first:"
    echo "   python data_collection_tree.py"
    echo "   or"
    echo "   python data_collection_tree_v2.py"
    exit 1
fi

echo "=========================================="
echo "Viewing simulation_log.txt"
echo "=========================================="
echo ""

# Check if argument provided
if [ "$1" == "tail" ]; then
    # Show last 50 lines
    tail -n 50 simulation_log.txt
elif [ "$1" == "head" ]; then
    # Show first 50 lines
    head -n 50 simulation_log.txt
elif [ "$1" == "grep" ] && [ -n "$2" ]; then
    # Search for pattern
    grep "$2" simulation_log.txt
elif [ "$1" == "less" ]; then
    # Interactive view
    less simulation_log.txt
else
    # Show entire file
    cat simulation_log.txt
fi

echo ""
echo "=========================================="
echo "Log file info:"
lines=$(wc -l < simulation_log.txt)
size=$(du -h simulation_log.txt | cut -f1)
echo "  Lines: $lines"
echo "  Size: $size"
echo "=========================================="
echo ""
echo "Usage:"
echo "  ./view_log.sh          # Show entire log"
echo "  ./view_log.sh tail     # Show last 50 lines"
echo "  ./view_log.sh head     # Show first 50 lines"
echo "  ./view_log.sh grep 'ROUTER'  # Search for pattern"
echo "  ./view_log.sh less     # Interactive view"
