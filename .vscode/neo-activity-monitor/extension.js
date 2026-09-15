const vscode = require('vscode');
const axios = require('axios');

let activityMonitor;
let notificationPoller;
let currentDeveloper = '';
let serverUrl = '';

class NeoActivityMonitor {
  constructor(context) {
    this.context = context;
    this.statusBar = null;
    this.workflowPanel = null;
    this.notifications = [];
    this.lastNotificationCheck = null;
    this.currentFile = '';
    this.currentFunction = '';
  }

  async initialize() {
    // Get settings
    const config = vscode.workspace.getConfiguration('neo');
    serverUrl = config.get('serverUrl') || process.env.ACTIVITY_LOG_SERVER || 'http://localhost:5000';
    currentDeveloper = config.get('developer') || process.env.USER || 'developer';

    if (!serverUrl) {
      vscode.window.showErrorMessage('Neo: ACTIVITY_LOG_SERVER not configured');
      return false;
    }

    // Test connection
    try {
      await axios.get(`${serverUrl}/health`);
      vscode.window.showInformationMessage(`✓ Connected to Activity Log Server: ${serverUrl}`);
      return true;
    } catch (error) {
      vscode.window.showErrorMessage(`✗ Cannot connect to Activity Log Server: ${serverUrl}`);
      return false;
    }
  }

  createStatusBar() {
    this.statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    this.statusBar.command = 'neo-activity-monitor.viewWorkflow';
    this.statusBar.text = '$(eye-closed) Neo';
    this.statusBar.tooltip = 'Click to view activity';
    this.statusBar.show();
  }

  updateStatusBar(state) {
    const icons = {
      available: '$(radio-tower)',
      editing: '$(circle-filled)',
      conflict_waiting: '$(warning)',
      pending_review: '$(merge)',
      both_done: '$(check-all)',
      in_pr: '$(git-pull-request)',
      approved: '$(verified)',
      merged: '$(git-merge)',
      rolled_back: '$(history)',
    };

    const icon = icons[state] || '$(eye-closed)';
    this.statusBar.text = `${icon} Neo: ${state}`;
  }

  startPollingNotifications() {
    // Poll for notifications every 5 seconds
    notificationPoller = setInterval(async () => {
      try {
        const response = await axios.get(`${serverUrl}/api/notifications`, {
          params: {
            developer: currentDeveloper,
            since: this.lastNotificationCheck,
          },
        });

        const newNotifications = response.data.notifications || [];
        if (newNotifications.length > 0) {
          this.handleNotifications(newNotifications);
          this.lastNotificationCheck = new Date().toISOString();
        }
      } catch (error) {
        // Silently fail - server might be down
      }
    }, 5000);
  }

  handleNotifications(notifications) {
    for (const notif of notifications) {
      switch (notif.type) {
        case 'lock_acquired':
          vscode.window.showInformationMessage(
            `🔒 ${notif.data.developer} started editing ${notif.function}`
          );
          break;

        case 'lock_blocked':
          vscode.window.showWarningMessage(
            `⏳ Waiting for ${notif.data.blocking_developer} to finish ${notif.function}`
          );
          break;

        case 'lock_released':
          vscode.window.showInformationMessage(
            `🔓 ${notif.data.developer} finished editing ${notif.function}`
          );
          break;

        case 'review_requested':
          const reviewAction = await vscode.window.showInformationMessage(
            `👀 Review ${notif.data.from_developer}'s changes to ${notif.function}?`,
            'Review',
            'Later'
          );
          if (reviewAction === 'Review') {
            this.autoPullBranch(notif.data.branch);
          }
          break;

        case 'approval_needed':
          vscode.window.showInformationMessage(
            `⭐ Your approval needed for ${notif.function} on PR #${notif.data.pr_number}`
          );
          break;

        case 'merged':
          vscode.window.showInformationMessage(
            `✅ ${notif.function} merged to main`
          );
          break;
      }

      this.notifications.push(notif);
    }
  }

  async autoPullBranch(branch) {
    try {
      const terminal = vscode.window.createTerminal('Neo: Auto-pull');
      terminal.sendText(`git fetch origin ${branch}`, true);
      terminal.sendText(`git checkout ${branch}`, true);
      terminal.show();
      vscode.window.showInformationMessage(`✓ Pulling ${branch}`);
    } catch (error) {
      vscode.window.showErrorMessage(`Failed to pull branch: ${error.message}`);
    }
  }

  async startEditing() {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
      vscode.window.showErrorMessage('No file open');
      return;
    }

    // Extract current function (simplified - just use filename for now)
    const file = editor.document.fileName;
    const relativePath = vscode.workspace.asRelativePath(file);

