import json
from pathlib import Path
from typing import Any
from src.core.types import RunState

def read_json(file_path: Path) -> Any:
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def write_json(file_path: Path, value: Any) -> None:
    # Ensure parent directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        # If it's a Pydantic model, convert to dict first
        if hasattr(value, "model_dump"):
            dumped = value.model_dump(exclude_none=True)
        elif isinstance(value, dict):
            dumped = {}
            for k, v in value.items():
                # Convert keys if they are Platform Enum
                key_str = k.value if hasattr(k, "value") else str(k)
                if hasattr(v, "model_dump"):
                    dumped[key_str] = v.model_dump(exclude_none=True)
                else:
                    dumped[key_str] = v
        else:
            dumped = value
            
        json.dump(dumped, f, indent=2, ensure_ascii=False)
        f.write("\n")

def read_state(file_path: Path) -> RunState:
    data = read_json(file_path)
    return RunState.model_validate(data)
