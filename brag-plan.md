# Neo 3.0 Launch Video - Brag Plan

**Generated**: 2026-09-19  
**Project**: Neo - Agent Coordination Layer  
**Format**: Landscape (16:9)  
**Duration**: 20 seconds  
**Tone**: Polished + Deadpan (confident, understated tech)  

---

## 9-Question Rubric Analysis

### 1. What is the app?
Neo is an agent coordination layer that prevents merge conflicts **before autonomous agents generate code**, enabling multiple AI agents to work safely on shared codebases simultaneously.

### 2. What is the funniest or most impressive claim?
**"Instead of: generate → commit → merge → conflict → resolve → revert → retry"**  
**"Neo enables: intent → coordinate → authorize → generate → commit ✓"**

The absurdity is that teams still manually resolve conflicts, and Neo just... prevents the whole thing before it happens. Not flashy, just obviously correct.

### 3. What is the visual hook?
Neo's color identity: Deep gradient background (#0a0e27 to #1a0033) with cyan-to-pink gradient text (#00d9ff to #ff006e). The visual language is premium, slightly sci-fi (matrix-inspired "Neo" reference), but serious about the tech underneath.

**Strongest visual**: The conflict detection state transition. Show two agents attempting the same function → Neo intercepts → one agent pauses safely → both complete cleanly.

### 4. What should be shown from the actual UI?
- **Hero section** from index.html or dashboard showing the color palette
- **Activity log structure** (the core data model of Neo)
- **Real code snippet**: The pre-gen check API call (from examples/cli_demo.py)
- **Dashboard mockup**: The conflict heatmap or state machine visualization (from ui_dashboard.html)

### 5. What is the shortest satisfying video?
**15 seconds minimum, 20 seconds target.** 
- Hook (0-2s): Two agents, one conflict
- Problem reveal (2-5s): The manual merge flow (what people do now)
- Solution intro (5-8s): Neo intercepts before code generation
- Key feature moments (8-15s): <10ms latency, line-level detection, 5+ agents
- CTA (15-20s): Try it, link to repo

### 6. What tone fits best?
**Preset**: `polished` (serious, elegant)  
**Creative direction**: "Quiet premium product film — the joke is that conflict detection should work like this by default"

This product is genuinely useful, not absurd. The confidence comes from correctness, not hype.

### 7. What should the audio feel like?
**Approach**: Clean, minimal, premium. Think Vercel product films—understated, composed, trust-building.

- **Music bed**: Warm, forward-thinking, tech-confident (60-80 bpm, ~100 dB ambient). Modern electronic with organic elements (keys, pads). No aggressive drops or hype. 
- **SFX**: 
  - Soft UI interaction sounds (icon appears: +60dB, ~400Hz harmonic)
  - Lock/checkpoint sounds (quiet, authoritative, ~200Hz)
  - Success pulse (warm bell tone, +70dB, ~800Hz)
- **No voiceover by default.** Video speaks through motion, not narration.

Reference energy: Linear's "Velocity" promo, Vercel's "Next.js release" videos.

### 8. What should the share caption say?
**Share Copy**:  
"Two agents. One file. Conflict?  
Not anymore. Neo detects overlaps before code generation—zero manual merges.  
Intent → Coordinate → Generate → Commit ✓  
github.com/jaykrishna316/Neo"

### 9. What's the user flow worth showing?
Neo is not a UI product; it's a coordination API. The "user flow" is the developer workflow:

**Beat-by-beat**:
1. **Agent A declares intent** → "I'm refactoring authenticate_user (lines 40-80)"
2. **Agent B checks for conflicts** → Sends query: "Is it safe to modify lines 50-75?"
3. **Neo returns: HIGH RISK (82/100)** → Visualized as a score, risk color coding
4. **Agent B pauses at checkpoint** → No polling, no wasted tokens, context saved
5. **Agent A completes work** → Lock released
6. **Agent B resumes from checkpoint** → Exact same context, picks up seamlessly
7. **Both commit cleanly** → Sequential, zero manual work

---

## Storyboard: 20-Second Beat Breakdown

