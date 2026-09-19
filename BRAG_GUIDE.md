# Using Brag to Generate Neo 3.0 Launch Video

This guide explains how to use **Brag**, the Claude Code skill that turns any project into a polished 20-second launch video.

---

## What is Brag?

**Brag** is a Claude Code skill that:
- Analyzes your repository to understand what you built
- Plans a specific, creative video angle (not generic templates)
- Generates a composition brief for video rendering
- Uses Hyperframes to render a professional MP4 video
- Outputs share copy for social media

**Result**: A ~20-second launch video that feels like it was made specifically for your project.

**GitHub**: [latent-spaces/brag](https://github.com/latent-spaces/brag)

---

## Prerequisites

To generate the Neo launch video, you need:

- **Claude Code** (IDE with Brag skill support)
- **Node.js 22+** (for Hyperframes)
- **FFmpeg** on your PATH (for video encoding)
- **Hyperframes CLI** (`npx hyperframes` available)

### Verify Prerequisites

```bash
# Check Node.js version
node --version  # Should be 22+

# Check FFmpeg
ffmpeg -version

# Check Hyperframes
npx hyperframes doctor
```

If any are missing, install them:

```bash
# Install Node.js 22+ (follow nodejs.org for your OS)

# Install FFmpeg
# macOS:
brew install ffmpeg

# Ubuntu/Debian:
sudo apt-get install ffmpeg

# Windows (Chocolatey):
choco install ffmpeg
```

---

## Installation

### Option 1: Claude Code Plugin Marketplace (Recommended)

In Claude Code:

```bash
/plugin marketplace add latent-spaces/brag
/plugin install brag@brag
```

### Option 2: Skills CLI (For other agents)

```bash
# Global installation (available everywhere)
npx skills add https://github.com/latent-spaces/brag --skill brag -g

# Or scoped to this project
npx skills add https://github.com/latent-spaces/brag --skill brag
```

### Option 3: Manual Installation

```bash
# Copy Brag skill to your Claude Code skills directory
rsync -a --exclude '.DS_Store' https://github.com/latent-spaces/brag/skills/brag/ ~/.claude/skills/brag/

# Restart Claude Code
```

---

## Generating the Neo Launch Video

### Step 1: Verify Neo is Prepared

The Neo repository includes:
- ✅ `brag-plan.md` — Complete storyboard and creative brief
- ✅ `.brag.json` — Configuration (from our earlier setup)
- ✅ `index.html`, CSS, dashboards — Visual assets
- ✅ `README.md` — Product story
- ✅ Code examples — Real implementation details

### Step 2: Invoke Brag

From the Neo directory in Claude Code:

```bash
/brag
```

**Or with custom tone:**

```bash
/brag --tone "polished deadpan confidence"
```

**Or with narration (optional):**

```bash
/brag --voice
```

### Step 3: Brag Analyzes Neo

Brag will:

1. **Inspect** → Read Neo's structure:
   - `README.md` (problem/solution/features)
   - `index.html` (visual identity, colors)
   - `core/` and `examples/` (implementation details)
   - `brag-plan.md` (the creative brief we prepared)

2. **Plan** → Answer Neo-specific questions:
   - What is Neo? (Agent coordination layer)
   - Funniest/most impressive claim? (Intent → Coordinate → Generate)
   - Visual hook? (Cyan-pink gradient, conflict detection state)
   - User flow? (Agent A declares → Agent B checks → Neo decides)

3. **Storyboard** → Create beat-by-beat plan (already done in `brag-plan.md`)

4. **Compose** → Hand off to Hyperframes with:
   - Scene descriptions
   - Timing and transitions
   - Color palette
   - Music and SFX cues

5. **Render** → Hyperframes generates:
   - Motion graphics
   - Text overlays
   - Transitions
   - Audio mixing
   - Final MP4 video

### Step 4: Review Output

Brag creates `brag-output/` directory:

```
brag-output/
├── brag-plan.md           # The complete storyboard (we created this)
├── composition/           # Hyperframes composition structure
│   ├── config.json        # Video settings
│   ├── scenes.json        # Scene breakdown
│   └── assets/            # Images, fonts, audio
├── share-copy.txt         # Social media captions (auto-generated)
├── brag.mp4              # ✅ Final video (1920x1080, 20s, H.264)
└── brag.jpg              # Poster frame (for thumbnails)
```

---

## Video Specifications

| Property | Value |
|----------|-------|
| **Duration** | ~20 seconds |
| **Resolution** | 1920×1080 (Full HD) |
| **Frame Rate** | 60 fps |
| **Format** | MP4 (H.264) |
| **Audio** | Stereo, 44.1 kHz with music + SFX |
| **File Size** | ~10-15 MB |
| **Codec** | H.264 video, AAC audio |

---

## What the Neo Video Shows

### Scene Breakdown (20 seconds)

| Time | Content | Focus |
|------|---------|-------|
| **0–2s** | Two agents reaching for same function | **Hook: The problem** |
| **2–5s** | Traditional conflict flow (generate → conflict → resolve) | **Problem reveal** |
| **5–9s** | Neo intercepts at intent stage, coordinates agents | **Solution intro** |
| **9–11s** | Feature: <10ms latency metric | **Key benefit 1** |
| **11–13s** | Line-level conflict detection visualization | **Key benefit 2** |
| **13–15s** | Five agents queued, unlimited scaling | **Key benefit 3** |
| **15–20s** | GitHub link + "Try Neo" CTA | **Call to action** |

### Visual Identity

- **Colors**: Dark gradient (#0a0e27 → #1a0033) with cyan (#00d9ff) and pink (#ff006e) accents
- **Typography**: Clean, premium, readable (0.8s per line minimum)
- **Audio**: Warm, forward-thinking tech music (warm pads, modern keys) + subtle UI SFX
- **Tone**: Polished, deadpan confidence — understated, premium

---

## Sharing the Video

Once generated, you have `brag.mp4`:

### Share Captions

**Twitter/X**:
```
Two agents. One file. Conflict? Not anymore.
Neo detects overlaps before code generation—zero manual merges.
Intent → Coordinate → Generate → Commit ✓
github.com/jaykrishna316/Neo
```

**LinkedIn**:
```
🤖 Watch Neo 3.0 in action: Multi-agent coordination that actually works.

When Agent A and Agent B write to src/auth.py simultaneously:
❌ Traditional: merge conflict → manual resolution → retry
✅ Neo: intent → check → coordinate → merge ✓

<10ms latency, line-level detection, unlimited agents.
github.com/jaykrishna316/Neo
```

**YouTube Description**:
```
Neo 3.0: Agent Coordination Before Conflicts Emerge

Watch how Neo prevents merge conflicts in multi-agent systems:
✓ Pre-generation conflict detection (<10ms)
✓ Line-level semantic analysis
✓ Smart checkpointing without token waste
✓ 5+ agent teams validated

Try it: github.com/jaykrishna316/Neo
Run: python3 run.py
```

### Distribution

1. **GitHub**: Attach to releases/Neo-3.0-launch
2. **LinkedIn**: Post video + carousel
3. **Twitter/X**: Video + thread
4. **YouTube**: Upload as unlisted or community post
5. **Discord/Slack**: Share in AI/dev communities

---

## Customization Options

### Tone Variations

```bash
# Confident, premium (recommended)
/brag --tone polished

# Chaotic, fast-paced
/brag --tone chaotic

# Deadpan startup parody
/brag --tone yc-parody

# Custom direction
/brag --tone "premium sci-fi product film with deadpan humor"
```

### Format Options

```bash
# Landscape (default)
/brag --format landscape

# Vertical (for mobile/stories)
/brag --format vertical

# Square (for social tiles)
/brag --format square
```

### Audio Options

```bash
# With narration (Kokoro voice)
/brag --voice

# No music (silent)
/brag --no-music

# No sound effects
/brag --no-sfx
```

### Duration

```bash
# Shorter video (15s)
/brag --duration 15

# Longer video (30s)
/brag --duration 30
```

---

## Workflow: Full Example

### 1. Prepare (Already Done ✅)

```bash
# Verify files exist
ls -la brag-plan.md .brag.json index.html

# Check branch
git branch  # Should be on claude/brag-neo-launch-video-h3filv
```

### 2. Invoke Brag

```bash
# In Claude Code, in the Neo directory
/brag

# Or with specific tone
/brag --tone "polished deadpan confidence"
```

### 3. Wait for Rendering

Brag will:
- Analyze Neo (30s)
- Plan video (1m)
- Compose for Hyperframes (1m)
- Render video (2–3m)
- Generate share copy (30s)

**Total**: ~5–7 minutes

### 4. Review Output

```bash
# Check output directory
ls -lh brag-output/

# Watch the video
open brag-output/brag.mp4

# Read the share copy
cat brag-output/share-copy.txt
```

### 5. Share

```bash
# Copy video
cp brag-output/brag.mp4 ~/Desktop/neo-launch-3.0.mp4

# Share on GitHub, LinkedIn, Twitter, etc.
```

---

## Troubleshooting

### "Command '/brag' not found"

- **Solution 1**: Install Brag via marketplace: `/plugin marketplace add latent-spaces/brag`
- **Solution 2**: Install via skills CLI: `npx skills add https://github.com/latent-spaces/brag --skill brag`
- **Solution 3**: Restart Claude Code after installing

### "FFmpeg not found"

```bash
# macOS
brew install ffmpeg

# Ubuntu
sudo apt-get install ffmpeg

# Windows
choco install ffmpeg
```

Then verify: `ffmpeg -version`

### "Hyperframes CLI not found"

```bash
npx hyperframes doctor
```

If it doesn't work, install globally:

```bash
npm install -g hyperframes
```

### "Node.js version too old"

```bash
# Check version
node --version

# Install Node.js 22+ from nodejs.org
# Or use nvm (Node Version Manager)
nvm install 22
```

### Video renders but looks wrong

- **Dark/low contrast**: Check CSS color extraction in `brag-plan.md` — verify colors are correct
- **Text too fast**: Timing is in `brag-plan.md` — each text element should settle 0.8–1s minimum
- **Audio issues**: Check music track in `brag-output/assets/` — verify it's not corrupted

**Solution**: Edit `brag-plan.md` with corrections, then run `/brag` again.

---

## What We've Prepared

This branch (`claude/brag-neo-launch-video-h3filv`) includes:

| File | Purpose |
|------|---------|
| `brag-plan.md` | Complete storyboard answering all 9 Brag questions |
| `.brag.json` | Configuration with features, use cases, visuals |
| `LAUNCH_VIDEO.md` | Documentation about the video |
| `LAUNCH_VIDEO_MARKETING.md` | Ready-to-use social captions |
| `BRAG_GUIDE.md` | This guide (how to actually generate the video) |
| `index.html`, dashboards | Visual assets Brag will analyze |
| `README.md` | Product story Brag reads |

Everything is ready. Just run `/brag` to generate the video. ✅

---

## Next Steps

1. **Install Brag** (if not already installed)
2. **Run `/brag`** in Claude Code
3. **Review** `brag-output/brag.mp4`
4. **Share** with the team/community
5. **Track** engagement (views, clicks, stars)

---

## Resources

- **Brag GitHub**: https://github.com/latent-spaces/brag
- **Brag Website**: https://latent-spaces.github.io/brag/
- **Hyperframes**: https://hyperframes.heygen.com/
- **This Branch**: `claude/brag-neo-launch-video-h3filv`
- **Neo Repository**: https://github.com/jaykrishna316/Neo

---

**Last Updated**: 2026-09-19  
**Status**: Ready to generate launch video  
**Branch**: `claude/brag-neo-launch-video-h3filv`  
**Generated By**: Claude Code Session
