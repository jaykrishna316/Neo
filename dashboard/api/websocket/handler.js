/**
 * WebSocket Handler
 * Manages real-time event broadcasting via Socket.io
 */

class WebSocketHandler {
  constructor(io, aggregator, logger) {
    this.io = io;
    this.aggregator = aggregator;
    this.logger = logger;
    this.subscriptions = new Map(); // Track subscriptions per socket
  }

  emitRefresh(socket, section) {
    return this.aggregator.emitRefresh(socket, section);
  }

  async broadcastMetrics() {
    try {
      const overview = await this.aggregator.getDashboardOverview();
      this.io.emit('metrics:overview', overview);
    } catch (err) {
      this.logger.error('Broadcast metrics error:', err);
    }
  }

  async broadcastActivityUpdate() {
    try {
      const feed = await this.aggregator.getActivityFeed(20);
      this.io.emit('activity:update', feed);
    } catch (err) {
      this.logger.error('Broadcast activity error:', err);
    }
  }

  async broadcastGraphUpdate() {
    try {
      const graph = await this.aggregator.getServicesGraph();
      this.io.emit('graph:update', graph);
    } catch (err) {
      this.logger.error('Broadcast graph error:', err);
    }
  }

  // Start periodic broadcasts (called from server)
  startPeriodicBroadcasts() {
    // Broadcast overview every 10 seconds
    setInterval(() => this.broadcastMetrics(), 10000);

    // Broadcast activity every 30 seconds
    setInterval(() => this.broadcastActivityUpdate(), 30000);

    // Broadcast graph every 60 seconds
    setInterval(() => this.broadcastGraphUpdate(), 60000);

    this.logger.info('WebSocket periodic broadcasts started');
  }
}

module.exports = (io, aggregator, logger) => {
  const handler = new WebSocketHandler(io, aggregator, logger);

  // Start broadcasts on initialization
  handler.startPeriodicBroadcasts();

  return handler;
};
