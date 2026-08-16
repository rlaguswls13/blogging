from datetime import datetime
from src.core.paths import run_directory
from src.core.files import read_state, write_json
from src.core.types import WorkflowStatus

def approve_run(run_id: str) -> None:
    state_path = run_directory(run_id) / "state.json"
    state = read_state(state_path)
    
    if state.status == WorkflowStatus.PUBLISHED:
        raise ValueError("이미 게시된 실행은 다시 승인할 수 없습니다.")
        
    state.status = WorkflowStatus.APPROVED
    state.humanApproved = True
    state.updatedAt = datetime.utcnow().isoformat() + "Z"
    
    write_json(state_path, state)
