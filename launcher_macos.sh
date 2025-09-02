#!/bin/bash
# PubMed Literature Push Launcher for macOS
# Integrates environment checking, automatic setup and one-click launch

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

# Set UTF-8 locale
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Log function
log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    
    local color=""
    case "$level" in
        "INFO") color="$WHITE" ;;
        "SUCCESS") color="$GREEN" ;;
        "WARNING") color="$YELLOW" ;;
        "ERROR") color="$RED" ;;
        *) color="$WHITE" ;;
    esac
    
    echo -e "${color}[$timestamp] [$level] $message${NC}"
}

# Show help information
show_help() {
    echo -e "${CYAN}===================================="
    echo -e "${CYAN}  PubMed Literature Push Launcher for macOS (Cross-Platform)"
    echo -e "${CYAN}====================================${NC}"
    echo ""
    echo -e "${YELLOW}Usage:${NC}"
    echo -e "${WHITE}  ./launcher_macos.sh [Options]${NC}"
    echo ""
    echo -e "${YELLOW}Options:${NC}"
    echo -e "${WHITE}  --setup         Run complete environment setup${NC}"
    echo -e "${WHITE}  --force         Force environment re-setup${NC}"
    echo -e "${WHITE}  --action        Execute specific action${NC}"
    echo -e "${WHITE}                  Available actions: start, stop, restart, run, config, check${NC}"
    echo -e "${WHITE}                  enable-autostart, disable-autostart${NC}"
    echo -e "${WHITE}  --help          Show this help information${NC}"
    echo ""
    echo -e "${YELLOW}Examples:${NC}"
    echo -e "${WHITE}  ./launcher_macos.sh                    # Quick launch${NC}"
    echo -e "${WHITE}  ./launcher_macos.sh --setup            # Complete environment setup${NC}"
    echo -e "${WHITE}  ./launcher_macos.sh --action start     # Start background service${NC}"
    echo -e "${WHITE}  ./launcher_macos.sh --action run       # Run main program${NC}"
    echo ""
}

# Check Python installation
check_python() {
    log "INFO" "Checking Python installation..."
    
    if command -v python3 &> /dev/null; then
        local python_version=$(python3 --version 2>&1)
        log "SUCCESS" "Python found: $python_version"
        PYTHON_CMD="python3"
        return 0
    elif command -v python &> /dev/null; then
        local python_version=$(python --version 2>&1)
        log "SUCCESS" "Python found: $python_version"
        PYTHON_CMD="python"
        return 0
    else
        log "ERROR" "Python not found. Please install Python 3.8+ and add to PATH"
        return 1
    fi
}

# Create virtual environment
create_virtualenv() {
    log "INFO" "Creating Python virtual environment..."
    
    local venv_path="$PROJECT_ROOT/.venv"
    
    if [ -d "$venv_path" ]; then
        log "INFO" "Virtual environment already exists, skipping creation"
        return 0
    fi
    
    if ! $PYTHON_CMD -m venv "$venv_path"; then
        log "ERROR" "Failed to create virtual environment"
        return 1
    fi
    
    log "SUCCESS" "Virtual environment created successfully"
    return 0
}

# Install dependencies
install_dependencies() {
    log "INFO" "Installing Python dependencies..."
    
    local requirements_file="$PROJECT_ROOT/requirements.txt"
    local python_exe="$PROJECT_ROOT/.venv/bin/python"
    local pip_exe="$PROJECT_ROOT/.venv/bin/pip"
    
    if [ ! -f "$requirements_file" ]; then
        log "ERROR" "requirements.txt file does not exist"
        return 1
    fi
    
    if [ ! -f "$python_exe" ]; then
        log "ERROR" "Python executable does not exist in virtual environment"
        return 1
    fi
    
    # Upgrade pip first
    if ! $pip_exe install --upgrade pip; then
        log "WARNING" "Failed to upgrade pip, continuing anyway"
    fi
    
    # Install requirements
    if ! $pip_exe install -r "$requirements_file"; then
        log "ERROR" "Failed to install dependencies"
        return 1
    fi
    
    log "SUCCESS" "Dependencies installed successfully"
    return 0
}

