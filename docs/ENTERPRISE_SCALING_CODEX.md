# Enterprise Scaling: GitHub Copilot / Codex Coordination

## Overview

Integrate coordination state machine with **GitHub Copilot** (powered by OpenAI Codex) for IDE-based multi-developer scenarios. Keep human developers and AI assistants from conflicting in shared codebases.

## Architecture

```
Developer 1 (VS Code with Copilot)
    ↓
Copilot Extension + Coordination Client
    ↓
Coordination Service ← Shared Log ← Event Bus

Developer 2 (VS Code with Copilot)
    ↓
Copilot Extension + Coordination Client

IDE Coordination Plugin
├── Pre-suggestion: Check conflicts
├── Suggestion generation (Copilot)
└── Post-acceptance: Mark complete
```

## Implementation

### 1. VS Code Extension with Coordination

```typescript
// src/extension.ts
import * as vscode from 'vscode';
import axios from 'axios';

export class CoordinationClient {
    private coordinationUrl: string;
    private deviceId: string;
    
    constructor(coordinationUrl: string) {
        this.coordinationUrl = coordinationUrl;
        this.deviceId = `dev-${os.hostname()}-${os.userInfo().username}`;
    }
    
    async checkConflicts(
        filePath: string,
        region: string,
        intent: string
    ): Promise<ConflictCheck> {
        const response = await axios.post(
            `${this.coordinationUrl}/check-conflicts`,
            {
                agent_id: this.deviceId,
                file_path: filePath,
                region: region,
                intent: intent
            }
        );
        
        return response.data;
    }
    
    async logIntent(
        filePath: string,
        region: string,
        intent: string
    ) {
        return axios.post(
            `${this.coordinationUrl}/log-intent`,
            {
                agent_id: this.deviceId,
                file_path: filePath,
                region: region,
                intent: intent
            }
        );
    }
    
    async markComplete(filePath: string) {
        return axios.post(
            `${this.coordinationUrl}/mark-complete`,
            {
                agent_id: this.deviceId,
                file_path: filePath
            }
        );
    }
    
    async subscribeToEvents(callback: (event: any) => void) {
        const ws = new WebSocket(
            `${this.coordinationUrl.replace('http', 'ws')}/events?agent_id=${this.deviceId}`
        );
        
        ws.onmessage = (event) => callback(JSON.parse(event.data));
    }
}

class CoordinatedCopilotExtension {
    private coordination: CoordinationClient;
    private currentFile: string = '';
    private currentRegion: string = '';
    
    activate(context: vscode.ExtensionContext) {
        this.coordination = new CoordinationClient(
            vscode.workspace.getConfiguration().get('coordination.url')
        );
        
        // Hook into Copilot suggestions
        this.setupCopiletHooks();
        
        // Subscribe to coordination events
        this.coordination.subscribeToEvents((event) => {
            this.handleCoordinationEvent(event);
        });
    }
    
    private setupCopiletHooks() {
        // Before Copilot generates suggestion
        vscode.commands.registerCommand('copilot.before-generate', async (context) => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) return;
            
            const filePath = editor.document.uri.fsPath;
            const region = this.getRegionFromSelection(editor);
            
            // Check conflicts
            const check = await this.coordination.checkConflicts(
                filePath,
                region,
                "Generating code suggestion"
            );
            
            if (check.risk_score > 70) {
                // Show warning
                const choice = await vscode.window.showWarningMessage(
                    `High risk conflict detected (${check.risk_score}/100)`,
                    'Wait for others',
                    'Proceed carefully',
                    'Collaborate'
                );
                
                if (choice === 'Wait for others') {
                    vscode.window.showInformationMessage(
                        `Waiting for ${check.conflicting_agents.join(', ')}...`
                    );
                    // Don't generate
                    return false;
                }
            }
            
            // Log intent
            await this.coordination.logIntent(
                filePath,
                region,
                "Copilot suggestion"
            );
            
            return true; // Allow generation
        });
        
        // After Copilot suggestion accepted
        vscode.commands.registerCommand('copilot.suggestion-accepted', async (context) => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) return;
            
            await this.coordination.markComplete(editor.document.uri.fsPath);
        });
    }
    
    private getRegionFromSelection(editor: vscode.TextEditor): string {
        const selection = editor.selection;
        const startLine = selection.start.line;
        const endLine = selection.end.line;
        
        return `lines ${startLine + 1}-${endLine + 1}`;
    }
    
    private handleCoordinationEvent(event: any) {
        if (event.event_type === 'lock_removed') {
            vscode.window.showInformationMessage(
                '✓ Lock cleared! You can proceed now.'
            );
        } else if (event.event_type === 'collaboration_proposed') {
            const choice = vscode.window.showInformationMessage(
                'Another dev wants to collaborate on this file',
                'Open chat',
                'Proceed anyway'
            );
        }
    }
}

export function activate(context: vscode.ExtensionContext) {
    const extension = new CoordinatedCopilotExtension();
    extension.activate(context);
}
```

