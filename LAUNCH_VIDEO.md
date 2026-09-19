# Neo 3.0 Launch Video

> **Automated launch video generation for autonomous agent coordination framework**

## Overview

This document describes the Neo 3.0 launch video — a 20-second automated showcase of Neo's core value proposition, features, and capabilities. The video is generated using **Brag**, a Claude Code skill that transforms repository metadata into shareable launch videos.

---

## What is Neo 3.0?

**Neo 3.0** is the latest evolution of Neo, the agent coordination layer that prevents merge conflicts **before autonomous agents generate code**.

### The Core Innovation

```
Traditional Agent Workflow:          Neo Workflow:
Agent A generates code        →      Agent A declares intent
   ↓                               ↓
Agent B generates code        →      Agent B checks for conflicts
   ↓                               ↓
Merge conflict               →      Coordination decisions
   ↓                               ↓
Manual resolution              ✓ Safe parallel execution
```

Neo eliminates merge conflicts, failed builds, and wasted tokens by inserting a coordination layer that runs **before code generation**.

---

## Launch Video Features

The Neo 3.0 launch video showcases:

### 1. **The Problem** (0-3 seconds)
- Two autonomous agents attempting to modify the same function simultaneously
- Git merge conflict appearing in real-time
- Error messages and build failure indicators
- Visual: Code split-screen with merge conflict markers

### 2. **The Solution** (3-7 seconds)
- Neo's pre-generation coordination gate activating
- Agent A's intent being registered
- Agent B querying for conflicts
- One agent pausing at a checkpoint while the other completes safely
- Visual: Coordination layer intercepting before code generation

### 3. **Key Features** (7-12 seconds)
Rapid feature showcase with metrics:
- ⚡ **<10ms latency** - Sub-millisecond conflict checks
- 🔍 **Line-level detection** - Semantic conflict analysis
- 🤝 **5+ agent teams** - Unlimited concurrent agents with per-resource locking
- ⚡ **Zero dependencies** - Production-ready, runs on Python 3.8+
- 💾 **Smart checkpointing** - Agents pause without token waste

### 4. **Enterprise Capabilities** (12-18 seconds)
- Multi-tenant architecture (1500+ ops/sec per tenant)
- IDE integrations: Claude Code, Devin, OpenAI Copilot
- Real-time MCP event streaming
- Audit trails and compliance reporting
- Visual: Architecture diagram with IDE logos

### 5. **Call-to-Action** (18-20 seconds)
```
Try Neo 3.0 Now:
  • GitHub: github.com/jaykrishna316/Neo
  • Demo: python3 run.py
  • Dashboard: Explore interactive examples
```

---

## Launch Video Configuration

The video generation is configured via `.brag.json`:

### Core Configuration

```json
{
  "name": "Neo 3.0",
  "tagline": "Autonomous agents coordinating safely before conflicts emerge",
  "description": "Neo is the agent coordination layer...",
  "music": {
    "genre": "modern, energetic, tech-forward",
    "mood": "confident, fast-paced, professional",
    "duration": "20 seconds"
  }
}
```

### Visual Moments

The video is structured as 5 sequential moments:

| Moment | Duration | Focus | Visuals |
|--------|----------|-------|---------|
| **Problem** | 0-3s | Agent conflict | Code, merge conflict, errors |
| **Solution** | 3-7s | Pre-gen coordination | Coordination gate, checkpoint |
| **Features** | 7-12s | Key metrics | Dashboard, feature cards |
| **Enterprise** | 12-18s | Scale & integration | Architecture, IDE logos |
| **CTA** | 18-20s | Action | GitHub, demo command |

---

## How to Generate the Launch Video

### Option 1: Using Claude Code (Recommended)

1. **Install Brag skill** (one-time):
   ```bash
   # In Claude Code editor, use plugin marketplace
   # Add: latent-spaces/brag
   ```

2. **Run Brag**:
   ```bash
   # In the Neo directory
   /brag
   ```

3. **Output**:
   ```
   ✅ Neo 3.0 launch video generated
   📁 Output: neo-launch-3.0.mp4
   🎵 Duration: 20 seconds
   📊 Format: 1920x1080 @ 60fps
   ```

### Option 2: Using CLI (Advanced)

```bash
# Install Brag CLI
npx skills add https://github.com/latent-spaces/brag --skill brag

# Run from Neo directory
npx brag --config .brag.json --output neo-launch-3.0.mp4
```

### Option 3: Configuration-Only (Current Implementation)

The `.brag.json` configuration file is committed to the repository, enabling:
- **Reproducible video generation** - Same config always produces same video
- **Version tracking** - Changes to tagline/features tracked in git
- **CI/CD integration** - Automated video regeneration on release

---

## Video Specifications

### Technical Details

| Property | Value |
|----------|-------|
| **Duration** | 20 seconds |
| **Resolution** | 1920x1080 (Full HD) |
| **Frame Rate** | 60 fps |
| **Format** | MP4 (H.264) |
| **Audio** | Stereo, 44.1kHz |
| **File Size** | ~8-12 MB |
| **Rendering Engine** | Hyperframes |

### Platforms

