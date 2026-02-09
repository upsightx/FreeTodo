"""AgentOS entrypoint for FreeTodo (Agno)."""

from __future__ import annotations

from agno.os import AgentOS

from lifetrace.llm.agent_os_tools import (
    agent_os_session_end,
    agent_os_session_start,
    agent_os_tool_guard,
    build_agent_os_external_tools,
    get_all_freetodo_tools,
)
from lifetrace.llm.agno_agent import DEFAULT_LANG, AgnoAgentService
from lifetrace.util.agent_os_utils import select_agent_os_port, write_agent_os_port_file
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
    if not selected_tools:
        selected_tools = get_all_freetodo_tools()

    external_tools = _normalize_list(settings.get("agno.agent_os.external_tools"))

    agent_id = settings.get("agno.agent_os.agent_id", "freetodo-agent")
    agent_name = settings.get("agno.agent_os.agent_name", "FreeTodo Agent")
    extra_tools = build_agent_os_external_tools(allowed_tools=external_tools)
    tool_hooks = [agent_os_tool_guard]
    pre_hooks = [agent_os_session_start]
    post_hooks = [agent_os_session_end]

    service = AgnoAgentService(
        lang=lang,
        selected_tools=selected_tools,
        extra_tools=extra_tools,
        tool_hooks=tool_hooks,
        pre_hooks=pre_hooks,
        post_hooks=post_hooks,
        agent_id=agent_id,
        agent_name=agent_name,
    )
    return service.agent


agent_os = AgentOS(agents=[_build_agent()])
app = agent_os.get_app()


if __name__ == "__main__":
    host = str(settings.get("agno.agent_os.host", "127.0.0.1"))
    port = select_agent_os_port(host)
    write_agent_os_port_file(host, port)
    agent_os.serve(
        app="lifetrace.agent_os:app",
        host=host,
        port=port,
        reload=settings.server.debug,
    )
