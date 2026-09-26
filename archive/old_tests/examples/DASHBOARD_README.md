# Neo Analytics Dashboard 🚀

Ultra-futuristic real-time monitoring dashboard for multi-agent coordination. Visualize conflicts, track agent activity, and identify code hotspots.

## Quick Start

1. **Open the dashboard:**
   ```bash
   # Local testing
   open neo_analytics_dashboard.html
   # or
   python3 -m http.server 8000
   # Then visit: http://localhost:8000/examples/neo_analytics_dashboard.html
   ```

2. **View mock data** - Dashboard loads with realistic Neo coordination data

## Features

### 📊 Key Metrics
- **Conflicts Detected**: Total conflicts caught by Neo
- **Active Agents**: Live agents in flight
- **Coordination Events**: Total interactions today
- **Tokens Saved**: Value from preventing conflicts

### 🔥 File Conflict Heat Map
Color-coded file conflict intensity:
- **Red/Hot (95°)**: Critical - 8+ conflicts today
- **Orange/Warm (78°)**: High - 6+ conflicts
- **Cyan/Cool (62°)**: Medium - 3-5 conflicts
- **Blue/Cold (24°)**: Low - 0-2 conflicts

**Pro Tips:**
- Hover over files to see details
- Use heat map to identify refactoring candidates
- Cold files = stable, high-confidence zones

### 📈 Coordination Timeline
- **Event count** by hour (blue line)
- **Conflict occurrences** (red line)
- Identify peak coordination times
- Spot patterns in team workflow

### 🤖 Active Agents
Real-time agent status:
- **Name & Status** - Active/Idle with animation
- **In-Flight Tasks** - Current work queue
- **Token Usage** - Cumulative for session
- **Multi-provider** - Claude, GPT-4, Gemini, Groq, Local models

### ⚠️ Recent Events
- **Conflict pairs** - Which agents conflicted?
- **File/Function** - Where did it happen?
- **Resolution status** - Prevented/Escalated
- **Timestamp** - When it occurred

## Data Structure

The dashboard reads `mock_activity_log.json`:

```json
{
  "metadata": {
    "total_agents": 12,
    "total_events": 487,
    "total_conflicts_detected": 24,
    "prevention_rate": 100.0
  },
  "agents": [...],
  "files": [
    {
      "path": "src/auth/login.py",
      "conflicts": 8,
      "writers": 4,
      "hotness": 95
    }
  ],
  "conflict_events": [...],
  "timeline": [...]
}
```

## Customization

### Change Mock Data
Edit `mock_activity_log.json`:
```json
{
  "files": [
    {
      "path": "your/file.py",
      "conflicts": 15,
      "writers": 5,
      "hotness": 88
    }
  ]
}
```

### Connect Real Data
Replace the hardcoded dashboard data with API calls:
```javascript
// In neo_analytics_dashboard.html
fetch('http://your-api/neo/analytics')
  .then(r => r.json())
  .then(data => {
    // Update dashboard with real data
  });
```

### Modify Colors
Edit CSS variables in `<style>`:
```css
:root {
    --primary: #00d9ff;    /* Neo cyan */
    --secondary: #ff006e;  /* Neo magenta */
    --accent: #8338ec;     /* Neo purple */
    --hot: #ff1744;        /* Conflict red */
    --cold: #1e88e5;       /* Safe blue */
}
```

## Integration Patterns

### 1. Standalone Demo
```bash
open neo_analytics_dashboard.html
```
Perfect for: Sales demos, investor presentations, marketing

### 2. Embedded in Web App
```html
<iframe src="/neo/dashboard" width="1600" height="900"></iframe>
```

### 3. Real-Time with WebSocket
```javascript
// Connect to live Neo coordination API
const ws = new WebSocket('wss://api.neo/ws/analytics');
ws.onmessage = (msg) => {
  updateDashboard(JSON.parse(msg.data));
};
```

### 4. Grafana Integration
Export metrics to Prometheus format:
```bash
curl http://your-neo-api/metrics/prometheus > metrics.txt
```

## What Enterprise Customers See

| Feature | Value |
|---------|-------|
| **Visibility** | "See exactly where conflicts happen" |
| **Insights** | "Which files need refactoring?" |
| **Monitoring** | "Is coordination working right now?" |
| **Intelligence** | "Predict future hotspots" |
| **Reporting** | "Show exec team ROI of Neo" |

## Performance Notes

- Dashboard loads instantly (no API calls in mock mode)
- Chart.js handles timeline visualization
- Glassmorphism effects optimized for modern browsers
- Smooth animations at 60fps

## Browser Support

- ✅ Chrome/Edge 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Mobile browsers (responsive)

## Product Positioning

**"Real-time intelligence for multi-agent coordination"**

Use this dashboard to:
1. **Demo Neo's value** - "See conflicts prevented in real-time"
2. **Prove ROI** - "Here's token savings + productivity gains"
3. **Monitor production** - "Live coordination status"
4. **Identify bottlenecks** - "Refactor these hot files"
5. **Team onboarding** - "This is how Neo protects your code"

## Files Included

- `neo_analytics_dashboard.html` - Standalone dashboard (no dependencies except Chart.js)
- `mock_activity_log.json` - Sample data from a 12-agent coordination session
- `DASHBOARD_README.md` - This guide

## Next Steps

1. **Open the dashboard** - `open neo_analytics_dashboard.html`
2. **Explore the UI** - Hover, interact, read insights
3. **Modify mock data** - Change `mock_activity_log.json`
4. **Connect real API** - Replace fetch calls with your Neo API
5. **Deploy to production** - Use as admin panel for enterprise customers

---

**Built for enterprise visibility into multi-agent AI coordination** ⚡
