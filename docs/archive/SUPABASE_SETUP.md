# Neo Phase 2: Supabase Cloud Setup

This guide walks through setting up Neo with Supabase for cloud-based coordination.

---

## What is Supabase?

Supabase is an open-source Firebase alternative that provides:
- PostgreSQL database (hosted in the cloud)
- Real-time subscriptions
- Row-level security
- RESTful API
- Free tier for development

---

## Step 1: Create a Supabase Project

### 1.1 Sign Up
1. Go to [supabase.com](https://supabase.com)
2. Click "Start your project"
3. Sign up with email or GitHub

### 1.2 Create a New Project
1. Click "New Project"
2. Fill in:
   - **Project name**: "neo-coordination" (or your choice)
   - **Database password**: Save this securely
   - **Region**: Choose closest to your location
3. Click "Create new project"

Wait 2-3 minutes for the project to initialize.

---

## Step 2: Create Activity Log Schema

### 2.1 Access the Database
1. In Supabase dashboard, click **SQL Editor** (left sidebar)
2. Click **New Query**

### 2.2 Create Table
Copy and paste this SQL query:

```sql
-- Create activity_log table
CREATE TABLE IF NOT EXISTS activity_log (
  id BIGSERIAL PRIMARY KEY,
  
  -- Core fields
  developer_id TEXT NOT NULL,
  file_path TEXT NOT NULL,
  intent TEXT NOT NULL,
  region TEXT,
  timestamp DOUBLE PRECISION NOT NULL,
  
  -- Multitenancy
  tenant_id TEXT NOT NULL DEFAULT 'default',
  
  -- Metadata
  agent_metadata JSONB,
  intent_category TEXT,
  intent_scope TEXT,
  blocking_others BOOLEAN DEFAULT false,
  estimated_completion INTEGER,
  
  -- Lock fields
  lock_state TEXT,                    -- "ACQUIRED", "WAITING", "RELEASED"
  lock_holder TEXT,
  lock_acquired_at DOUBLE PRECISION,
  lock_expires_at DOUBLE PRECISION,
  lock_timeout_seconds INTEGER DEFAULT 1800,
  lock_reason TEXT,                   -- "MEDIUM_CONFLICT", "HIGH_CONFLICT"
  lock_scope TEXT,                    -- "file", "function", "region"
  queue_position INTEGER,
  waiting_for TEXT,
  
  -- Timestamps
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_activity_log_tenant_id ON activity_log(tenant_id);
CREATE INDEX idx_activity_log_developer_id ON activity_log(developer_id);
CREATE INDEX idx_activity_log_file_path ON activity_log(file_path);
CREATE INDEX idx_activity_log_timestamp ON activity_log(timestamp);
CREATE INDEX idx_activity_log_lock_state ON activity_log(lock_state);

-- Enable Row Level Security
ALTER TABLE activity_log ENABLE ROW LEVEL SECURITY;

-- Create policy: Allow all reads/writes for now (secure later)
CREATE POLICY "Allow all access" ON activity_log
  FOR ALL
  USING (true)
  WITH CHECK (true);
```

3. Click **Run** (or Ctrl+Enter)

### 2.3 Verify Table Creation
1. Click **Table Editor** (left sidebar)
2. You should see `activity_log` table
3. Click it to view the schema

---

## Step 3: Get Your Credentials

### 3.1 Find Project URL and Key
1. Click **Settings** (gear icon, bottom left)
2. Click **API**
3. You'll see:
   - **Project URL**: `https://[project-id].supabase.co`
   - **Anon Key**: (public key for client requests)

### 3.2 Copy Credentials
Copy both values — you'll need them for `.env` file

---

## Step 4: Configure Neo

### 4.1 Update `.env` File
Create or update `.env` in Neo root:

```bash
# Copy from .env.example
cp .env.example .env

# Edit .env with your Supabase credentials
ACTIVITY_LOG_MODE=supabase
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-anon-key-here
```

### 4.2 Install Supabase SDK
```bash
pip install supabase-py
```

---

## Step 5: Test Cloud Connection

### 5.1 Run Connection Test
```bash
# Test that Neo can connect to Supabase
python -c "
import os
os.environ['ACTIVITY_LOG_MODE'] = 'supabase'
from core.activity_log_adapter import ActivityLogAdapter
entries = ActivityLogAdapter.read_log()
print(f'✅ Connected to Supabase. Entries: {len(entries)}')
"
```

Expected output: `✅ Connected to Supabase. Entries: 0`

### 5.2 Run Full Test Suite
```bash
# Run existing tests with cloud storage
ACTIVITY_LOG_MODE=supabase python tests/test_two_developer_coordination.py
ACTIVITY_LOG_MODE=supabase python tests/test_three_developer_coordination.py
ACTIVITY_LOG_MODE=supabase python tests/test_edge_cases.py
```

Expected: All tests PASS with cloud storage

---

## Step 6: Verify Data in Supabase

### 6.1 View Entries in Dashboard
1. Go to **Table Editor**
2. Click **activity_log**
3. You should see test entries from the test runs

### 6.2 Query Directly
In **SQL Editor**, run:
```sql
SELECT developer_id, file_path, intent, lock_state, timestamp 
FROM activity_log 
ORDER BY timestamp DESC 
LIMIT 10;
```

---

## Troubleshooting

### "SUPABASE_URL and SUPABASE_KEY environment variables required"
**Fix**: Check that `.env` file is in Neo root directory and properly formatted

### "Failed to connect to Supabase"
**Fix**: 
1. Verify URL and Key are correct in `.env`
2. Check that Supabase project is active (not paused)
3. Run: `curl https://your-url.supabase.co` to test connectivity

### "Table activity_log does not exist"
**Fix**: Re-run the SQL schema creation query in Step 2.2

### Tests fail with "Connection refused"
**Fix**: Ensure `ACTIVITY_LOG_MODE=supabase` environment variable is set before running tests

---

## Next Steps

Once cloud storage is working:

1. **Part 2**: Update MCP Server for cloud connectivity
2. **Part 3**: Integrate with Claude Code IDE
3. **Part 4**: Enable multi-team isolation

See `PHASE_2_ROADMAP.md` for full implementation timeline.

---

## Security Notes

### For Development (Current Setup)
- Row Level Security (RLS) is enabled but allows all access
- This is fine for local testing and non-sensitive data

### For Production
Later, implement proper RLS policies:
```sql
-- Example: Only allow developers to see their own activities
CREATE POLICY "Users can view own activities"
  ON activity_log FOR SELECT
  USING (developer_id = auth.uid()::text);
```

---

## Cost Estimation

**Supabase Pricing**:
- Free tier: Up to 50 GB database, 2 GB bandwidth
- Pro tier: $25/month for 500 GB
- For Neo coordination: Free tier is sufficient for most teams

**Estimated Usage** (per month):
- Database storage: < 100 MB (activity log only)
- API calls: 1000s per month (minimal)
- **Total cost**: Free or $25/month

---

## References

- [Supabase Documentation](https://supabase.com/docs)
- [Supabase Python SDK](https://github.com/supabase/supabase-py)
- [PostgreSQL JSON/JSONB](https://www.postgresql.org/docs/current/datatype-json.html)
