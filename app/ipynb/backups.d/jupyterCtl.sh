#!/usr/bin/env bash

# =============================================================================
# Jupyter Notebook Control Script
# =============================================================================
# Purpose: Start, stop, and check status of Jupyter Lab for Bank Inventory System
# Usage: ./jupyter_control.sh [start|stop|status|restart]
# =============================================================================

# Script configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
VENV_PATH="${PROJECT_ROOT}/.venv"
NOTEBOOK_DIR="${PROJECT_ROOT}/app/ipynb"
LOG_DIR="${PROJECT_ROOT}/app/var/tmp"
LOG_FILE="${LOG_DIR}/jupyter_nohup.out"
PID_FILE="${LOG_DIR}/jupyter.pid"
JUPYTER_PORT=18888

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# =============================================================================
# Helper Functions
# =============================================================================

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

check_prerequisites() {
    # Check if virtual environment exists
    if [ ! -d "$VENV_PATH" ]; then
        print_error "Virtual environment not found at: $VENV_PATH"
        print_status "Please create it first with: uv venv"
        exit 1
    fi
    
    # Check if notebook directory exists
    if [ ! -d "$NOTEBOOK_DIR" ]; then
        print_warning "Notebook directory not found, creating: $NOTEBOOK_DIR"
        mkdir -p "$NOTEBOOK_DIR"
    fi
    
    # Check if log directory exists
    if [ ! -d "$LOG_DIR" ]; then
        print_status "Creating log directory: $LOG_DIR"
        mkdir -p "$LOG_DIR"
    fi
    
    # Check if Jupyter is installed
    if ! "${VENV_PATH}/bin/python" -c "import jupyter" 2>/dev/null; then
        print_error "Jupyter not installed in virtual environment"
        print_status "Install with: uv add jupyter jupyterlab"
        exit 1
    fi
}

get_jupyter_pid() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        # Check if process is actually running
        if ps -p "$pid" > /dev/null 2>&1; then
            echo "$pid"
        else
            # PID file exists but process is not running
            rm -f "$PID_FILE"
            echo ""
        fi
    else
        echo ""
    fi
}

# =============================================================================
# Main Functions
# =============================================================================

start_jupyter() {
    print_status "Starting Jupyter Lab..."
    
    # Check if already running
    local pid=$(get_jupyter_pid)
    if [ -n "$pid" ]; then
        print_warning "Jupyter Lab is already running with PID: $pid"
        print_status "Access at: http://0.0.0.0:${JUPYTER_PORT}"
        return 0
    fi
    
    # Check prerequisites
    check_prerequisites
    
    # Load environment variables
    if [ -f "${PROJECT_ROOT}/.env" ]; then
        print_status "Loading environment variables from .env"
        set -a
        source "${PROJECT_ROOT}/.env"
        set +a
    fi
    
    # Activate virtual environment and start Jupyter
    print_status "Activating virtual environment: $VENV_PATH"
    print_status "Notebook directory: $NOTEBOOK_DIR"
    print_status "Log file: $LOG_FILE"
    
    # Start Jupyter Lab in background
    cd "$PROJECT_ROOT"
    nohup "${VENV_PATH}/bin/jupyter" lab \
        --notebook-dir="$NOTEBOOK_DIR" \
        --port=$JUPYTER_PORT \
        --no-browser \
        --ip=0.0.0.0 \
        --NotebookApp.token='' \
        --NotebookApp.password='' \
        --ServerApp.disable_check_xsrf=True \
        > "$LOG_FILE" 2>&1 &
    
    local jupyter_pid=$!
    echo $jupyter_pid > "$PID_FILE"
    
    # Wait a moment for Jupyter to start
    sleep 3
    
    # Check if Jupyter started successfully
    if ps -p $jupyter_pid > /dev/null; then
        print_success "Jupyter Lab started successfully with PID: $jupyter_pid"
        print_status "Access Jupyter Lab at: http://localhost:${JUPYTER_PORT}"
        print_status "Notebook directory: $NOTEBOOK_DIR"
        print_status "Log file: $LOG_FILE"
        echo ""
        print_status "To view logs: tail -f $LOG_FILE"
        print_status "To stop: $0 stop"
    else
        print_error "Failed to start Jupyter Lab"
        print_status "Check log file for details: $LOG_FILE"
        tail -n 20 "$LOG_FILE"
        rm -f "$PID_FILE"
        exit 1
    fi
}