### Scene 1: The Hook (0–2 seconds)
**Content**: Split-screen: Agent A and Agent B both reaching for the same function.  
**Text**: "Two agents. One problem."  
**Visual**: Dark background, code snippets appearing in cyan, soft glow. Typography: bold, clean.  
**Audio**: Music fades in, subtle UI tone (lock icon slides in).  
**Transition**: Zoom to conflict marker.

**Timing**: 2s settled read.

---

### Scene 2: The Old Way (2–5 seconds)
**Content**: Flow diagram showing traditional approach.  
```
Generate → Commit → Merge → CONFLICT ❌ → Manual Resolution → Retry
```
**Text**: "The old way: Conflict after code."  
**Visual**: Gray/desaturated colors for the "old way," growing red conflict indicator.  
**Audio**: Slight tension build, discordant note on conflict marker.  
**Transition**: Wipe/cut to black.

**Timing**: 3s, text holds long enough to read.

---

### Scene 3: The Neo Solution (5–9 seconds)
**Content**: Neo's approach—pre-generation gate.  
```
Agent A declares intent → Agent B queries → Neo checks → Decision
```
**Text**: "Neo detects before code is written."  
**Visual**:  
- Agent A icon (left) + intent box "refactor login (lines 40–80)" in cyan
- Query arrow from Agent B
- Neo layer in center (logo + "Coordination Layer" label)
- High-risk score appears (82/100, warm color)
- Agent B pauses (checkpoint animation)

**Audio**: Music swells slightly, lock/checkpoint sound (authoritative, low-frequency).  
**Transition**: Slide into feature moments.

**Timing**: 4s (slow reveal builds confidence).

---

### Scene 4a: Feature Moment — Latency (9–11 seconds)
**Content**: Metric card: "< 10ms latency"  
**Visual**: A clock icon, number ticking down, cyan glow.  
**Text**: "< 10ms latency. Real-time checks."  
**Audio**: Quick confirmation tone (~800Hz, +70dB, 0.2s).  
**Transition**: Slide to next feature.

**Timing**: 2s.

---

### Scene 4b: Feature Moment — Line-Level Detection (11–13 seconds)
**Content**: Code with overlapping line ranges highlighted.  
**Visual**:  
- Code block (authenticate_user function)
- Lines 40–80 highlighted in one color
- Lines 50–75 highlighted in another
- Overlap region shows conflict zone
- Label: "Line-level semantic detection"

**Text**: "Detects overlaps at the line level."  
**Audio**: Subtle harmonics as highlight regions appear.  
**Transition**: Slide to next feature.

**Timing**: 2s.

---

### Scene 4c: Feature Moment — Multi-Agent Support (13–15 seconds)
**Content**: Five agent icons, all waiting to work on the same file.  
**Visual**:  
- 5 colored circles (agents)
- Queue visualization, per-resource locking shown
- Label: "5+ agent teams. Unlimited per resource."

**Text**: "Scale to 5+ agents safely."  
**Audio**: Layered bells/tones (one per agent entering queue), builds harmony.  
**Transition**: Cut to CTA.

**Timing**: 2s.

---

### Scene 5: Call-to-Action (15–20 seconds)
**Content**: GitHub badge + command to try.  
**Text**:  
```
Try Neo 3.0  
python3 run.py  
github.com/jaykrishna316/Neo
```

**Visual**:  
- Dark background
- Neo logo (cyan + pink gradient)
- GitHub badge appears
- Command text settles (monospace, cyan)
- Subtle glow/pulse on the command

**Audio**: Music resolves to a calm close, final confirmation tone.  
**Transition**: Fade to black.

**Timing**: 5s (gives viewers time to note the link).

---

## Music Cue Guidance