✅ **Optimal For:**
- LinkedIn carousel posts
- YouTube community/Shorts
- Twitter/X video posts
- GitHub repository cards
- Product launch announcements
- Sales/investor decks

---

## Brag Workflow: Behind the Scenes

Here's how Brag transforms the `.brag.json` into a video:

```
1. Configuration Parsing
   └─ Read .brag.json for tagline, features, visual moments

2. Insight Extraction
   └─ Identify core problem/solution/benefits
   └─ Extract key metrics and social proof

3. Brief Generation
   └─ Create focused brief for Hyperframes
   └─ Structure visual moments in sequence
   └─ Select music and pacing

4. Motion Graphics Rendering
   └─ Generate animated title cards
   └─ Create feature showcase animations
   └─ Render code examples and diagrams
   └─ Time visual transitions (20s total)

5. Sound Design
   └─ Select genre-appropriate background music
   └─ Add UI sound effects (clicks, transitions)
   └─ Layer audio narration (optional)

6. Final Rendering
   └─ Composite video tracks
   └─ Encode to MP4 H.264
   └─ Output: neo-launch-3.0.mp4
```

---

## Asset References

### Logo & Branding
- **Neo Logo**: Included in repository root
- **Color Scheme**: 
  - Primary: Deep blue (#1e40af)
  - Accent: Cyan (#06b6d4)
  - Dark: Almost black (#0f172a)

### Code Examples Used
- Conflict scenario: `examples/conflict_demo.py`
- Coordination demo: `examples/cli_demo.py`
- Dashboard: `examples/neo_unified_dashboard.html`

### Documentation
- **Quick Start**: `GETTING_STARTED.md`
- **Architecture**: `OVERVIEW.md`
- **Features**: `README.md` (Features section)

---

## Version History

### Neo 3.0 (Current)
- **Release Date**: 2026-09-19
- **Video Config**: `.brag.json`
- **Key Highlight**: 5-phase agent autonomy engine + State Machine v2
- **Target Audience**: Enterprise AI teams, autonomous agent developers

### Previous Versions
- **Neo 2.0**: Event-driven coordination (5 phases)
- **Neo 1.0**: Pre-generation conflict detection (foundation)

---

## Distribution Strategy

### Launch Timeline

| Date | Action | Platform |
|------|--------|----------|
| **2026-09-20** | Generate video | neo-launch-3.0.mp4 |
| **2026-09-21** | GitHub Release | Attach to GitHub release |
| **2026-09-22** | LinkedIn Post | Video + highlights carousel |
| **2026-09-23** | YouTube Upload | Community post with link |
| **2026-09-25** | Press Kit | Share with dev communities |

### Sharing Checklist

- [ ] Generate video using `/brag` command
- [ ] Verify resolution and duration (1920x1080, 20s)
- [ ] Create GitHub release with video attachment
- [ ] Write LinkedIn caption highlighting features
- [ ] Upload to YouTube (unlisted or public)
- [ ] Create product hunt post with video embed
- [ ] Share in AI/agent developer communities
- [ ] Update website with embedded video
- [ ] Include in investor materials (if applicable)

---

## Future Enhancements

### Planned for Neo 3.1+
- [ ] Multi-language subtitle generation
- [ ] Custom music selection (from library)
- [ ] Automated social media captions
- [ ] Interactive HTML version of video
- [ ] Behind-the-scenes developer commentary
- [ ] Customer testimonial integration

### Brag Ecosystem
- **Brag Templates**: Custom templates for different repo types
- **Music Library**: Genre-specific royalty-free tracks
- **Animation Presets**: Motion graphic styles for consistency
- **Analytics**: Track video engagement and click-through rates

---

## FAQ

### Q: Can I customize the music?
**A**: Yes! Brag selects music based on the `music.genre` and `music.mood` fields in `.brag.json`. You can modify these to adjust the style.

### Q: How long does video generation take?
**A**: Typical generation time is 2-5 minutes, depending on complexity and Hyperframes rendering queue.

### Q: Can I use the video commercially?
**A**: Yes! The video is generated from your repository with royalty-free music from Brag's curated library. Attribution to Hyperframes is included in the video footer.

### Q: What if I want to make changes to the video?
**A**: Edit `.brag.json` (features, tagline, visual moments) and regenerate. Git tracks all changes for version control.

### Q: Is the video accessible (captions, etc.)?
**A**: Brag includes optional auto-generated captions. Enable via `"captions": true` in `.brag.json`.

---

## Resources

### Official Brag Links
- **GitHub**: https://github.com/latent-spaces/brag
- **Website**: https://latent-spaces.github.io/brag/
- **Demo**: [YouTube: /brag Turns Any Side Project Into a Launch Video](https://www.youtube.com/watch?v=4Zuai9Ff5zI)

### Neo Documentation
- **Getting Started**: `GETTING_STARTED.md`
- **Architecture**: `OVERVIEW.md`
- **Examples**: `examples/` directory
- **API Reference**: `docs/` directory

### Contact
- **Issues**: GitHub Issues in Neo repository
- **Brag Support**: GitHub Issues in latent-spaces/brag
- **Neo Author**: https://github.com/jaykrishna316

---

**Last Updated**: 2026-09-19  
**Video Version**: 3.0  
**Status**: Ready for generation via `/brag` command