stop_jupyter() {
    print_status "Stopping Jupyter Lab..."
    
    local pid=$(get_jupyter_pid)
    if [ -z "$pid" ]; then
        print_warning "Jupyter Lab is not running"
        return 0
    fi
    
    # Try graceful shutdown first
    print_status "Sending TERM signal to PID: $pid"
    kill -TERM $pid 2>/dev/null
    
    # Wait for process to terminate
    local count=0
    while [ $count -lt 10 ]; do
        if ! ps -p $pid > /dev/null 2>&1; then
            break
        fi
        sleep 1
        count=$((count + 1))
    done
    
    # Force kill if still running
    if ps -p $pid > /dev/null 2>&1; then
        print_warning "Process didn't terminate, forcing shutdown..."
        kill -9 $pid 2>/dev/null
        sleep 1
    fi
    
    # Clean up PID file
    rm -f "$PID_FILE"
    
    print_success "Jupyter Lab stopped successfully"
}

status_jupyter() {
    local pid=$(get_jupyter_pid)
    
    echo "========================================="
    echo "Jupyter Lab Status"
    echo "========================================="
    
    if [ -n "$pid" ]; then
        print_success "Jupyter Lab is RUNNING"
        echo ""
        echo "  PID:              $pid"
        echo "  URL:              http://localhost:${JUPYTER_PORT}"
        echo "  Notebook Dir:     $NOTEBOOK_DIR"
        echo "  Log File:         $LOG_FILE"
        echo "  Virtual Env:      $VENV_PATH"
        
        # Show process info
        echo ""
        echo "Process Information:"
        ps -f -p $pid | tail -n +1
        
        # Show recent log entries
        if [ -f "$LOG_FILE" ]; then
            echo ""
            echo "Recent Log Entries:"
            echo "-----------------"
            tail -n 5 "$LOG_FILE"
        fi
    else
        print_warning "Jupyter Lab is NOT RUNNING"
        echo ""
        echo "  Notebook Dir:     $NOTEBOOK_DIR"
        echo "  Log File:         $LOG_FILE"
        echo "  Virtual Env:      $VENV_PATH"
        
        # Check if log file exists and show last error
        if [ -f "$LOG_FILE" ]; then
            echo ""
            echo "Last Log Entries:"
            echo "-----------------"
            tail -n 10 "$LOG_FILE" | grep -E "(ERROR|Error|Failed|failed)" | tail -n 3
        fi
    fi
    
    echo "========================================="
}

restart_jupyter() {
    print_status "Restarting Jupyter Lab..."
    stop_jupyter
    sleep 2
    start_jupyter
}

view_logs() {
    if [ -f "$LOG_FILE" ]; then
        print_status "Viewing Jupyter Lab logs (Ctrl+C to exit)..."
        echo "========================================="
        tail -f "$LOG_FILE"
    else
        print_error "Log file not found: $LOG_FILE"
        exit 1
    fi
}

# =============================================================================
# Main Script Logic
# =============================================================================

case "$1" in
    start)
        start_jupyter
        ;;
    stop)
        stop_jupyter
        ;;
    status)
        status_jupyter
        ;;
    restart)
        restart_jupyter
        ;;
    logs)
        view_logs
        ;;
    *)
        echo "Bank Application Inventory System - Jupyter Lab Control"
        echo ""
        echo "Usage: $0 {start|stop|status|restart|logs}"
        echo ""
        echo "Commands:"
        echo "  start    - Start Jupyter Lab server"
        echo "  stop     - Stop Jupyter Lab server"
        echo "  status   - Check if Jupyter Lab is running"
        echo "  restart  - Restart Jupyter Lab server"
        echo "  logs     - View Jupyter Lab logs (tail -f)"
        echo ""
        echo "Configuration:"
        echo "  Virtual Env:  $VENV_PATH"
        echo "  Notebook Dir: $NOTEBOOK_DIR"
        echo "  Log File:     $LOG_FILE"
        echo "  Port:         $JUPYTER_PORT"
        exit 1
        ;;
esac

exit 0
