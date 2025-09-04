# PubMed Literature Push Integrated Launcher
# Integrates functionality from setup.ps1 and start_launcher.ps1
# Supports environment checking, automatic setup and one-click launch

param(
    [switch]$Setup,
    [switch]$Force,
    [string]$Action,
    [switch]$Help
)

# Set console encoding to UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# Show help information
function Show-Help {
    Write-Host "====================================" -ForegroundColor Cyan
    Write-Host "  PubMed Literature Push Integrated Launcher (Cross-Platform)" -ForegroundColor Cyan
    Write-Host "====================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage:" -ForegroundColor Yellow
    Write-Host "  .\launcher.ps1 [Options]" -ForegroundColor White
    Write-Host ""
    Write-Host "Options:" -ForegroundColor Yellow
    Write-Host "  -Setup      Run complete environment setup" -ForegroundColor White
    Write-Host "  -Force      Force environment re-setup" -ForegroundColor White
    Write-Host "  -Action     Execute specific action" -ForegroundColor White
    Write-Host "              Available actions: start, stop, restart, run, config, check" -ForegroundColor White
    Write-Host "              enable-autostart, disable-autostart" -ForegroundColor White
    Write-Host "  -Help       Show this help information" -ForegroundColor White
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Yellow
    Write-Host "  .\launcher.ps1                    # Quick launch" -ForegroundColor White
    Write-Host "  .\launcher.ps1 -Setup             # Complete environment setup" -ForegroundColor White
    Write-Host "  .\launcher.ps1 -Action start      # Start background service" -ForegroundColor White
    Write-Host "  .\launcher.ps1 -Action run        # Run main program" -ForegroundColor White
    Write-Host ""
}

# Get script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectRoot = $ScriptDir

# Log function
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $color = switch ($Level) {
        "INFO" { "White" }
        "SUCCESS" { "Green" }
        "WARNING" { "Yellow" }
        "ERROR" { "Red" }
        default { "White" }
    }
    Write-Host "[$timestamp] [$Level] $Message" -ForegroundColor $color
}

# Check PowerShell execution policy
function Test-ExecutionPolicy {
    Write-Log "Checking PowerShell execution policy..."
    $policy = Get-ExecutionPolicy
    if ($policy -eq "Restricted") {
        Write-Log "PowerShell execution policy is Restricted, needs modification" "WARNING"
        Write-Log "Please run PowerShell as Administrator and execute: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" "WARNING"
        return $false
    }
    Write-Log "PowerShell execution policy check passed: $policy" "SUCCESS"
    return $true
}

# Check Python installation
function Test-Python {
    Write-Log "Checking Python installation..."
    try {
        $pythonVersion = python --version 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Log "Python version: $pythonVersion" "SUCCESS"
            return $true
        }
    } catch {
        # Ignore exception
    }
    
    Write-Log "Python not found, please install Python 3.8+ and add to PATH" "ERROR"
    return $false
}

# Create virtual environment
function New-VirtualEnvironment {
    Write-Log "Creating Python virtual environment..."
    
    $venvPath = Join-Path $ProjectRoot ".venv"
    
    if (Test-Path $venvPath) {
        Write-Log "Virtual environment already exists, skipping creation" "INFO"
        return $true
    }
    
    try {
        python -m venv .venv
        if ($LASTEXITCODE -eq 0) {
            Write-Log "Virtual environment created successfully" "SUCCESS"
            return $true
        } else {
            Write-Log "Failed to create virtual environment" "ERROR"
            return $false
        }
    } catch {
        Write-Log "Virtual environment creation exception: $($_.Exception.Message)" "ERROR"
        return $false
    }
}

