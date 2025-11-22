# ProcOrg Web UI Guide

## Accessing the Web UI

1. **Start the server:**
   ```bash
   cd /Users/ploskon/devel/procorg
   ./start-web.sh
   ```

2. **Open in browser:**
   - Primary URL: http://localhost:9777
   - Fallback URL: http://localhost:9778 (if 9777 is in use)

## Web UI Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ProcOrg                                                     │
│ Process Orchestration and Management                       │
├─────────────────────────────────────────────────────────────┤
│ Scheduler: Running (3 scheduled) [Stop Scheduler]          │
├─────────────────────────────────────────────────────────────┤
│ [+ Add Process]                                             │
├─────────────────────────────────────────────────────────────┤
│ ┌───────────────┐  ┌───────────────┐  ┌───────────────┐   │
│ │ example-process│  │scheduled-proc │  │ error-process │   │
│ │ Status: idle   │  │ Status: idle  │  │ Status: idle  │   │
│ │                │  │               │  │               │   │
│ │ Script: /path  │  │ Cron: */10 *  │  │ Script: /path │   │
│ │                │  │               │  │               │   │
│ │ [Run] [Stop]   │  │ [Run] [Stop]  │  │ [Run] [Stop]  │   │
│ │ [Logs] [Delete]│  │ [Logs][Delete]│  │ [Logs][Delete]│   │
│ └───────────────┘  └───────────────┘  └───────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Features Already Built In

### 1. Process Cards
Each process appears as a card with:
- **Process Name** (top left)
- **Status Badge** (top right) - color-coded:
  - 🟢 Green: running
  - ⚪ Gray: idle
  - 🔴 Red: failed

### 2. Action Buttons
Each card has 4 buttons:

#### **Run Button**
- Click to start the process
- Disabled while running
- Shows "Running..." when active

#### **Stop Button**
- Click to terminate a running process
- Disabled when not running
- Uses graceful termination

#### **Logs Button**
- Opens log viewer panel
- Real-time updates
- Switch between stdout/stderr

#### **Delete Button**
- Remove the process permanently
- Confirmation dialog prevents accidents
- Disabled while process is running

### 3. Add Process Button
- Green "+ Add Process" button at top
- Opens registration form
- Fields:
  - Process name (required)
  - Script path (required)
  - Cron expression (optional)
  - Description (optional)

### 4. Log Viewer
When you click "Logs":
- Panel slides open at bottom
- Shows real-time output
- Buttons to switch stdout ↔ stderr
- Auto-scrolls to latest output

### 5. Scheduler Control
Top bar shows:
- Scheduler status (running/stopped)
- Number of scheduled processes
- Start/Stop button

## Example Workflow in Web UI

### Running a Process:
1. Open http://localhost:9777
2. Find your process card (e.g., "my-script")
3. Click the **[Run]** button
4. Status changes to "running"
5. Click **[Logs]** to see output in real-time
6. Process completes automatically

### Viewing Logs:
1. Click **[Logs]** button on any process card
2. Log panel opens at bottom showing stdout
3. Click **[stderr]** button to see errors
4. Click **[stdout]** to switch back
5. Click **[Close]** to hide log panel

### Adding a New Process:
1. Click **[+ Add Process]** button (top)
2. Fill in the form:
   - Name: `backup-job`
   - Path: `/Users/you/scripts/backup.sh`
   - Cron: `0 2 * * *` (optional, for 2 AM daily)
   - Description: `Daily database backup`
3. Click **[Register Process]**
4. New process card appears immediately

### Deleting a Process:
1. Make sure process is not running
2. Click **[Delete]** button
3. Confirm in dialog
4. Process card disappears

## Troubleshooting

### "No processes showing"

**Check API connection:**
```bash
curl http://localhost:9777/api/processes
```

**Should return JSON with your processes**

**If empty**, check CLI:
```bash
source venv/bin/activate
procorg list
```

**If CLI shows processes but web doesn't:**
- Hard refresh browser (Cmd+Shift+R or Ctrl+Shift+F5)
- Check browser console for errors (F12)
- Restart web server: `pkill -9 python3 && ./start-web.sh`

### "Can't connect to server"

**Check if server is running:**
```bash
lsof -i :9777
```

**Start server:**
```bash
./start-web.sh
```

### "Process won't run"

**Check script path is absolute:**
```bash
# Good
/Users/ploskon/scripts/backup.sh

# Bad
./backup.sh
scripts/backup.sh
```

**Verify script is executable:**
```bash
chmod +x /path/to/your/script.sh
```

## Live Demo

The server is currently running at: **http://localhost:9777**

You should see 4 processes:
1. example-process
2. scheduled-process (runs every 10 minutes)
3. error-process
4. my-script

Try clicking **[Run]** on any of them, then **[Logs]** to see the output!