    try {
      const response = await axios.post(`${serverUrl}/api/start_editing`, {
        developer: currentDeveloper,
        file_path: relativePath,
        function_name: 'unknown', // Could extract from AST in production
      });

      if (response.data.success) {
        vscode.window.showInformationMessage(`✓ Lock acquired on ${relativePath}`);
        this.updateStatusBar('editing');
      } else {
        vscode.window.showWarningMessage(
          `⏳ Blocked: ${response.data.message}`
        );
        this.updateStatusBar('conflict_waiting');
      }
    } catch (error) {
      vscode.window.showErrorMessage(`Failed to acquire lock: ${error.message}`);
    }
  }

  async finishEditing() {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
      vscode.window.showErrorMessage('No file open');
      return;
    }

    const file = editor.document.fileName;
    const relativePath = vscode.workspace.asRelativePath(file);

    try {
      const response = await axios.post(`${serverUrl}/api/finish_editing`, {
        developer: currentDeveloper,
        file_path: relativePath,
        function_name: 'unknown',
      });

      if (response.data.success) {
        vscode.window.showInformationMessage(`✓ Lock released on ${relativePath}`);
        this.updateStatusBar('both_done');

        if (response.data.next_developer) {
          vscode.window.showInformationMessage(
            `Next: ${response.data.next_developer} should review your changes`
          );
        }
      } else {
        vscode.window.showErrorMessage(response.data.message);
      }
    } catch (error) {
      vscode.window.showErrorMessage(`Failed to release lock: ${error.message}`);
    }
  }

  async viewWorkflowState() {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
      vscode.window.showErrorMessage('No file open');
      return;
    }

    const file = editor.document.fileName;
    const relativePath = vscode.workspace.asRelativePath(file);

    try {
      const response = await axios.get(`${serverUrl}/api/workflow/state`, {
        params: {
          file_path: relativePath,
          function_name: 'unknown',
        },
      });

      const state = response.data;
      const webviewContent = this.getWebviewContent(state);

      if (!this.workflowPanel) {
        this.workflowPanel = vscode.window.createWebviewPanel(
          'neoWorkflow',
          'Neo Workflow State',
          vscode.ViewColumn.Beside,
          {}
        );
      }

      this.workflowPanel.webview.html = webviewContent;
      this.updateStatusBar(state.current_state);
    } catch (error) {
      vscode.window.showErrorMessage(`Failed to get workflow state: ${error.message}`);
    }
  }

  getWebviewContent(state) {
    return `
      <!DOCTYPE html>
      <html>
      <head>
        <style>
          body { font-family: -apple-system, sans-serif; padding: 20px; }
          .state { padding: 15px; background: #f5f5f5; border-radius: 4px; margin: 10px 0; }
          .status { font-size: 18px; font-weight: bold; color: #0066cc; }
          .info { margin: 10px 0; padding: 10px; background: white; border-left: 3px solid #0066cc; }
          .history { margin-top: 20px; }
          .transition { padding: 8px; border-left: 2px solid #ddd; margin: 5px 0; }
        </style>
      </head>
      <body>
        <h2>Workflow State</h2>
        <div class="state">
          <div class="status">${state.current_state?.toUpperCase() || 'UNKNOWN'}</div>
          <div class="info">
            <strong>Current Editor:</strong> ${state.current_editor || 'None'}<br/>
            <strong>Waiting:</strong> ${(state.waiting_developers || []).join(', ') || 'None'}<br/>
            <strong>Developers Involved:</strong> ${(state.all_developers || []).join(', ')}
          </div>
        </div>

        <h3>State History</h3>
        <div class="history">
          ${(state.state_history || []).reverse().map(h => `
            <div class="transition">
              <strong>${h.to_state.toUpperCase()}</strong> by ${h.actor || 'system'}<br/>
              <small>${h.reason}</small>
            </div>
          `).join('')}
        </div>
      </body>
      </html>
    `;
  }
}

function activate(context) {
  activityMonitor = new NeoActivityMonitor(context);

  // Initialize
  activityMonitor.initialize().then((success) => {
    if (!success) return;

    activityMonitor.createStatusBar();
    activityMonitor.startPollingNotifications();
  });

  // Register commands
  context.subscriptions.push(
    vscode.commands.registerCommand('neo-activity-monitor.startEditing', () => {
      activityMonitor.startEditing();
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('neo-activity-monitor.finishEditing', () => {
      activityMonitor.finishEditing();
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('neo-activity-monitor.viewWorkflow', () => {
      activityMonitor.viewWorkflowState();
    })
  );

  vscode.window.showInformationMessage('✓ Neo Activity Monitor activated');
}

function deactivate() {
  if (notificationPoller) {
    clearInterval(notificationPoller);
  }
}

module.exports = { activate, deactivate };
