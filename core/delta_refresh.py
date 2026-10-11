import ast
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

        # Read source for body extraction
        try:
            with open(current_file_path, 'r') as f:
                source = f.read()
            tree = ast.parse(source)
        except:
            tree = None

        for sym in current_snap.symbols:
            if sym not in base_snap.symbols:
                # Added symbol
                body = DeltaGenerator._extract_body(tree, sym, source) if tree else None
                deltas.append(SymbolDelta(sym, "added", body))
                changed.append(sym)
            elif base_snap.symbols[sym].body_hash != current_snap.symbols[sym].body_hash:
                # Changed symbol
                body = DeltaGenerator._extract_body(tree, sym, source) if tree else None
                deltas.append(SymbolDelta(sym, "changed", body))
                changed.append(sym)

        return FileDelta(current_file_path, "symbols", deltas, changed)

    @staticmethod
    def _extract_body(tree, sym_name: str, source: str) -> Optional[str]:
        """Extract the body of a symbol from AST."""
        if not tree:
            return None

        lines = source.split('\n')
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.name == sym_name:
                    try:
                        start = node.lineno - 1
                        end = node.end_lineno
                        if start >= 0 and end <= len(lines):
                            return '\n'.join(lines[start:end])
                    except:
                        pass
        return None

class ContextRefreshBuilder:
    @staticmethod
    def build_message(deltas: List[FileDelta], agent_id: str, file_path: str) -> str:
        return f"Context refresh for {agent_id}: {len(deltas)} changes"
