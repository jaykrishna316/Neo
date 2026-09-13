# Neo Landing Page Setup Guide

## Quick Start

1. **Place your hero image** in this folder with the filename: `neo-hero.png`
   - The file should be in PNG format
   - Size: 1200x627px (optimized for web)
   - Same folder as `neo_premium.html`

2. **Open in browser** 
   - Double-click `neo_premium.html` or
   - Right-click → Open with → Your preferred browser

3. **What you'll see**
   - Full-screen hero section with your rendered image
   - Professional test results from Agent A & B
   - Problem description
   - Solution overview
   - Three-tier enforcement architecture
   - Call-to-action section
   - Scroll animations and effects

## File Structure

```
neoweb/
├── neo_premium.html          (Main landing page)
├── neo-hero.png              (Your hero image - place here)
├── neo_icon.svg              (Neo logo icon)
├── neo_linkedin_banner.html  (LinkedIn profile banner)
├── index.html                (Directory/index page)
├── README.md                 (Project info)
└── SETUP.md                  (This file)
```

## Image Requirements

- **Filename**: `neo-hero.png` (must match exactly)
- **Format**: PNG
- **Recommended Size**: 1200x627px
- **Location**: Same folder as neo_premium.html

## Customization

All styling uses CSS variables that can be customized:
- `--primary`: #00d9ff (cyan)
- `--secondary`: #ff006e (magenta)
- `--accent`: #8338ec (purple)

These colors are used throughout the page for consistency.

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers (responsive design)

## Issues?

- Hard refresh browser cache (Cmd+Shift+R or Ctrl+Shift+R)
- Check image filename is exactly `neo-hero.png`
- Verify image is in same folder as HTML file