# Launch GUI tool
start_gui() {
    log "INFO" "Starting GUI interface..."
    
    # 优先使用跨平台GUI，如果不存在则使用原版GUI
    local gui_path="$PROJECT_ROOT/cross_platform_launcher_gui.py"
    if [ ! -f "$gui_path" ]; then
        gui_path="$PROJECT_ROOT/launcher_gui.py"
    fi
    
    local python_exe="$PROJECT_ROOT/.venv/bin/python"
    
    if [ ! -f "$gui_path" ]; then
        log "ERROR" "GUI interface file does not exist"
        return 1
    fi
    
    if [ ! -f "$python_exe" ]; then
        log "ERROR" "Python executable does not exist"
        return 1
    fi
    
    # Test Python environment
    if ! $python_exe -c "import sys; print('Python version:', sys.version); import tkinter; print('tkinter available')" 2>/dev/null; then
        log "ERROR" "Python environment test failed"
        return 1
    fi
    
    # Test GUI program imports
    if ! $python_exe -c "import sys; sys.path.append('$PROJECT_ROOT'); import launcher_gui; print('launcher_gui imported successfully')" 2>/dev/null; then
        log "ERROR" "GUI program import test failed"
        return 1
    fi
    
    # Launch GUI
    log "INFO" "Launching GUI interface..."
    cd "$PROJECT_ROOT"
    
    if $python_exe "$gui_path" > gui_output.log 2> gui_error.log & then
        local gui_pid=$!
        log "SUCCESS" "GUI interface launched successfully (PID: $gui_pid)"
        echo $gui_pid > "$PROJECT_ROOT/.gui_pid"
        return 0
    else
        log "ERROR" "Failed to launch GUI interface"
        if [ -f gui_error.log ]; then
            log "ERROR" "Error log: $(cat gui_error.log)"
        fi
        return 1
    fi
}

# Check environment
check_environment() {
    log "INFO" "Checking environment..."
    
    local venv_path="$PROJECT_ROOT/.venv"
    local python_exe="$PROJECT_ROOT/.venv/bin/python"
    local needs_setup=0
    
    if [ ! -d "$venv_path" ]; then
        log "WARNING" "Virtual environment does not exist"
        needs_setup=1
    elif [ ! -f "$python_exe" ]; then
        log "WARNING" "Python executable does not exist in virtual environment"
        needs_setup=1
    else
        # Check dependencies
        if ! $python_exe -c "import tkinter; import yaml; import requests; print('All dependencies OK')" 2>/dev/null; then
            log "WARNING" "Dependencies not installed or incomplete"
            needs_setup=1
        else
            log "SUCCESS" "All dependencies are available"
        fi
    fi
    
    return $needs_setup
}

# Enable auto-start on boot (macOS)
enable_autostart() {
    log "INFO" "Configuring auto-start on boot..."
    
    local plist_file="$HOME/Library/LaunchAgents/com.pubmed-literature-push.plist"
    local python_exe="$PROJECT_ROOT/.venv/bin/python"
    local main_program="$PROJECT_ROOT/main.py"
    
    if [ ! -f "$main_program" ]; then
        log "ERROR" "Main program file does not exist"
        return 1
    fi
    
    # Create LaunchAgent plist
    cat > "$plist_file" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.pubmed-literature-push</string>
    <key>ProgramArguments</key>
    <array>
        <string>$python_exe</string>
        <string>$main_program</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$PROJECT_ROOT</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$PROJECT_ROOT/logs/autostart.log</string>
    <key>StandardErrorPath</key>
    <string>$PROJECT_ROOT/logs/autostart_error.log</string>
</dict>
</plist>
EOF
    
    # Create logs directory
    mkdir -p "$PROJECT_ROOT/logs"
    
    # Load the LaunchAgent
    launchctl load "$plist_file"
    
    log "SUCCESS" "Auto-start configured successfully"
    log "INFO" "LaunchAgent plist created at: $plist_file"
    return 0
}

# Disable auto-start on boot (macOS)
disable_autostart() {
    log "INFO" "Removing auto-start configuration..."
    
    local plist_file="$HOME/Library/LaunchAgents/com.pubmed-literature-push.plist"
    
    if [ -f "$plist_file" ]; then
        launchctl unload "$plist_file"
        rm -f "$plist_file"
        log "SUCCESS" "Auto-start configuration removed successfully"
    else
        log "INFO" "Auto-start configuration does not exist"
    fi
    
    return 0
}

