#!/bin/bash

# Streamlit Control Script
# Usage: ./streamlit_control.sh --restart | --stop

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STREAMLIT_APP="${SCRIPT_DIR}/../streamlit_app.py"
APP_DIR="${SCRIPT_DIR}"
VAR_DIR="${APP_DIR}/../var/tmp/"
PID_FILE="${VAR_DIR}/streamlit.pid"
LOG_FILE="${VAR_DIR}/streamlit.log"
VENV_ACTIVATE="${SCRIPT_DIR}/../../.venv/bin/activate"
ENV_FILE="${SCRIPT_DIR}/../../.env"
STREAMLIT_PORT=8501

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Create var directory if it doesn't exist
mkdir -p "${VAR_DIR}"

# Function to check if Streamlit is running
is_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            return 0
        else
            # PID file exists but process is dead
            rm -f "$PID_FILE"
            return 1
        fi
    else
        return 1
    fi
}

# Function to stop Streamlit
stop_streamlit() {
    echo -e "${YELLOW}Stopping ALL Streamlit instances...${NC}"

    # Kill ALL streamlit processes regardless of port
    # First try to find all streamlit processes
    STREAMLIT_PIDS=$(pgrep -f "streamlit run" 2>/dev/null)

    if [ -n "$STREAMLIT_PIDS" ]; then
        echo "Found Streamlit processes: $STREAMLIT_PIDS"

        # Kill all streamlit processes
        for PID in $STREAMLIT_PIDS; do
            echo "Killing Streamlit process: $PID"
            kill "$PID" 2>/dev/null
        done

        # Wait a moment
        sleep 2

        # Force kill any remaining
        REMAINING_PIDS=$(pgrep -f "streamlit run" 2>/dev/null)
        if [ -n "$REMAINING_PIDS" ]; then
            echo "Force killing remaining processes: $REMAINING_PIDS"
            for PID in $REMAINING_PIDS; do
                kill -9 "$PID" 2>/dev/null
            done
        fi

        echo -e "${GREEN}All Streamlit instances stopped${NC}"
    else
        echo "No Streamlit processes found"
    fi

    # Clean up PID file regardless
    rm -f "$PID_FILE"

    # Also kill any orphaned Python processes running streamlit
    pkill -f "python.*streamlit" 2>/dev/null || true

    return 0
}

# Function to clear Streamlit cache
clear_cache() {
    echo -e "${YELLOW}Clearing Streamlit cache...${NC}"

    # Clear Streamlit cache directories
    CACHE_DIRS=(
        "${HOME}/.streamlit/cache"
        "${SCRIPT_DIR}/.streamlit/cache"
        "${APP_DIR}/.streamlit/cache"
    )

    for dir in "${CACHE_DIRS[@]}"; do
        if [ -d "$dir" ]; then
            echo "Removing cache: $dir"
            rm -rf "$dir"
        fi
    done

    # Clear Python cache
    find "${APP_DIR}" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "${APP_DIR}" -type f -name "*.pyc" -delete 2>/dev/null || true

    echo -e "${GREEN}Cache cleared${NC}"
}

# Function to start Streamlit
start_streamlit() {
    echo -e "${YELLOW}Starting Streamlit...${NC}"

    # ALWAYS kill any existing instances first to prevent port conflicts
    stop_streamlit
    sleep 2

    # Check if virtual environment exists
    if [ ! -f "$VENV_ACTIVATE" ]; then
        echo -e "${RED}Virtual environment not found at $VENV_ACTIVATE${NC}"
        return 1
    fi

    # Check if env file exists
    if [ ! -f "$ENV_FILE" ]; then
        echo -e "${RED}Environment file not found at $ENV_FILE${NC}"
        return 1
    fi

    # Check if app file exists
    if [ ! -f "${STREAMLIT_APP}" ]; then
        echo -e "${RED}Streamlit app not found at ${STREAMLIT_APP}${NC}"
        return 1
    fi

    # Clear cache before starting
    clear_cache

    # Start Streamlit in background
    echo "Starting Streamlit on port ${STREAMLIT_PORT}..."

    # Use nohup to run in background
    cd "$SCRIPT_DIR"
    nohup bash -c "
        source '$VENV_ACTIVATE'
        source '$ENV_FILE'
        export PYTHONPATH='$SCRIPT_DIR'
        streamlit run '$STREAMLIT_APP' \
            --server.port=${STREAMLIT_PORT} \
            --server.headless=true \
            --browser.gatherUsageStats=false \
            --server.fileWatcherType=none \
            --logger.level=info \
            > '$LOG_FILE' 2>&1 &
        echo \$! > '$PID_FILE'
    " > /dev/null 2>&1 &

    # Wait a moment for the process to start
    sleep 3

    # Check if started successfully
    if is_running; then
        PID=$(cat "$PID_FILE")
        echo -e "${GREEN}Streamlit started successfully${NC}"
        echo "PID: $PID"
        echo "Port: $STREAMLIT_PORT"
        echo "Log file: $LOG_FILE"
        echo "URL: http://localhost:${STREAMLIT_PORT}"
        return 0
    else
        echo -e "${RED}Failed to start Streamlit${NC}"
        echo "Check log file: $LOG_FILE"
        if [ -f "$LOG_FILE" ]; then
            echo "Last 10 lines of log:"
            tail -10 "$LOG_FILE"
        fi
        return 1
    fi
}

# Function to restart Streamlit
restart_streamlit() {
    echo -e "${YELLOW}Restarting Streamlit...${NC}"

    # Stop if running
    if is_running; then
        stop_streamlit
        sleep 2
    fi

    # Start
    start_streamlit
}

# Function to show status
show_status() {
    if is_running; then
        PID=$(cat "$PID_FILE")
        echo -e "${GREEN}Streamlit is running${NC}"
        echo "PID: $PID"
        echo "Port: $STREAMLIT_PORT"
        echo "Log file: $LOG_FILE"

        # Show process info
        ps -p "$PID" -o pid,vsz,rss,comm,args --no-headers
    else
        echo -e "${YELLOW}Streamlit is not running${NC}"
    fi
}

# Function to tail logs
tail_logs() {
    if [ -f "$LOG_FILE" ]; then
        echo "Tailing log file: $LOG_FILE"
        echo "Press Ctrl+C to stop..."
        tail -f "$LOG_FILE"
    else
        echo -e "${YELLOW}Log file not found: $LOG_FILE${NC}"
    fi
}

# Main script
case "$1" in
    --restart|-r)
        restart_streamlit
        ;;
    --stop|-s)
        stop_streamlit
        ;;
    --start)
        start_streamlit
        ;;
    --status)
        show_status
        ;;
    --logs|-l)
        tail_logs
        ;;
    --clear-cache)
        clear_cache
        ;;
    *)
        echo "Streamlit Control Script"
        echo "Usage: $0 [OPTION]"
        echo ""
        echo "Options:"
        echo "  --restart, -r    Stop (if running) and start Streamlit with fresh cache"
        echo "  --stop, -s       Stop Streamlit"
        echo "  --start          Start Streamlit (fails if already running)"
        echo "  --status         Show current status"
        echo "  --logs, -l       Tail the log file"
        echo "  --clear-cache    Clear Streamlit cache only"
        echo ""
        echo "Files:"
        echo "  PID file: $PID_FILE"
        echo "  Log file: $LOG_FILE"
        echo "  App: $STREAMLIT_APP"
        echo "  Port: $STREAMLIT_PORT"
        exit 1
        ;;
esac

exit $?