### 2. Copilot Prompt Enhancement

```typescript
class CopilotPromptEnhancer {
    /**
     * Enhance Copilot's system prompt with coordination context.
     */
    
    async enhancePrompt(
        originalPrompt: string,
        conflictContext: any
    ): Promise<string> {
        
        let enhanced = originalPrompt;
        
        if (conflictContext.risk_score > 0) {
            enhanced += `

COORDINATION AWARENESS:
You are working in a shared codebase with other developers.

Other developers working on this file:
${conflictContext.conflicting_agents.map((agent: string) => `- ${agent}`).join('\n')}

Their work: ${conflictContext.conflict_details.join(', ')}

Guidelines:
1. Make minimal, focused changes
2. Avoid renaming or restructuring
3. Coordinate with their changes
4. Keep changes to your assigned region: ${conflictContext.region}
`;
        }
        
        return enhanced;
    }
}
```

### 3. GitHub Integration

```typescript
class GitHubCoordinationIntegration {
    /**
     * Sync coordination state with GitHub.
     * Store activity log in a special branch or discussion.
     */
    
    async syncToGitHub(
        owner: string,
        repo: string,
        activity: any
    ) {
        // Option 1: Commit to .devsync branch
        await this.commitActivityLog(owner, repo, activity);
        
        // Option 2: Update GitHub Discussion
        await this.updateGitHubDiscussion(owner, repo, activity);
        
        // Option 3: Create check run
        await this.createCheckRun(owner, repo, activity);
    }
    
    private async commitActivityLog(
        owner: string,
        repo: string,
        activity: any
    ) {
        const octokit = new Octokit({
            auth: process.env.GITHUB_TOKEN
        });
        
        // Append to .devsync/coordination.log.json
        const content = await octokit.rest.repos.getContent({
            owner,
            repo,
            path: '.devsync/coordination.log.json',
            ref: 'devsync-activity'
        });
        
        const currentLog = JSON.parse(
            Buffer.from((content.data as any).content, 'base64').toString()
        );
        
        currentLog.push(activity);
        
        await octokit.rest.repos.createOrUpdateFileContents({
            owner,
            repo,
            path: '.devsync/coordination.log.json',
            message: `Log: ${activity.agent_id} on ${activity.file_path}`,
            content: Buffer.from(JSON.stringify(currentLog, null, 2)).toString('base64'),
            branch: 'devsync-activity'
        });
    }
    
    private async updateGitHubDiscussion(
        owner: string,
        repo: string,
        activity: any
    ) {
        // Store in GitHub Discussions for visibility
        const octokit = new Octokit({
            auth: process.env.GITHUB_TOKEN
        });
        
        // Post comment in coordination discussion
        // (implementation depends on GitHub Discussion API)
    }
}
```

### 4. Local Conflict Detection in Editor

```typescript
class EditorConflictDetector {
    /**
     * Real-time conflict detection as developer types.
     * Show decorations/gutter warnings.
     */
    
    private decorationType = vscode.window.createTextEditorDecorationType({
        backgroundColor: new vscode.ThemeColor('editor.warningBackground'),
        border: '1px solid ' + new vscode.ThemeColor('editor.warningBorder')
    });
    
    async watchForConflicts(
        editor: vscode.TextEditor,
        coordination: CoordinationClient
    ) {
        let timeout: NodeJS.Timeout;
        
        editor.document.onDidChange(() => {
            clearTimeout(timeout);
            
            timeout = setTimeout(async () => {
                const filePath = editor.document.uri.fsPath;
                const region = this.getEditedRegion(editor);
                
                const check = await coordination.checkConflicts(
                    filePath,
                    region,
                    "Live editing"
                );
                
                if (check.risk_score > 50) {
                    this.showConflictDecoration(editor, check);
                }
            }, 500); // Debounce
        });
    }
    
    private showConflictDecoration(
        editor: vscode.TextEditor,
        conflict: any
    ) {
        const ranges: vscode.Range[] = [];
        
        // Parse region and create ranges
        const regex = /lines (\d+)-(\d+)/;
        const match = conflict.region?.match(regex);
        
        if (match) {
            const startLine = parseInt(match[1]) - 1;
            const endLine = parseInt(match[2]) - 1;
            
            for (let i = startLine; i <= endLine; i++) {
                ranges.push(
                    new vscode.Range(
                        new vscode.Position(i, 0),
                        new vscode.Position(i, Number.MAX_SAFE_INTEGER)
                    )
                );
            }
        }
        
        editor.setDecorations(this.decorationType, ranges);
        
        // Show info message
        vscode.window.showWarningMessage(
            `⚠️ ${conflict.conflicting_agents.join(', ')} are editing this area`
        );
    }
}
```