# Check background process
check_background_process() {
    local main_py="main.py"
    
    # Look for Python processes running main.py
    local pids=$(pgrep -f "python.*$main_py" 2>/dev/null)
    
    if [ -n "$pids" ]; then
        for pid in $pids; do
            local cmd=$(ps -p "$pid" -o command= 2>/dev/null)
            if [[ "$cmd" == *"$main_py"* ]]; then
                echo "$pid"
                return 0
            fi
        done
    fi
    
    return 1
}

# Start background program
start_background_program() {
    log "INFO" "Starting background program..."
    
    local main_program="$PROJECT_ROOT/main.py"
    local python_exe="$PROJECT_ROOT/.venv/bin/python"
    
    if [ ! -f "$main_program" ]; then
        log "ERROR" "Main program file does not exist"
        return 1
    fi
    
    if [ ! -f "$python_exe" ]; then
        log "ERROR" "Python executable does not exist"
        return 1
    fi
    
    # Check if already running
    local existing_pid=$(check_background_process)
    if [ -n "$existing_pid" ]; then
        log "INFO" "Background program is already running (PID: $existing_pid)"
        return 0
    fi
    
    # Start background program
    cd "$PROJECT_ROOT"
    if nohup "$python_exe" "$main_program" > background_output.log 2> background_error.log & then
        local bg_pid=$!
        log "SUCCESS" "Background program started successfully (PID: $bg_pid)"
        echo $bg_pid > "$PROJECT_ROOT/.background_pid"
        return 0
    else
        log "ERROR" "Failed to start background program"
        return 1
    fi
}

# Stop background program
stop_background_program() {
    log "INFO" "Stopping background program..."
    
    local existing_pid=$(check_background_process)
    
    if [ -n "$existing_pid" ]; then
        # Try graceful shutdown first
        kill "$existing_pid" 2>/dev/null
        
        # Wait for graceful shutdown
        for i in {1..10}; do
            if ! kill -0 "$existing_pid" 2>/dev/null; then
                log "SUCCESS" "Background program stopped gracefully (PID: $existing_pid)"
                return 0
            fi
            sleep 1
        done
        
        # Force kill if still running
        if kill -9 "$existing_pid" 2>/dev/null; then
            log "SUCCESS" "Background program stopped forcefully (PID: $existing_pid)"
            return 0
        else
            log "ERROR" "Failed to stop background program"
            return 1
        fi
    else
        log "INFO" "Background program is not running"
        return 0
    fi
}

# Restart background program
restart_background_program() {
    log "INFO" "Restarting background program..."
    
    local existing_pid=$(check_background_process)
    if [ -n "$existing_pid" ]; then
        log "INFO" "Stopping existing background program (PID: $existing_pid)..."
        stop_background_program
        sleep 2
    fi
    
    return start_background_program
}

# Run main program in foreground
run_main_program() {
    log "INFO" "Starting main program in foreground..."
    
    local main_program="$PROJECT_ROOT/main.py"
    local python_exe="$PROJECT_ROOT/.venv/bin/python"
    
    if [ ! -f "$main_program" ]; then
        log "ERROR" "Main program file does not exist"
        return 1
    fi
    
    if [ ! -f "$python_exe" ]; then
        log "ERROR" "Python executable does not exist"
        return 1
    fi
    
    log "INFO" "Starting main program..."
    log "INFO" "Press Ctrl+C to stop the program"
    
    cd "$PROJECT_ROOT"
    exec "$python_exe" "$main_program"
}

# Start config editor
start_config_editor() {
    log "INFO" "Starting configuration editor..."
    
    local config_editor="$PROJECT_ROOT/config_editor_gui.py"
    local python_exe="$PROJECT_ROOT/.venv/bin/python"
    
    if [ ! -f "$config_editor" ]; then
        log "ERROR" "Configuration editor file does not exist"
        return 1
    fi
    
    if [ ! -f "$python_exe" ]; then
        log "ERROR" "Python executable does not exist"
        return 1
    fi
    
    cd "$PROJECT_ROOT"
    exec "$python_exe" "$config_editor"
}

