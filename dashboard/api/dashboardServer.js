// Dashboard HTTP server - serves pro-dashboard.html on port 3000
const http = require('http');
const fs = require('fs');
const path = require('path');
const url = require('url');

const dashboardPath = path.join(__dirname, '..', 'pro-dashboard.html');

const server = http.createServer((req, res) => {
  const parsedUrl = url.parse(req.url, true);
  const pathname = parsedUrl.pathname;

  // CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }

  // Serve the dashboard
  if (pathname === '/' || pathname === '/dashboard') {
    res.setHeader('Content-Type', 'text/html');
    res.writeHead(200);
    fs.createReadStream(dashboardPath).pipe(res);
  } else {
    res.writeHead(404);
    res.end(JSON.stringify({ error: 'Not found' }));
  }
});

const PORT = 3000;
server.listen(PORT, () => {
  console.log('\n🎨 Neo Dashboard running on http://localhost:' + PORT);
  console.log('📡 API Server: http://localhost:3001');
  console.log('🔄 Real-time updates: WebSocket ready\n');
});

process.on('SIGINT', () => {
  console.log('\n👋 Dashboard shutdown...');
  server.close();
  process.exit(0);
});