# Install dependencies
function Install-Dependencies {
    Write-Log "Installing Python dependencies..."
    
    $requirementsFile = Join-Path $ProjectRoot "requirements.txt"
    $pythonExe = Join-Path $ProjectRoot ".venv"
    $pythonExe = Join-Path $pythonExe "Scripts"
    $pythonExe = Join-Path $pythonExe "python.exe"
    
    Write-Log "DEBUG: Requirements file = $requirementsFile" "INFO"
    Write-Log "DEBUG: Python executable = $pythonExe" "INFO"
    Write-Log "DEBUG: Requirements file exists = $(Test-Path $requirementsFile)" "INFO"
    Write-Log "DEBUG: Python executable exists = $(Test-Path $pythonExe)" "INFO"
    
    if (-not (Test-Path $requirementsFile)) {
        Write-Log "requirements.txt file does not exist" "ERROR"
        return $false
    }
    
    try {
        Write-Log "DEBUG: Upgrading pip..." "INFO"
        & $pythonExe -m pip install --upgrade pip
        if ($LASTEXITCODE -ne 0) {
            Write-Log "DEBUG: pip upgrade failed with exit code: $LASTEXITCODE" "WARNING"
        } else {
            Write-Log "DEBUG: pip upgrade successful" "SUCCESS"
        }
        
        Write-Log "DEBUG: Installing requirements from $requirementsFile..." "INFO"
        $installOutput = & $pythonExe -m pip install -r $requirementsFile 2>&1
        Write-Log "DEBUG: Installation output: $installOutput" "INFO"
        
        if ($LASTEXITCODE -eq 0) {
            Write-Log "Dependencies installed successfully" "SUCCESS"
            return $true
        } else {
            Write-Log "Failed to install dependencies (exit code: $LASTEXITCODE)" "ERROR"
            Write-Log "Installation output: $installOutput" "ERROR"
            return $false
        }
    } catch {
        Write-Log "Dependencies installation exception: $($_.Exception.Message)" "ERROR"
        Write-Log "Exception details: $($_.Exception | Out-String)" "ERROR"
        return $false
    }
}

