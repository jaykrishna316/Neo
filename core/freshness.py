import json, os, time
from pathlib import Path
from typing import Optional, Dict, List
from core.symbol_hasher import snapshot_file, FileSnapshot, SymbolInfo

class FreshnessTracker:
    def __init__(self, state_dir: Optional[str] = None):
        self.state_dir = Path(state_dir or os.environ.get("NEO_STATE_DIR", ".neo_state"))
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.snapshots: Dict[str, Dict[str, FileSnapshot]] = {}
    
    def record_read(self, agent_id: str, file_path: str, symbols: Optional[List[str]] = None) -> None:
        snapshot = snapshot_file(file_path, agent_id, time.time())
        if Path(file_path).exists():
            snapshot.file_content = Path(file_path).read_text()
        if agent_id not in self.snapshots:
            self.snapshots[agent_id] = {}
        self.snapshots[agent_id][file_path] = snapshot
        self._save_snapshot(agent_id, file_path, snapshot)
    
    def check_freshness(self, agent_id: str, file_path: str) -> str:
        base = self._load_snapshot(agent_id, file_path)
        if not base: return "UNVERIFIABLE"
        current = snapshot_file(file_path, agent_id, time.time())
        if current.parse_error: return "UNVERIFIABLE"
        return "CURRENT" if base.content_hash == current.content_hash else "STALE_SOURCE"
    
    def delta_since_base(self, agent_id: str, file_path: str) -> str:
        base = self._load_snapshot(agent_id, file_path)
        if not base: return Path(file_path).read_text() if Path(file_path).exists() else ""
        current = snapshot_file(file_path, agent_id, time.time())
        changed_syms = [s for s in current.symbols if s not in base.symbols or base.symbols[s].body_hash != current.symbols[s].body_hash]
        return '\n'.join([f"Changed: {s}" for s in changed_syms]) if changed_syms else ""
    
    def _save_snapshot(self, agent_id: str, file_path: str, snap: FileSnapshot) -> None:
        snap_file = self.state_dir / f"{agent_id}_{Path(file_path).stem}.json"
        data = {
            "file_path": snap.file_path,
            "agent_id": snap.agent_id,
            "timestamp": snap.timestamp,
            "content_hash": snap.content_hash,
            "symbols": {n: {"name": s.name, "type": s.type, "lineno": s.lineno, "body_hash": s.body_hash, "signature": s.signature} for n, s in snap.symbols.items()},
            "file_content": snap.file_content
        }
        snap_file.write_text(json.dumps(data))
    
    def _load_snapshot(self, agent_id: str, file_path: str) -> Optional[FileSnapshot]:
        if agent_id in self.snapshots and file_path in self.snapshots[agent_id]:
            return self.snapshots[agent_id][file_path]
        snap_file = self.state_dir / f"{agent_id}_{Path(file_path).stem}.json"
        if not snap_file.exists(): return None
        try:
            data = json.loads(snap_file.read_text())
            symbols = {n: SymbolInfo(s["name"], s["type"], s["lineno"], s["body_hash"], s["signature"]) for n, s in data.get("symbols", {}).items()}
            snap = FileSnapshot(data["file_path"], data["agent_id"], data["timestamp"], symbols, data["content_hash"], data.get("file_content"))
            if agent_id not in self.snapshots: self.snapshots[agent_id] = {}
            self.snapshots[agent_id][file_path] = snap
            return snap
        except: return None

_tracker = None
def _get_tracker():
    global _tracker
    if not _tracker: _tracker = FreshnessTracker(os.environ.get("NEO_STATE_DIR", ".neo_state"))
    return _tracker

def record_read(agent_id: str, file_path: str, symbols: Optional[List[str]] = None) -> None:
    _get_tracker().record_read(agent_id, file_path, symbols)

def check_freshness(agent_id: str, file_path: str) -> str:
    return _get_tracker().check_freshness(agent_id, file_path)

def delta_since_base(agent_id: str, file_path: str) -> str:
    return _get_tracker().delta_since_base(agent_id, file_path)
