from dataclasses import dataclass
from typing import Dict, List, Optional
from core.symbol_hasher import FileSnapshot

@dataclass
class SymbolDelta:
    name: str
    type: str
    body: Optional[str] = None

@dataclass
class FileDelta:
    file_path: str
    delta_type: str
    symbol_deltas: List[SymbolDelta] = None
    changed_symbols: List[str] = None

class DeltaGenerator:
    @staticmethod
    def generate(base_snap: FileSnapshot, current_file_path: str, dep_syms: Optional[List[str]] = None) -> FileDelta:
        import time
        from core.symbol_hasher import snapshot_file
        current_snap = snapshot_file(current_file_path, base_snap.agent_id, time.time())
        if current_snap.parse_error:
            return FileDelta(current_file_path, "full_file", changed_symbols=[])
        
        changed = []
        deltas = []
        for sym in current_snap.symbols:
            if sym not in base_snap.symbols or base_snap.symbols[sym].body_hash != current_snap.symbols[sym].body_hash:
                changed.append(sym)
                deltas.append(SymbolDelta(sym, "changed", current_snap.symbols[sym].signature))
        
        return FileDelta(current_file_path, "symbols", deltas, changed)

class ContextRefreshBuilder:
    @staticmethod
    def build_message(deltas: List[FileDelta], agent_id: str, file_path: str) -> str:
        return f"Context refresh for {agent_id}: {len(deltas)} changes"