# Launch GUI tool
function Start-GUI {
    Write-Log "Starting GUI interface..."
    
    # 优先使用跨平台GUI，如果不存在则使用原版GUI
    $guiPath = Join-Path $ProjectRoot "cross_platform_launcher_gui.py"
    if (-not (Test-Path $guiPath)) {
        $guiPath = Join-Path $ProjectRoot "launcher_gui.py"
    }
    
    $venvPath = Join-Path $ProjectRoot ".venv"
    $scriptsPath = Join-Path $venvPath "Scripts"
    $pythonExe = Join-Path $scriptsPath "python.exe"
    $pythonwExe = Join-Path $scriptsPath "pythonw.exe"
    
    # 添加详细日志来验证假设
    Write-Log "DEBUG: ProjectRoot = $ProjectRoot" "INFO"
    Write-Log "DEBUG: GUI path = $guiPath" "INFO"
    Write-Log "DEBUG: Venv path = $venvPath" "INFO"
    Write-Log "DEBUG: Scripts path = $scriptsPath" "INFO"
    Write-Log "DEBUG: Python exe = $pythonExe" "INFO"
    Write-Log "DEBUG: Pythonw exe = $pythonwExe" "INFO"
    
    # 检查文件和路径是否存在
    Write-Log "DEBUG: GUI file exists = $(Test-Path $guiPath)" "INFO"
    Write-Log "DEBUG: Venv directory exists = $(Test-Path $venvPath)" "INFO"
    Write-Log "DEBUG: Scripts directory exists = $(Test-Path $scriptsPath)" "INFO"
    Write-Log "DEBUG: Python exe exists = $(Test-Path $pythonExe)" "INFO"
    Write-Log "DEBUG: Pythonw exe exists = $(Test-Path $pythonwExe)" "INFO"
    
    if (-not (Test-Path $guiPath)) {
        Write-Log "GUI interface file does not exist" "ERROR"
        return $false
    }
    
    # Prefer pythonw.exe to avoid CMD window
    $pythonExecutable = if (Test-Path $pythonwExe) { $pythonwExe } else { $pythonExe }
    
    if (-not (Test-Path $pythonExecutable)) {
        Write-Log "Python executable does not exist" "ERROR"
        return $false
    }
    
    # 测试 Python 是否可以正常工作，特别是 tkinter
    try {
        Write-Log "Testing Python environment..." "INFO"
        $testResult = & $pythonExecutable -c "import sys; print('Python version:', sys.version); import tkinter; print('tkinter available')" 2>&1
        Write-Log "Python test result: $testResult" "INFO"
        
        # 测试 GUI 程序的导入
        Write-Log "Testing GUI program imports..." "INFO"
        $importTest = & $pythonExecutable -c "import sys; sys.path.append('$ProjectRoot'); import launcher_gui; print('launcher_gui imported successfully')" 2>&1
        Write-Log "Import test result: $importTest" "INFO"
        
        # 测试运行 GUI 程序但不显示界面
        Write-Log "Testing GUI program execution..." "INFO"
        $executionTest = & $pythonExecutable -c "import sys; sys.path.append('$ProjectRoot'); import launcher_gui; print('GUI program can be executed')" 2>&1
        Write-Log "Execution test result: $executionTest" "INFO"
    } catch {
        Write-Log "Python environment test failed: $($_.Exception.Message)" "ERROR"
        return $false
    }
    
    try {
        Write-Log "Launching GUI interface..." "INFO"
        Write-Log "Using executable: $pythonExecutable" "INFO"
        Write-Log "Arguments: $guiPath" "INFO"
        Write-Log "Working directory: $ProjectRoot" "INFO"
        
        # Always use pythonw.exe if available, otherwise python.exe
        if ($pythonExecutable -eq $pythonwExe) {
            # Use pythonw.exe for normal startup
            Write-Log "Starting with pythonw.exe (no console window)" "INFO"
            $process = Start-Process -FilePath $pythonExecutable -ArgumentList "`"$guiPath`"" -WorkingDirectory $ProjectRoot -PassThru -RedirectStandardOutput "pythonw_output.log" -RedirectStandardError "pythonw_error.log"
            Write-Log "Process started with ID: $($process.Id)" "INFO"
            Write-Log "Output redirected to pythonw_output.log" "INFO"
            Write-Log "Errors redirected to pythonw_error.log" "INFO"
        } else {
            # Use python.exe with no window
            Write-Log "Starting with python.exe (hidden console window)" "INFO"
            $process = Start-Process -FilePath $pythonExecutable -ArgumentList "`"$guiPath`"" -WorkingDirectory $ProjectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput "python_output.log" -RedirectStandardError "python_error.log"
            Write-Log "Process started with ID: $($process.Id)" "INFO"
            Write-Log "Output redirected to python_output.log" "INFO"
            Write-Log "Errors redirected to python_error.log" "INFO"
        }
        
        # Give the process a moment to start
        Start-Sleep -Seconds 2
        
        # 检查进程是否仍在运行
        $processCheck = Get-Process -Id $process.Id -ErrorAction SilentlyContinue
        if ($processCheck) {
            Write-Log "Process is still running after 2 seconds" "INFO"
            Write-Log "GUI interface launched successfully" "SUCCESS"
            return $true
        } else {
            Write-Log "Process has exited or failed to start" "WARNING"
            
            # 读取输出和错误日志
            $outputFile = if ($pythonExecutable -eq $pythonwExe) { "pythonw_output.log" } else { "python_output.log" }
            $errorFile = if ($pythonExecutable -eq $pythonwExe) { "pythonw_error.log" } else { "python_error.log" }
            
            if (Test-Path $outputFile) {
                $outputContent = Get-Content $outputFile -Raw
                Write-Log "Process output: $outputContent" "INFO"
            }
            
            if (Test-Path $errorFile) {
                $errorContent = Get-Content $errorFile -Raw
                Write-Log "Process error: $errorContent" "ERROR"
            }
            
            # 尝试使用 python.exe 而不是 pythonw.exe
            if ($pythonExecutable -eq $pythonwExe) {
                Write-Log "Trying with python.exe instead of pythonw.exe..." "INFO"
                $process2 = Start-Process -FilePath $pythonExe -ArgumentList "`"$guiPath`"" -WorkingDirectory $ProjectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput "python_fallback_output.log" -RedirectStandardError "python_fallback_error.log"
                Write-Log "Fallback process started with ID: $($process2.Id)" "INFO"
                
                Start-Sleep -Seconds 2
                
                $processCheck2 = Get-Process -Id $process2.Id -ErrorAction SilentlyContinue
                if ($processCheck2) {
                    Write-Log "Fallback process is still running after 2 seconds" "INFO"
                    Write-Log "GUI interface launched successfully with fallback" "SUCCESS"
                    return $true
                } else {
                    Write-Log "Fallback process has also exited or failed to start" "WARNING"
                    
                    if (Test-Path "python_fallback_output.log") {
                        $fallbackOutput = Get-Content "python_fallback_output.log" -Raw
                        Write-Log "Fallback process output: $fallbackOutput" "INFO"
                    }
                    
                    if (Test-Path "python_fallback_error.log") {
                        $fallbackError = Get-Content "python_fallback_error.log" -Raw
                        Write-Log "Fallback process error: $fallbackError" "ERROR"
                    }
                    
                    Write-Log "GUI interface launch failed" "ERROR"
                    return $false
                }
            } else {
                Write-Log "GUI interface launch failed" "ERROR"
                return $false
            }
        }
    } catch {
        Write-Log "Failed to launch GUI interface: $($_.Exception.Message)" "ERROR"
        Write-Log "Exception details: $($_.Exception | Out-String)" "ERROR"
        return $false
    }
}

# Check environment
function Test-Environment {
    $venvPath = Join-Path $ProjectRoot ".venv"
    $scriptsPath = Join-Path $venvPath "Scripts"
    $pythonExe = Join-Path $scriptsPath "python.exe"
    
    Write-Log "DEBUG: Environment check started" "INFO"
    Write-Log "DEBUG: VenvPath = $venvPath" "INFO"
    Write-Log "DEBUG: ScriptsPath = $scriptsPath" "INFO"
    Write-Log "DEBUG: PythonExe = $pythonExe" "INFO"
    
    $needsSetup = $false
    
    if (-not (Test-Path $venvPath)) {
        Write-Log "DEBUG: Virtual environment directory does not exist" "WARNING"
        Write-Log "Virtual environment does not exist, needs creation" "WARNING"
        $needsSetup = $true
    } else {
        Write-Log "DEBUG: Virtual environment directory exists" "INFO"
        
        if (-not (Test-Path $scriptsPath)) {
            Write-Log "DEBUG: Scripts directory does not exist" "WARNING"
            Write-Log "Virtual environment Scripts directory does not exist" "WARNING"
            $needsSetup = $true
        } else {
            Write-Log "DEBUG: Scripts directory exists" "INFO"
            
            if (-not (Test-Path $pythonExe)) {
                Write-Log "DEBUG: Python executable does not exist" "WARNING"
                Write-Log "Virtual environment Python executable does not exist" "WARNING"
                $needsSetup = $true
            } else {
                Write-Log "DEBUG: Python executable exists" "INFO"
                
                # Check if dependencies are installed
                try {
                    Write-Log "DEBUG: Testing dependencies import..." "INFO"
                    $result = & $pythonExe -c "import sys; print('Python path:', sys.executable); import tkinter; print('tkinter OK'); import yaml; print('yaml OK'); import requests; print('requests OK')" 2>&1
                    Write-Log "DEBUG: Dependency test result: $result" "INFO"
                    
                    if ($LASTEXITCODE -ne 0) {
                        Write-Log "DEBUG: Dependency test failed with exit code: $LASTEXITCODE" "WARNING"
                        Write-Log "Dependencies not installed or incomplete, need reinstallation" "WARNING"
                        $needsSetup = $true
                    } else {
                        Write-Log "DEBUG: All dependencies are available" "SUCCESS"
                    }
                } catch {
                    Write-Log "DEBUG: Dependency check exception: $($_.Exception.Message)" "WARNING"
                    Write-Log "Dependency check exception, need reinstallation" "WARNING"
                    $needsSetup = $true
                }
            }
        }
    }
    
    Write-Log "DEBUG: Environment check completed, needsSetup = $needsSetup" "INFO"
    return $needsSetup
}

# Enable auto-start on boot
function Enable-AutoStart {
    Write-Log "Configuring auto-start on boot with 10-minute delay..."
    
    $startupPath = [Environment]::GetFolderPath("Startup")
    $vbsFile = Join-Path $startupPath "PubMedLiteraturePush.vbs"
    $venvPath = Join-Path $ProjectRoot ".venv"
    $scriptsPath = Join-Path $venvPath "Scripts"
    $pythonExe = Join-Path $scriptsPath "python.exe"
    $mainProgramPath = Join-Path $ProjectRoot "main.py"
    
    try {
        # Remove old batch file if exists
        $batchFile = Join-Path $startupPath "PubMedLiteraturePush.bat"
        if (Test-Path $batchFile) {
            Remove-Item $batchFile -Force
            Write-Log "Removed old batch file" "INFO"
        }
        
        # Create VBScript file for completely hidden startup with 10-minute delay
        $vbsContent = "Set WshShell = CreateObject(`"WScript.Shell`")`r`n"
        $vbsContent += "WScript.Sleep 600000 ' Wait 10 minutes (600000 milliseconds)`r`n"
        $vbsContent += "WshShell.Run `"$pythonExe $mainProgramPath`", 0, False"
        
        # Create VBScript file
        Set-Content -Path $vbsFile -Value $vbsContent -Encoding ASCII
        
        Write-Log "Auto-start configured successfully with 10-minute delay" "SUCCESS"
        Write-Log "VBScript file created at: $vbsFile" "INFO"
        Write-Log "Program will wait 10 minutes before starting after boot" "INFO"
        return $true
    } catch {
        Write-Log "Failed to configure auto-start: $($_.Exception.Message)" "ERROR"
        return $false
    }
}

# Remove auto-start configuration
function Disable-AutoStart {
    Write-Log "Removing auto-start configuration..."
    
    $startupPath = [Environment]::GetFolderPath("Startup")
    $batchFile = Join-Path $startupPath "PubMedLiteraturePush.bat"
    $vbsFile = Join-Path $startupPath "PubMedLiteraturePush.vbs"
    
    try {
        $removedFiles = @()
        
        # Remove batch file
        if (Test-Path $batchFile) {
            Remove-Item $batchFile -Force
            $removedFiles += "Batch file"
            Write-Log "Batch auto-start file removed" "SUCCESS"
        }
        
        # Clean up old VBS file if exists
        if (Test-Path $vbsFile) {
            Remove-Item $vbsFile -Force
            $removedFiles += "Legacy VBS script"
            Write-Log "Legacy VBS auto-start script removed" "SUCCESS"
        }
        
        if ($removedFiles.Count -gt 0) {
            Write-Log "Auto-start configuration removed successfully ($($removedFiles -join ', '))" "SUCCESS"
        } else {
            Write-Log "Auto-start configuration does not exist" "INFO"
        }
        return $true
    } catch {
        Write-Log "Failed to remove auto-start configuration: $($_.Exception.Message)" "ERROR"
        return $false
    }
}

# Check background process
function Test-BackgroundProcess {
    $processName = "python"
    $mainPy = "main.py"
    
    try {
        $processes = Get-Process -Name $processName -ErrorAction SilentlyContinue
        foreach ($proc in $processes) {
            if ($proc.ProcessName -eq $processName) {
                $commandLine = (Get-CimInstance Win32_Process -Filter "ProcessId = $($proc.Id)").CommandLine
                if ($commandLine -and $commandLine.Contains($mainPy)) {
                    return @{
                        IsRunning = $true
                        ProcessId = $proc.Id
                        CommandLine = $commandLine
                    }
                }
            }
        }
        return @{ IsRunning = $false }
    } catch {
        Write-Log "Failed to check background process: $($_.Exception.Message)" "ERROR"
        return @{ IsRunning = $false }
    }
}

# Start background program
function Start-BackgroundProgram {
    Write-Log "Starting background program..."
    
    $mainProgramPath = Join-Path $ProjectRoot "main.py"
    $venvPath = Join-Path $ProjectRoot ".venv"
    $scriptsPath = Join-Path $venvPath "Scripts"
    $pythonExe = Join-Path $scriptsPath "python.exe"
    
    if (-not (Test-Path $mainProgramPath)) {
        Write-Log "Main program file does not exist" "ERROR"
        return $false
    }
    
    if (-not (Test-Path $pythonExe)) {
        Write-Log "Python executable does not exist" "ERROR"
        return $false
    }
    
    # Check if already running
    $processStatus = Test-BackgroundProcess
    if ($processStatus.IsRunning) {
        Write-Log "Background program is already running (PID: $($processStatus.ProcessId))" "INFO"
        return $true
    }
    
    try {
        Write-Log "Starting background program..." "INFO"
        $process = Start-Process -FilePath $pythonExe -ArgumentList $mainProgramPath -WorkingDirectory $ProjectRoot -WindowStyle Hidden -PassThru
        Write-Log "Background program started successfully (PID: $($process.Id))" "SUCCESS"
        return $true
    } catch {
        Write-Log "Failed to start background program: $($_.Exception.Message)" "ERROR"
        return $false
    }
}

# Stop background program
function Stop-BackgroundProgram {
    Write-Log "Stopping background program..."
    
    $processStatus = Test-BackgroundProcess
    $stoppedBySignal = $false
    
    # First try to stop using signal file (for pythonw.exe)
    $stopFile = Join-Path $ProjectRoot ".stop_signal"
    if (Test-Path $stopFile) {
        Remove-Item $stopFile -Force
    }
    
    # Create stop signal file
    try {
        New-Item -Path $stopFile -ItemType File -Force | Out-Null
        Write-Log "Created stop signal file for graceful shutdown" "INFO"
        
        # Wait for program to exit gracefully
        for ($i = 0; $i -lt 10; $i++) {
            Start-Sleep -Seconds 1
            $newStatus = Test-BackgroundProcess
            if (-not $newStatus.IsRunning) {
                $stoppedBySignal = $true
                break
            }
        }
        
        # Clean up signal file
        if (Test-Path $stopFile) {
            Remove-Item $stopFile -Force
        }
    } catch {
        Write-Log "Failed to create stop signal file: $($_.Exception.Message)" "WARNING"
    }
    
    if ($stoppedBySignal) {
        Write-Log "Background program stopped gracefully via signal file" "SUCCESS"
        return $true
    }
    
    # If signal file method failed, try force terminate process
    if ($processStatus.IsRunning) {
        try {
            Stop-Process -Id $processStatus.ProcessId -Force
            Write-Log "Background program stopped forcefully (PID: $($processStatus.ProcessId))" "SUCCESS"
            return $true
        } catch {
            Write-Log "Failed to stop background program: $($_.Exception.Message)" "ERROR"
            return $false
        }
    } else {
        Write-Log "Background program is not running" "INFO"
        return $true
    }
}

# Restart background program
function Restart-BackgroundProgram {
    Write-Log "Restarting background program..."
    
    $processStatus = Test-BackgroundProcess
    if ($processStatus.IsRunning) {
        Write-Log "Stopping existing background program (PID: $($processStatus.ProcessId))..."
        Stop-BackgroundProgram | Out-Null
        Start-Sleep -Seconds 2
    }
    
    return Start-BackgroundProgram
}

# Run main program in foreground
function Start-MainProgram {
    Write-Log "Starting main program in foreground..."
    
    $mainProgramPath = Join-Path $ProjectRoot "main.py"
    $venvPath = Join-Path $ProjectRoot ".venv"
    $scriptsPath = Join-Path $venvPath "Scripts"
    $pythonExe = Join-Path $scriptsPath "python.exe"
    
    if (-not (Test-Path $mainProgramPath)) {
        Write-Log "Main program file does not exist" "ERROR"
        return $false
    }
    
    if (-not (Test-Path $pythonExe)) {
        Write-Log "Python executable does not exist" "ERROR"
        return $false
    }
    
    try {
        Write-Log "Starting main program..." "INFO"
        Write-Log "Press Ctrl+C to stop the program" "INFO"
        & $pythonExe $mainProgramPath
        return $true
    } catch {
        Write-Log "Failed to start main program: $($_.Exception.Message)" "ERROR"
        return $false
    }
}

# Start config editor
function Start-ConfigEditor {
    Write-Log "Starting configuration editor..."
    
    $configEditorPath = Join-Path $ProjectRoot "config_editor_gui.py"
    $venvPath = Join-Path $ProjectRoot ".venv"
    $scriptsPath = Join-Path $venvPath "Scripts"
    $pythonExe = Join-Path $scriptsPath "python.exe"
    
    if ((Test-Path $configEditorPath) -and (Test-Path $pythonExe)) {
        & $pythonExe $configEditorPath
        return $true
    } else {
        Write-Log "Configuration editor or Python executable not found" "ERROR"
        return $false
    }
}

# Main program
function Main {
    # Show help if requested
    if ($Help) {
        Show-Help
        return
    }
    
    # Display header
    Write-Host "====================================" -ForegroundColor Cyan
    Write-Host "  PubMed Literature Push Integrated Launcher" -ForegroundColor Cyan
    Write-Host "====================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Launch directory: $ProjectRoot" -ForegroundColor Yellow
    
    # Check if GUI launcher exists (优先检查跨平台版本)
    $LauncherPath = Join-Path $ProjectRoot "cross_platform_launcher_gui.py"
    $LauncherType = "cross_platform_launcher_gui.py"
    
    if (-not (Test-Path $LauncherPath)) {
        $LauncherPath = Join-Path $ProjectRoot "launcher_gui.py"
        $LauncherType = "launcher_gui.py"
    }
    
    if (Test-Path $LauncherPath) {
        Write-Host "Found launcher file: $LauncherType" -ForegroundColor Green
    } else {
        Write-Host "Error: No GUI launcher file found" -ForegroundColor Red
        Write-Host "Please ensure this script is in the project root directory" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
    
    # Note: setup.ps1 is no longer required as its functionality is integrated into this script
    Write-Host "Note: setup.ps1 functionality is integrated into this launcher" -ForegroundColor Green
    
    # Handle specific actions
    if ($Action) {
        switch ($Action.ToLower()) {
            "enable-autostart" { 
                Enable-AutoStart
                Read-Host "Press Enter to exit"
                return
            }
            "disable-autostart" { 
                Disable-AutoStart
                Read-Host "Press Enter to exit"
                return
            }
            "start" { 
                Start-BackgroundProgram
                Read-Host "Press Enter to exit"
                return
            }
            "stop" { 
                Stop-BackgroundProgram
                Read-Host "Press Enter to exit"
                return
            }
            "restart" { 
                Restart-BackgroundProgram
                Read-Host "Press Enter to exit"
                return
            }
            "run" { 
                Start-MainProgram
                Read-Host "Press Enter to exit"
                return
            }
            "config" { 
                Start-ConfigEditor
                Read-Host "Press Enter to exit"
                return
            }
            "check" {
                Test-Environment | Out-Null
                Write-Log "Environment check completed" "INFO"
                Read-Host "Press Enter to exit"
                return
            }
            default {
                Write-Host "Unknown action: $Action" -ForegroundColor Red
                Write-Host "Use -Help to see available actions" -ForegroundColor Yellow
                Read-Host "Press Enter to exit"
                return
            }
        }
    }
    
    # Check basic environment
    if (-not (Test-ExecutionPolicy)) {
        Read-Host "Press Enter to exit"
        return
    }
    
    if (-not (Test-Python)) {
        Read-Host "Press Enter to exit"
        return
    }
    
    # Check if environment setup is needed
    $needsSetup = Test-Environment
    
    if ($Setup -or $Force -or $needsSetup) {
        if ($Setup -or $Force) {
            Write-Log "User requested environment setup, starting automatic configuration..." "INFO"
        } else {
            Write-Log "Environment needs setup, starting automatic configuration..." "INFO"
        }
        
        # Create virtual environment
        if (-not (New-VirtualEnvironment)) {
            Read-Host "Press Enter to exit"
            return
        }
        
        # Install dependencies
        if (-not (Install-Dependencies)) {
            Read-Host "Press Enter to exit"
            return
        }
        
        Write-Log "Environment setup completed!" "SUCCESS"
    } else {
        Write-Log "Environment check completed, no setup needed" "SUCCESS"
    }
    
    # Launch GUI
    Write-Host ""
    Write-Host "Starting PubMed Literature Push launcher..." -ForegroundColor Cyan
    Write-Host ""
    
    if (Start-GUI) {
        Write-Log "Program launched successfully!" "SUCCESS"
    } else {
        Write-Log "Program launch failed!" "ERROR"
        Read-Host "Press Enter to exit"
    }
}

# Execute main program
Main