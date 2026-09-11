# Conflict Warning Dashboard - UI Guide

## Overview

An interactive web-based dashboard that visualizes concurrent developer activity, file changes, and conflict warnings in real-time.

**Live URL:** Open `ui_dashboard.html` in a browser to interact with the dashboard.

## Features

### 1. **Active Files Panel** 📁
Shows all files being modified with:
- **Developer Tags:** Color-coded tags showing which developers are working on each file
- **Region Information:** Specific functions/classes being edited (if specified)
- **Risk Level:** Visual indicator of conflict risk (LOW/MEDIUM/HIGH)

### 2. **Active Developers Panel** 👨‍💻
Displays each active developer with:
- **Gradient Cards:** Unique color for each developer
- **Files List:** Which files they're currently working on
- **Activity Count:** Number of changes they've made
- **Activity Age:** How long ago they last worked

### 3. **Conflict Warnings Panel** ⚠️
Real-time conflict detection with:
- **Risk Level Badges:** Color-coded (Red = HIGH, Orange = MEDIUM, Green = LOW)
- **Conflict Details:** Shows which developers have overlapping changes
- **Intent Description:** Why each developer is making their changes
- **Region Information:** Where the conflicts occur

### 4. **Activity Log Panel** 📋
Timeline view of all activity with:
- **Chronological Order:** Latest activity first
- **Developer Color-Coding:** Easy identification
- **File and Region Info:** Specific changes tracked
- **Timestamps:** When each change occurred

## Interactive Scenarios

### Run Pre-Built Scenarios

Click any scenario button to simulate real-world situations:

#### **Scenario 1: Overlapping Regions** (MEDIUM Risk)
- DevA starts refactoring `login_user` function (lines 20-40)
- DevB adds validation to the same function (lines 25-35)
- **Result:** MEDIUM risk warning (overlapping regions, no signature change)
- **UX:** Warning displayed but generation proceeds (non-blocking)

#### **Scenario 2: Non-Overlapping Regions** (LOW Risk)
- DevA refactors `login_user` function (lines 20-40)
- DevB adds separate `logout_user` function (lines 100-120)
- **Result:** LOW risk (different regions)
- **UX:** Silent, no warning

#### **Scenario 3: Signature Change** (HIGH Risk)
- DevA renames `login_user` to `authenticate` and changes signature
- DevB tries to call `login_user` with old signature
- **Result:** HIGH risk (signature change + overlap)
- **UX:** Blocking warning requires user confirmation

#### **Scenario 4: Entry Expiry**
- DevA starts work 31 minutes ago
- Entry expires after 30-minute window
- DevB works on same file
- **Result:** No warning (entry expired)
- **UX:** Silent proceed

#### **Scenario 5: Multiple Developers**
- DevA refactors User model (lines 10-50)
- DevB adds password hashing (lines 20-35)
- DevC adds email validation (lines 30-45)
- **Result:** DevC detects DevA's change
- **UX:** MEDIUM risk warning displayed

#### **Run All Scenarios**
Runs all 5 scenarios in sequence with realistic timing delays between operations.

## Visual Design

### Color Coding

