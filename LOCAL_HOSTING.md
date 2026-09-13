# Local Hosting Guide for Neo Landing Page

Host your Neo landing page from your local machine without needing GitHub or Cloudflare.

## Quick Start (Choose One)

### Option 1: Python (Easiest - macOS/Linux)

```bash
cd ~/Desktop/neoweb
python3 -m http.server 8000
```

Then open: **http://localhost:8000/neo_premium.html**

### Option 2: Node.js

```bash
cd ~/Desktop/neoweb
npx http-server
```

Then open the URL shown in terminal (usually **http://localhost:8080**)

### Option 3: Live Server (VS Code)

1. Install VS Code extension: **Live Server**
2. Right-click `neo_premium.html` → **Open with Live Server**
3. Browser opens automatically

## What You Need in Your Folder

```
neoweb/
├── neo_premium.html      ← Main landing page
├── neo-hero.png          ← Your hero image
└── Other files (optional)
```

## How It Works

- **Local Server**: Runs on your computer at `http://localhost:PORT`
- **No Internet Needed**: Works offline
- **Auto-Reload**: Many tools auto-refresh when files change
- **Instant**: No build process, instant changes

## Stopping the Server

- **Python**: Press `Ctrl+C` in terminal
- **Node**: Press `Ctrl+C` in terminal
- **VS Code Live Server**: Click "Go Live" button again to stop

## Testing on Other Devices

To access from another device (phone, tablet):

1. Find your computer's IP: 
   - **Mac/Linux**: `ifconfig | grep "inet "`
   - Look for IP like `192.168.1.100`

2. Visit: `http://192.168.1.100:8000/neo_premium.html`

## Share Your Landing Page

### Method 1: Direct File
- Send `neo_premium.html` + `neo-hero.png` in same folder
- Person opens HTML file locally
- Works instantly

### Method 2: File Server Link
- Share localhost link from terminal output
- Works only on same WiFi network
- Stop sharing = press Ctrl+C

### Method 3: GitHub (Optional)
- If you want to host online later, push to Neo repo
- Deploy to Cloudflare, Vercel, or Netlify anytime
- No commitment needed now

## Troubleshooting

**"Cannot find module" / "python not found"**
- Install Python: https://python.org
- Or install Node: https://nodejs.org

**Port already in use?**
```bash
# Use different port
python3 -m http.server 9000
# Visit: http://localhost:9000
```

**Image not showing?**
- Check filename is exactly `neo-hero.png`
- Image must be in same folder as HTML
- Refresh browser (Cmd+R or Ctrl+R)

**Slow to load?**
- Image file size? Check: `ls -lh neo-hero.png`
- Large images need optimization
- Should be under 2MB for web

## Advanced: CORS Issues (If You Hit Them)

If you see console errors about CORS when loading resources:

```bash
# Python with CORS headers
python3 -m http.server 8000 --bind localhost
```

This is rarely needed for static HTML sites.
