#!/bin/bash
# Stop all services
echo "Stopping all services..."
pkill -f "uvicorn.*main:app" 2>/dev/null || true
echo "All services stopped."