**Track**: "Happy Beats / Business Moves" from [ende.app](https://ende.app/en)  
**Duration**: 20–22 seconds (accommodates fade-in and resolution)  
**Cues**:
- **0–2s (Hook)**: Fade in at -12dB, rise to -6dB by 2s
- **2–5s (Old Way)**: Maintain bed, minor tension note at conflict marker
- **5–9s (Solution)**: Swell +2dB at Neo layer reveal, lock sound layered on music
- **9–15s (Features)**: Beat aligns to feature card reveals (BPM synced)
- **15–20s (CTA)**: Gradual fade starting at 18s, resolve to silence by 20s + final tone

---

## Color Palette (from Neo's CSS)

- **Primary Gradient**: #0a0e27 (dark navy) → #1a0033 (dark purple)
- **Accent Gradient**: #00d9ff (cyan) ← → #ff006e (hot pink)
- **Text**: #e0e0e0 (light gray)
- **Card Border**: rgba(0, 217, 255, 0.2) (transparent cyan)
- **Hover State**: rgba(0, 217, 255, 0.1) (bright cyan overlay)

**Video Palette**:
- Use the gradient background for stability
- Cyan for "correct/safe" states (passing checks, lined up agents)
- Warm orange/yellow for warnings/high-risk states
- Pink accent for emphasis/energy moments

---

## Assets to Reference

1. **Code snippets** from `examples/cli_demo.py` (the pre-gen check call)
2. **Dashboard mockup** from `ui_dashboard.html` (activity log, conflict heatmap)
3. **Logo** — Neo brand identity (if vector available)
4. **Numbers** to pull:
   - <10ms latency (core promise)
   - 5+ agents (scalability proof point)
   - 340% ROI (business metric, optional if space)
   - Zero dependencies (technical elegance)

---

## Creative Laws Applied

✅ **Short**: 20 seconds (not one second wasted)  
✅ **Readable**: Every text element holds 0.8–1s minimum  
✅ **Specific**: Every scene is Neo-specific (code functions, activity logs, coordination model)  
✅ **Show the thing**: Real code snippets and dashboard UI shown  
✅ **No generic SaaS**: Copy from Neo's own README, no "streamline" or "unlock"  
✅ **Hook is everything**: Opens with conflict (relatable problem), 2s decision point  
✅ **Funny earns its place**: Humor comes from the absurdity of the problem (manual merges), not forced jokes  

**Pattern Applied**:  
```
Hook (2s) → Problem reveal (3s) → Solution (4s) → Features (6s) → CTA (5s)
= 20s total
```

---

## Share Copy

**Twitter/X** (280 chars):
```
Two agents. One file. Conflict?
Not anymore. Neo detects overlaps before code generation—zero manual merges.
Intent → Coordinate → Generate → Commit ✓
github.com/jaykrishna316/Neo
```

**LinkedIn** (extended):
```
🤖 Watch Neo 3.0 in action: Multi-agent coordination that actually works.

When Agent A and Agent B write to src/auth.py simultaneously:
❌ Traditional: merge conflict → manual resolution → retry
✅ Neo: intent → check → coordinate → merge ✓

<10ms latency, line-level detection, unlimited agents.

github.com/jaykrishna316/Neo
```

---

## Tone System: Polished + Deadpan

**Tone Preset**: `polished`  
- Serious, elegant, premium  
- Trust-building through simplicity  
- No hype, no wasted words  

**Creative Direction**: "Quiet confidence—the joke is that this should work by default"  
- Understatement of the problem ("Conflict? Not anymore.")  
- Matter-of-fact solution reveal  
- Let the tech speak through the visualization, not voiceover  

**Pacing**: 20s total, never rushed, never boring. Every scene gives the viewer time to understand before moving on.

---

## Next Steps (For Hyperframes)

Once approved:

1. **Composition Brief** → Hand off to Hyperframes with:
   - Scene-by-scene breakdown (start times, text, visual directions)
   - Color palette + typography spec
   - Audio track + cue timings
   - Motion preferences (no flashy cuts, prefer slides/fades)

2. **Render** → Video output to `brag-output/brag.mp4` (1920×1080, 60fps, H.264)

3. **Poster Frame** → Pick frame at 3–4s (Neo logo + first feature moment) as thumbnail

4. **Share Assets** → Generate `share-copy.txt` with captions for all platforms

---

**Status**: Plan complete. Ready for Hyperframes composition.
