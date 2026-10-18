#!/usr/bin/env node

// Real-time activity monitor for 2-developer test
// Watches .devsync/activity-log.json and displays Neo's conflict detection in real-time

const fs = require('fs');
const path = require('path');
const http = require('http');

const LOG_FILE = path.join(__dirname, '..', '.devsync', 'activity-log.json');
const HEALTH_URL = 'http://localhost:3001/health';
const ACTIVITY_URL = 'http://localhost:3001/api/activity/feed';

let lastLog = null;
let updateCount = 0;

function fetchJSON(url) {
  return new Promise((resolve, reject) => {
    http.get(url, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          resolve(JSON.parse(data));
        } catch (e) {
          reject(e);
        }
      });
    }).on('error', reject);
  });
}

function detectConflicts(entries) {
  const fileMap = {};
  const conflicts = [];

  entries.forEach(entry => {
    const { file_path, agent_id, timestamp, intent } = entry;
    if (!fileMap[file_path]) fileMap[file_path] = [];
    fileMap[file_path].push({ agent_id, timestamp, intent });
  });

  // Check for multiple developers touching same file
  Object.entries(fileMap).forEach(([file, devs]) => {
    const uniqueDevs = [...new Set(devs.map(d => d.agent_id))];
    if (uniqueDevs.length > 1) {
      const timeSpan = new Date(devs[devs.length - 1].timestamp) - new Date(devs[0].timestamp);
      conflicts.push({
        file,
        developers: uniqueDevs,
        entries: devs.length,
        timeSpanMs: timeSpan,
        riskLevel: timeSpan < 60000 ? 'HIGH' : timeSpan < 300000 ? 'MEDIUM' : 'LOW'
      });
    }
  });

  return conflicts;
}

function formatTime(ms) {
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function displayUpdate(entries) {
  updateCount++;
  console.clear();

  console.log('\n' + '═'.repeat(70));
  console.log('  NEO CONFLICT DETECTION - 2-DEVELOPER REAL-TIME TEST');
  console.log('═'.repeat(70));

  // Activity summary
  console.log('\n📊 ACTIVITY SUMMARY:');
  console.log(`   Total Entries: ${entries.length}`);
  console.log(`   Updates Detected: ${updateCount}`);

  const devs = [...new Set(entries.map(e => e.agent_id))];
  console.log(`   Active Developers: ${devs.length}`);
  devs.forEach(dev => {
    const count = entries.filter(e => e.agent_id === dev).length;
    console.log(`     • ${dev}: ${count} entries`);
  });

  // File modification map
  const fileMap = {};
  entries.forEach(e => {
    if (!fileMap[e.file_path]) fileMap[e.file_path] = [];
    fileMap[e.file_path].push(e.agent_id);
  });

  console.log('\n📁 FILES BEING MODIFIED:');
  Object.entries(fileMap).forEach(([file, devs]) => {
    const uniqueDevs = [...new Set(devs)];
    const icon = uniqueDevs.length > 1 ? '⚠️ ' : '✅';
    console.log(`   ${icon} ${file} (${devs.length} changes by ${uniqueDevs.length} dev${uniqueDevs.length > 1 ? 's' : ''})`);
  });

  // Conflict detection
  const conflicts = detectConflicts(entries);

  console.log('\n🔴 CONFLICT DETECTION:');
  if (conflicts.length === 0) {
    console.log('   ✅ No conflicts detected');
  } else {
    conflicts.forEach(conflict => {
      const riskColor = conflict.riskLevel === 'HIGH' ? '🔴' : conflict.riskLevel === 'MEDIUM' ? '🟠' : '🟡';
      console.log(`   ${riskColor} ${conflict.file}`);
      console.log(`      Developers: ${conflict.developers.join(', ')}`);
      console.log(`      Changes: ${conflict.entries}, TimeSpan: ${formatTime(conflict.timeSpanMs)}`);
      console.log(`      Risk Level: ${conflict.riskLevel}`);
    });
  }

  // Intents and context
  console.log('\n💡 DEVELOPER INTENTS:');
  entries.slice(-10).forEach(entry => {
    const time = new Date(entry.timestamp).toLocaleTimeString();
    console.log(`   [${time}] ${entry.agent_id}: "${entry.intent}"`);
    console.log(`      File: ${entry.file_path}`);
  });

  // Service impact analysis
  const apiFiles = entries.filter(e => e.file_path.includes('api'));
  const uiFiles = entries.filter(e => e.file_path.includes('ui'));
  const coreFiles = entries.filter(e => e.file_path.includes('core'));

  console.log('\n🔗 SERVICE COUPLING IMPACTS:');
  console.log(`   API Layer:  ${apiFiles.length} changes → affects Dashboard UI`);
  console.log(`   UI Layer:   ${uiFiles.length} changes → depends on API`);
  console.log(`   Core:       ${coreFiles.length} changes → affects both`);

  // Context staleness detection
  console.log('\n⏰ CONTEXT STALENESS:');
  const now = Date.now();
  let staleSessions = 0;
  entries.forEach(entry => {
    const age = now - new Date(entry.timestamp).getTime();
    if (age > 300000) staleSessions++;
  });
  console.log(`   Sessions with stale context: ${staleSessions}`);
  if (staleSessions > 0) {
    console.log('   ⚠️ WARNING: Context older than 5 minutes detected');
  }

  // Blast radius estimate
  const touchedFiles = Object.keys(fileMap).length;
  const uniqueDeveloperIds = [...new Set(entries.map(e => e.agent_id))];
  const estimatedBlastRadius = Math.min(100, Math.round((touchedFiles / entries.length) * 50 + (conflicts.length * 25)));

  console.log('\n💥 BLAST RADIUS ESTIMATION:');
  console.log(`   Files Touched: ${touchedFiles}`);
  console.log(`   Concurrent Developers: ${uniqueDeveloperIds.length}`);
  console.log(`   Estimated Impact: ${estimatedBlastRadius}%`);
  console.log(`   Risk Assessment: ${estimatedBlastRadius > 70 ? '🔴 CRITICAL' : estimatedBlastRadius > 40 ? '🟠 HIGH' : '🟡 MEDIUM'}`);

  console.log('\n' + '═'.repeat(70) + '\n');
}

async function monitor() {
  console.log('🚀 Starting Neo Activity Monitor...');
  console.log('   Watching: ' + LOG_FILE);
  console.log('   API: ' + ACTIVITY_URL);
  console.log('\n   Waiting for developer activity...\n');

  let pollCount = 0;

  setInterval(async () => {
    try {
      const data = await fetchJSON(ACTIVITY_URL);
      const entries = data.entries || [];

      if (entries.length > 0 && JSON.stringify(entries) !== lastLog) {
        lastLog = JSON.stringify(entries);
        displayUpdate(entries);
      }
    } catch (e) {
      pollCount++;
      if (pollCount % 10 === 0) {
        console.log('⏳ Waiting for API server... (' + pollCount * 2 + 's)');
      }
    }
  }, 2000);
}

monitor().catch(console.error);
