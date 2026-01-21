# Python Upgrade: Windows PowerShell 7 Commands

## 🪟 PowerShell 7 Virtual Environment Commands

### ❌ DON'T use these (they won't work in PowerShell):
```powershell
deactivate          # ❌ Not a PowerShell command
source venv/bin/activate   # ❌ Unix-style paths
```

### ✅ CORRECT PowerShell 7 Commands:

#### **1. Activate Virtual Environment:**
```powershell
# From your project directory
venv\Scripts\Activate.ps1
```

#### **2. Deactivate Virtual Environment:**
```powershell
# Simply type:
deactivate

# OR use the function (it works in PowerShell too):
deactivate
```

#### **3. Check Virtual Environment Status:**
```powershell
# Check if activated (will show (venv) in prompt)
$env:VIRTUAL_ENV

# Check Python path
which python
# OR
Get-Command python
```

## 🚀 Complete Python 3.12 Upgrade Process (Windows)

### Phase 1: Pre-Upgrade Backup
```powershell
# Backup current requirements
pip freeze > requirements_backup_3.11.txt

# Verify current setup
python --version  # Should show 3.11.9
pip list
```

### Phase 2: Upgrade Process
```powershell
# 1. Deactivate current venv (if active)
deactivate

# 2. Install Python 3.12 via your preferred method
# (winget, chocolatey, or manual installer)

# 3. Remove old venv (optional but recommended)
Remove-Item -Recurse -Force venv

# 4. Create new venv with Python 3.12
python3.12 -m venv venv

# 5. Activate new venv
venv\Scripts\Activate.ps1

# 6. Upgrade pip
python -m pip install --upgrade pip

# 7. Install requirements
pip install -r requirements.txt
```

### Phase 3: Post-Upgrade Testing
```powershell
# Verify Python version
python --version  # Should show 3.12.x

# Test core imports
python -c "import psycopg2, yfinance, ib_insync, pandas; print('Imports OK')"

# Test database interface
python db.py health

# Test main application
python main.py --mode test --exchanges NSE
```

## 🎯 Alternative: Use Windows Terminal

If you prefer a more Unix-like experience:

1. **Install Windows Terminal** from Microsoft Store
2. **Use PowerShell profile** or switch to Command Prompt
3. **Use Git Bash** if you have Git for Windows installed

### Windows Terminal Setup:
```json
// Add to Windows Terminal settings.json
{
    "profiles": {
        "defaults": {
            "fontFace": "Cascadia Code"
        },
        "list": [
            {
                "guid": "{574e775e-4f2a-5b96-ac1e-a2962a402336}",
                "hidden": false,
                "name": "PowerShell 7",
                "source": "Windows.Terminal.PowershellCore"
            }
        ]
    }
}
```

## 🔧 Troubleshooting PowerShell Issues

### If `venv\Scripts\Activate.ps1` doesn't work:
```powershell
# Check execution policy
Get-ExecutionPolicy

# Allow script execution (if needed)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Try again
venv\Scripts\Activate.ps1
```

### If Python 3.12 isn't found:
```powershell
# Check available Python versions
where python
where python3.12

# Update PATH or use full path
C:\Path\To\Python312\python.exe -m venv venv
```

### Rollback Plan:
```powershell
# If issues occur, switch back to Python 3.11
# 1. Remove problematic venv
Remove-Item -Recurse -Force venv

# 2. Recreate with Python 3.11
python -m venv venv  # Uses system default (3.11)
venv\Scripts\Activate.ps1
pip install -r requirements_backup_3.11.txt
```

## ✅ Expected Results

After successful upgrade:
```
PS C:\Dev\Global Market Scanner\global-macro-scanner> python --version
Python 3.12.x

PS C:\Dev\Global Market Scanner\global-macro-scanner> python db.py health
✅ Database connection pool created (size: 5)
{
  "timestamp": "2026-01-19T...",
  "connection": "ok",
  "tables": {...},
  "issues": []
}
```

**You can absolutely use PowerShell 7!** Just use the correct Windows paths and commands. 🚀