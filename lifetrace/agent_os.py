"""AgentOS entrypoint for FreeTodo (Agno)."""

from __future__ import annotations

from agno.os import AgentOS

from lifetrace.llm.agno_agent import DEFAULT_LANG, AgnoAgentService
from lifetrace.util.settings import settings


def _normalize_list(value) -> list[str] | None:
    if not value:
        return None
    if isinstance(value, list | tuple):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return None


def _build_agent():
    lang = settings.get("agno.agent_os.lang", DEFAULT_LANG)
    selected_tools = _normalize_list(settings.get("agno.agent_os.selected_tools"))
    external_tools = _normalize_list(settings.get("agno.agent_os.external_tools"))
    external_tools_config = settings.get("agno.agent_os.external_tools_config", {}) or {}
    if not isinstance(external_tools_config, dict):
        external_tools_config = {}

    service = AgnoAgentService(
        lang=lang,
        selected_tools=selected_tools,
        external_tools=external_tools,
        external_tools_config=external_tools_config,
    )
    return service.agent


agent_os = AgentOS(agents=[_build_agent()])
app = agent_os.get_app()


if __name__ == "__main__":
    agent_os.serve(app="lifetrace.agent_os:app", reload=settings.server.debug)