# Main function
main() {
    # Parse command line arguments
    local setup=0
    local force=0
    local action=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --setup)
                setup=1
                shift
                ;;
            --force)
                force=1
                shift
                ;;
            --action)
                action="$2"
                shift 2
                ;;
            --help)
                show_help
                return 0
                ;;
            *)
                log "ERROR" "Unknown option: $1"
                show_help
                return 1
                ;;
        esac
    done
    
    # Display header
    echo -e "${CYAN}===================================="
    echo -e "${CYAN}  PubMed Literature Push Launcher for macOS (Cross-Platform)"
    echo -e "${CYAN}====================================${NC}"
    echo ""
    echo -e "${YELLOW}Launch directory: $PROJECT_ROOT${NC}"
    
    # Check if GUI launcher exists (优先检查跨平台版本)
    local launcher_path="$PROJECT_ROOT/cross_platform_launcher_gui.py"
    local launcher_type="cross_platform_launcher_gui.py"
    
    if [ ! -f "$launcher_path" ]; then
        launcher_path="$PROJECT_ROOT/launcher_gui.py"
        launcher_type="launcher_gui.py"
    fi
    
    if [ ! -f "$launcher_path" ]; then
        echo -e "${RED}Error: No GUI launcher file found${NC}"
        echo -e "${RED}Please ensure this script is in the project root directory${NC}"
        read -p "Press Enter to exit"
        return 1
    fi
    
    echo -e "${GREEN}Found launcher file: $launcher_type${NC}"
    
    # Handle specific actions
    if [ -n "$action" ]; then
        case "$action" in
            "enable-autostart")
                enable_autostart
                read -p "Press Enter to exit"
                return 0
                ;;
            "disable-autostart")
                disable_autostart
                read -p "Press Enter to exit"
                return 0
                ;;
            "start")
                start_background_program
                read -p "Press Enter to exit"
                return 0
                ;;
            "stop")
                stop_background_program
                read -p "Press Enter to exit"
                return 0
                ;;
            "restart")
                restart_background_program
                read -p "Press Enter to exit"
                return 0
                ;;
            "run")
                run_main_program
                return 0
                ;;
            "config")
                start_config_editor
                return 0
                ;;
            "check")
                if check_environment; then
                    log "INFO" "Environment check completed - setup needed"
                else
                    log "SUCCESS" "Environment check completed - no setup needed"
                fi
                read -p "Press Enter to exit"
                return 0
                ;;
            *)
                echo -e "${RED}Unknown action: $action${NC}"
                echo -e "${YELLOW}Use --help to see available actions${NC}"
                read -p "Press Enter to exit"
                return 1
                ;;
        esac
    fi
    
    # Check basic environment
    if ! check_python; then
        read -p "Press Enter to exit"
        return 1
    fi
    
    # Check if environment setup is needed
    if check_environment; then
        local needs_setup=1
    else
        local needs_setup=0
    fi
    
    if [ "$setup" -eq 1 ] || [ "$force" -eq 1 ] || [ "$needs_setup" -eq 1 ]; then
        if [ "$setup" -eq 1 ] || [ "$force" -eq 1 ]; then
            log "INFO" "User requested environment setup, starting automatic configuration..."
        else
            log "INFO" "Environment needs setup, starting automatic configuration..."
        fi
        
        # Create virtual environment
        if ! create_virtualenv; then
            read -p "Press Enter to exit"
            return 1
        fi
        
        # Install dependencies
        if ! install_dependencies; then
            read -p "Press Enter to exit"
            return 1
        fi
        
        log "SUCCESS" "Environment setup completed!"
    else
        log "SUCCESS" "Environment check completed, no setup needed"
    fi
    
    # Launch GUI
    echo ""
    echo -e "${CYAN}Starting PubMed Literature Push launcher...${NC}"
    echo ""
    
    if start_gui; then
        log "SUCCESS" "Program launched successfully!"
    else
        log "ERROR" "Program launch failed!"
        read -p "Press Enter to exit"
        return 1
    fi
    
    return 0
}

# Execute main function
main "$@"