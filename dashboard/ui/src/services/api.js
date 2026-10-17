/**
 * API Service
 * Handles all HTTP requests to the dashboard API
 */

const BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:3001';

class API {
  async request(endpoint, options = {}) {
    try {
      const url = `${BASE_URL}${endpoint}`;
      const response = await fetch(url, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers
        },
        ...options
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.statusText}`);
      }

      return await response.json();
    } catch (err) {
      console.error(`API request failed: ${endpoint}`, err);
      throw err;
    }
  }

  // Dashboard endpoints
  async getDashboardOverview() {
    const res = await this.request('/api/dashboard/overview');
    return res.data;
  }

  async getServicesGraph() {
    const res = await this.request('/api/dashboard/graph');
    return res.data;
  }

  async getConflictHeatmap() {
    const res = await this.request('/api/dashboard/heatmap');
    return res.data;
  }

  async getDashboardMetrics(metric, points = 100) {
    const res = await this.request(`/api/dashboard/metrics/${metric}?points=${points}`);
    return res.data;
  }

  // Services endpoints
  async getServiceCoupling() {
    const res = await this.request('/api/services/coupling');
    return res.data;
  }

  async getServiceTrends(service, window = 90) {
    const res = await this.request(`/api/services/${service}/trends?window=${window}`);
    return res.data;
  }

  async getServiceBlastRadius(service, changeType = 'modification') {
    const res = await this.request(
      `/api/services/${service}/blast-radius?change_type=${changeType}`
    );
    return res.data;
  }

  async getEntropyAnalysis(window = 90) {
    const res = await this.request(`/api/services/entropy/analysis?window=${window}`);
    return res.data;
  }

  // Activity endpoints
  async getActivityFeed(limit = 50) {
    const res = await this.request(`/api/activity/feed?limit=${limit}`);
    return res.data;
  }

  async getDeveloperActivity(agentId, limit = 50) {
    const res = await this.request(`/api/activity/developer/${agentId}?limit=${limit}`);
    return res.data;
  }

  async getFileActivity(filePath, limit = 50) {
    const res = await this.request(`/api/activity/file/${filePath}?limit=${limit}`);
    return res.data;
  }

  async getActivitySummary() {
    const res = await this.request('/api/activity/summary');
    return res.data;
  }
}

export default new API();