**Developer Tags:**
- 🔵 **DevA:** Blue (#1976d2) - Primary developer
- 🟣 **DevB:** Purple (#7b1fa2) - Secondary developer
- 🟢 **DevC:** Green (#388e3c) - Tertiary developer
- 🟠 **DevD:** Orange (#f57c00) - Quaternary developer

**Risk Levels:**
- 🟢 **LOW:** Green (#c8e6c9) - No conflict, silent
- 🟠 **MEDIUM:** Orange (#fff3e0) - Overlapping region, non-blocking warning
- 🔴 **HIGH:** Red (#ffebee) - Signature change, requires confirmation

**Developer Cards:**
Each developer gets a unique gradient background for easy visual identification at a glance.

### Visual Hierarchy

1. **Header** - POC title and description
2. **Scenario Controls** - One-click scenario execution
3. **Main Grid (2 columns)**
   - Left: Files and Developers
   - Right: Warnings and Activity Log
4. **Responsive Design** - Stacks to 1 column on smaller screens

## Using the Dashboard

### Quick Start (Web Browser)

```bash
# Simply open in any browser:
open ui_dashboard.html
# or
firefox ui_dashboard.html
# or
chromium ui_dashboard.html
```

### Workflow

1. **Open the dashboard** in a browser (Firefox, Chrome, Safari all work)
2. **Click a scenario button** to populate with test data
3. **Observe the visualization:**
   - Files panel shows active changes
   - Developers panel shows who's working
   - Warnings panel shows detected conflicts
   - Log panel shows timeline
4. **Run multiple scenarios** or click "Clear All" to reset

### Understanding the Output

Each scenario demonstrates:
- **File Activity:** Which files are being touched
- **Developer Involvement:** Who's making changes
- **Risk Assessment:** How conflicts are detected
- **Tiered Responses:** Different warning behaviors by risk level

## Technical Details

### Risk Classification Logic

The dashboard implements the same heuristic as the Python POC:

```javascript
function classifyRisk(currentRegion, otherRegion, otherIntent) {
    // Check for region overlap (line ranges)
    // Check for signature change keywords
    // Return: LOW, MEDIUM, or HIGH
}
```

### Local State Management

- All data is stored in JavaScript memory (browser)
- No server calls, no database
- Clearing all data clears the browser memory
- Refresh the page to reset

### Performance

- <10ms risk classification
- Real-time UI updates
- No network overhead
- Instant scenario execution

## Features Demonstrated

### ✅ File Tracking
- Shows which files have active changes
- Groups developers by file
- Displays risk level per file

### ✅ Developer Tagging
- Color-coded tags for each developer
- Shows all developers on a file
- Displays developer activity cards

### ✅ Region Visualization
- Shows specific functions/classes being edited
- Displays line ranges
- Highlights overlapping regions

### ✅ Conflict Detection
- Detects overlapping regions
- Identifies signature changes
- Classifies risk level
- Shows who's conflicting with whom

### ✅ Activity Timeline
- Chronological log of all changes
- Shows timestamps
- Displays intent descriptions
- Color-coded by developer

### ✅ Responsive Design
- Works on desktop (1400px+)
- Works on tablet (1024px)
- Works on mobile (adapts to single column)

## Integration Example

To integrate this dashboard with real activity log data:

```javascript
// Read actual activity log
fetch('.devsync/activity-log.json')
    .then(r => r.json())
    .then(entries => {
        // Populate dashboard
        entries.forEach(entry => {
            logEntry(
                entry.developer_id,
                entry.file_path,
                entry.intent,
                entry.region
            );
        });
    });
```

## Keyboard Shortcuts (Future)

Planned enhancements:
- `Ctrl+1` - Run Scenario 1
- `Ctrl+2` - Run Scenario 2
- `Ctrl+R` - Clear and reset
- `Ctrl+A` - Run all scenarios

## Troubleshooting

### Scenarios not running?
- Ensure JavaScript is enabled in your browser
- Check browser console for errors (F12 → Console)
- Try refreshing the page

### Visual issues?
- Clear browser cache (Ctrl+Shift+Delete)
- Try a different browser
- Check that CSS is rendering (gradient backgrounds should be visible)

### Data not persisting?
- The dashboard uses browser memory, not disk
- Data is cleared on refresh or "Clear All" button
- This is by design for the POC

## Next Steps

### Potential Enhancements
1. **Persistent Storage:** Save activity log to localStorage
2. **JSON Import:** Load real activity log files
3. **Export:** Download activity log as JSON
4. **Real-time Sync:** WebSocket updates from actual agents
5. **Advanced Filtering:** Filter by developer, file, risk level
6. **Diff Viewer:** Show actual code changes side-by-side
7. **Conflict Resolution:** UI for developers to resolve conflicts

### Integration Points
- Connect to Claude Code pre-generation hook
- Sync with actual `.devsync/activity-log.json`
- WebSocket for real-time multi-developer scenarios
- REST API for agent integration

## Browser Compatibility

| Browser | Support |
|---------|---------|
| Chrome/Chromium | ✅ Full |
| Firefox | ✅ Full |
| Safari | ✅ Full |
| Edge | ✅ Full |
| Mobile Safari | ✅ Basic |
| Mobile Chrome | ✅ Basic |

## Performance Metrics

- **Page Load:** <100ms
- **Scenario Execution:** <1s
- **Risk Classification:** <10ms per check
- **UI Render:** <50ms

## Open Source

This dashboard is part of the Conflict Warning POC and uses:
- Vanilla JavaScript (no frameworks)
- CSS Grid and Flexbox
- HTML5
- Zero dependencies

Perfect for:
- Teaching conflict detection concepts
- Demonstrating POC to stakeholders
- Testing risk classification logic
- Visualizing concurrent development scenarios