## Deployment

### Option 1: VS Code Marketplace

```json
{
  "name": "coordinated-copilot",
  "version": "1.0.0",
  "description": "Coordinate Copilot suggestions with team development",
  "publisher": "your-org",
  "engines": {
    "vscode": "^1.75.0"
  },
  "contributes": {
    "configuration": [
      {
        "title": "Coordinated Copilot",
        "properties": {
          "coordination.url": {
            "type": "string",
            "default": "http://localhost:8000",
            "description": "Coordination service URL"
          },
          "coordination.enabled": {
            "type": "boolean",
            "default": true,
            "description": "Enable coordination checks"
          }
        }
      }
    ]
  }
}
```

### Option 2: GitHub Copilot Server

Deploy as a custom Copilot server that intercepts suggestions:

```typescript
// copilot-server.ts
import { Hono } from 'hono';

const app = new Hono();

app.post('/completion', async (c) => {
    const request = await c.req.json();
    
    const coordination = new CoordinationClient();
    const check = await coordination.checkConflicts(
        request.filepath,
        request.position,
        "Copilot completion"
    );
    
    if (check.risk_score > 70) {
        // Return warning response
        return c.json({
            type: 'warning',
            message: 'High-risk region. Collaborate first.',
            proceed: false
        });
    }
    
    // Pass through to Copilot
    // (implementation depends on Copilot Server API)
});
```

## Multi-Developer Scenarios

### Scenario 1: Pair Programming

```typescript
// Auto-detect when two devs are on same file
class PairProgrammingDetector {
    async detectPairProgramming(
        coordination: CoordinationClient
    ): Promise<boolean> {
        const status = await coordination.getStatus();
        
        // Count developers on same file
        const fileMap = new Map();
        
        for (const entry of status) {
            if (!fileMap.has(entry.file)) {
                fileMap.set(entry.file, []);
            }
            fileMap.get(entry.file).push(entry.agent);
        }
        
        // If > 1 on same file, show pairing UI
        for (const [file, agents] of fileMap) {
            if (agents.length > 1) {
                vscode.window.showInformationMessage(
                    `Pair programming detected: ${agents.join(', ')} on ${file}`
                );
                return true;
            }
        }
        
        return false;
    }
}
```

### Scenario 2: Async Collaboration

```typescript
// When conflicts detected, enable async collab comments
class AsyncCollaborationUI {
    async showCollaborationWindow(
        conflict: any,
        coordination: CoordinationClient
    ) {
        const panel = vscode.window.createWebviewPanel(
            'coordination-collab',
            'Team Coordination',
            vscode.ViewColumn.Beside
        );
        
        panel.webview.html = `
            <h3>Coordinating with ${conflict.conflicting_agents.join(', ')}</h3>
            <p>${conflict.conflict_details}</p>
            
            <button id="wait">Wait for them (${conflict.estimated_wait}s)</button>
            <button id="collab">Collaborate in real-time</button>
            <button id="divide">Divide the work</button>
        `;
        
        // Handle button clicks
        // Send coordination decision back to service
    }
}
```

## Cost Estimation

| Component | Cost |
|-----------|------|
| VS Code Extension | Free (OSS) |
| Coordination Service | $30-100/month |
| GitHub API Usage | <$5/month |
| Hosting | $50-200/month |
| **Total** | **$80-305/month** |

## Getting Started

- [ ] Create VS Code extension
- [ ] Implement CoordinationClient
- [ ] Add pre/post suggestion hooks
- [ ] Test locally with Copilot
- [ ] Set up coordination service endpoint
- [ ] Publish to VS Code Marketplace
- [ ] Train team on usage

---

Compare implementations:
- `ENTERPRISE_SCALING_CLAUDE.md` - Claude API
- `ENTERPRISE_SCALING_OPENAI.md` - OpenAI GPT-4
- `ENTERPRISE_SCALING_DEVIN.md` - Devin autonomous agent

All frameworks use the same `CoordinationStateMachine` under the hood.
