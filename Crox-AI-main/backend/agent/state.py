from typing import Any, Optional

from models.schemas import AgentState, HistoryEntry, LastResult, ToolResult, WorkflowPlan
from repositories.state_repository import StateRepository


class AgentStateManager:
    """Owns the in-memory AgentState for a single run and persists it to
    Supabase after every mutation so the run survives a backend restart.
    """

    def __init__(self, run_id: str, state: AgentState, repository: Optional[StateRepository] = None):
        self.run_id = run_id
        self.state = state
        self._repo = repository or StateRepository()

    @classmethod
    def new(
        cls, run_id: str, goal: str, plan: WorkflowPlan, repository: Optional[StateRepository] = None
    ) -> "AgentStateManager":
        state = AgentState(goal=goal, plan=plan)
        manager = cls(run_id, state, repository)
        manager.persist()
        return manager

    @classmethod
    def load(cls, run_id: str, repository: Optional[StateRepository] = None) -> Optional["AgentStateManager"]:
        repo = repository or StateRepository()
        row = repo.get(run_id)
        if not row:
            return None
        state = AgentState(
            goal=row["state"].get("goal", ""),
            plan=WorkflowPlan(**row["state"]["plan"]),
            current_objective=row["state"].get("current_objective"),
            completed_objectives=row["state"].get("completed_objectives", []),
            facts=row.get("facts", {}),
            execution_history=[HistoryEntry(**h) for h in row.get("execution_history", [])],
            last_result=LastResult(**row["state"]["last_result"]) if row["state"].get("last_result") else None,
        )
        return cls(run_id, state, repo)

    def set_current_objective(self, objective_id: Optional[str]) -> None:
        self.state.current_objective = objective_id
        self.persist()

    def mark_completed(self, objective_id: str) -> None:
        if objective_id and objective_id not in self.state.completed_objectives:
            self.state.completed_objectives.append(objective_id)
        self.persist()

    def update_facts(self, facts: dict[str, Any]) -> None:
        self.state.facts.update(facts)
        self.persist()

    def record_tool_call(self, tool: str, arguments: dict[str, Any], result: ToolResult, reason: str = "") -> None:
        self.state.execution_history.append(
            HistoryEntry(tool=tool, arguments=arguments, result=result, reason=reason)
        )
        self.state.last_result = LastResult(
            tool=tool, success=result.success, data=result.data, error=result.error
        )
        self.persist()

    def to_public_dict(self) -> dict[str, Any]:
        return self.state.model_dump()

    def persist(self) -> None:
        state_dict = self.state.model_dump(exclude={"facts", "execution_history"})
        self._repo.upsert(
            run_id=self.run_id,
            state=state_dict,
            facts=self.state.facts,
            execution_history=[h.model_dump() for h in self.state.execution_history],
        )
