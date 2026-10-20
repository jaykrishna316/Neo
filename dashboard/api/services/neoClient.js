/**
 * Neo MCP Client
 * Bridges dashboard to Neo's conflict detection and analysis tools
 */

const { spawn } = require('child_process');
const path = require('path');

class NeoClient {
  constructor(logger) {
    this.logger = logger;
    this.process = null;
    this.isConnected = false;
    this.requestId = 0;
    this.pendingRequests = new Map();
    this.moreNeoPath = process.env.NEO_MCP_PATH || path.join(__dirname, '../../ide/mcp_neo_server.py');
  }

  async initialize() {
    return new Promise((resolve, reject) => {
      try {
        this.process = spawn('python3', ['-m', 'ide.mcp_neo_server'], {
          env: {
            ...process.env,
            PYTHONPATH: path.join(__dirname, '../..'),
            NEO_MULTITENANCY: process.env.NEO_MULTITENANCY || 'false',
            CLAUDE_TENANT_ID: process.env.CLAUDE_TENANT_ID || 'default'
          },
          stdio: ['pipe', 'pipe', 'pipe']
        });

        this.process.on('error', (err) => {
          this.logger.error('Neo process error:', err);
          this.isConnected = false;
        });

        this.process.stderr.on('data', (data) => {
          this.logger.error('Neo stderr:', data.toString());
        });

        this.process.stdout.on('data', (data) => {
          this.handleProcessOutput(data.toString());
        });

        // Simple readiness check
        setTimeout(() => {
          this.isConnected = true;
          this.logger.info('Neo MCP client initialized');
          resolve();
        }, 1000);
      } catch (err) {
        this.logger.error('Failed to initialize Neo client:', err);
        reject(err);
      }
    });
  }

  handleProcessOutput(data) {
    // Parse JSON-RPC responses from Neo MCP server
    const lines = data.trim().split('\n');
    lines.forEach((line) => {
      if (line.trim()) {
        try {
          const response = JSON.parse(line);
          if (response.id && this.pendingRequests.has(response.id)) {
            const { resolve, reject } = this.pendingRequests.get(response.id);
            this.pendingRequests.delete(response.id);
            if (response.error) {
              reject(new Error(response.error.message));
            } else {
              resolve(response.result);
            }
          }
        } catch (err) {
          this.logger.debug('Non-JSON output from Neo:', line);
        }
      }
    });
  }

  async callTool(toolName, params) {
    if (!this.isConnected) {
      throw new Error('Neo MCP client not connected');
    }

    const id = ++this.requestId;
    const request = {
      jsonrpc: '2.0',
      id,
      method: 'tools/call',
      params: {
        name: toolName,
        arguments: params
      }
    };

    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.pendingRequests.delete(id);
        reject(new Error(`Neo tool call timeout: ${toolName}`));
      }, 30000);

      this.pendingRequests.set(id, {
        resolve: (result) => {
          clearTimeout(timeout);
          resolve(result);
        },
        reject: (error) => {
          clearTimeout(timeout);
          reject(error);
        }
      });

      this.process.stdin.write(JSON.stringify(request) + '\n');
    });
  }

  // High-level API methods
  async checkConflicts(agentId, filePath, intent, region = 'all') {
    try {
      const result = await this.callTool('neo_check_conflicts', {
        agent_id: agentId,
        file_path: filePath,
        intent,
        region
      });
      return result;
    } catch (err) {
      this.logger.error('Conflict check failed:', err);
      return { risk_level: 'ERROR', message: err.message };
    }
  }

  async calculateBlastRadius(agentId, filePath, changeType) {
    try {
      const result = await this.callTool('neo_calculate_blast_radius', {
        agent_id: agentId,
        file_path: filePath,
        change_type: changeType
      });
      return result;
    } catch (err) {
      this.logger.error('Blast radius calculation failed:', err);
      return { complexity: 'UNKNOWN', affected_files: [], estimated_dev_hours: 0, token_estimate: 0 };
    }
  }

  async getCouplingTrends(filePath, window = 90) {
    try {
      const result = await this.callTool('neo_get_coupling_trends', {
        file_path: filePath,
        window_days: window
      });
      return result;
    } catch (err) {
      this.logger.error('Coupling trends fetch failed:', err);
      return { velocity: 0, trend_direction: 'STABLE', coupled_services: [] };
    }
  }

  async analyzeEntropyCoupling(window = 90) {
    try {
      const result = await this.callTool('neo_analyze_entropy_coupling', {
        window_days: window
      });
      return result;
    } catch (err) {
      this.logger.error('Entropy analysis failed:', err);
      return {
        services: [],
        architectual_issues: [],
        data_age_days: null,
        is_meaningful: false
      };
    }
  }

  async getActiveWork() {
    try {
      const result = await this.callTool('neo_get_active_work', {});
      return result;
    } catch (err) {
      this.logger.error('Active work fetch failed:', err);
      return { entries: [] };
    }
  }

  async getStatus() {
    try {
      const result = await this.callTool('neo_get_status', {});
      return result;
    } catch (err) {
      this.logger.error('Status check failed:', err);
      return {
        status: 'DISCONNECTED',
        version: 'unknown',
        features: []
      };
    }
  }

  async shutdown() {
    if (this.process) {
      this.process.kill();
      this.isConnected = false;
    }
  }
}

module.exports = NeoClient;
