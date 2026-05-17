"""Kubernetes pod tools with MCP Elicitation for missing parameters."""

from mcp.types import ToolAnnotations

from core.server import mcp
from fastmcp import Context
from k8s_client import core_v1


def _list_namespaces() -> list[str]:
    return [ns.metadata.name for ns in core_v1().list_namespace().items]


def _list_pod_names(namespace: str) -> list[str]:
    return [p.metadata.name for p in core_v1().list_namespaced_pod(namespace).items]


async def _elicit_namespace(ctx: Context) -> str | None:
    namespaces = _list_namespaces()
    result = await ctx.elicit(
        message="Select namespace:",
        schema={
            "type": "object",
            "properties": {
                "namespace": {
                    "type": "string",
                    "title": "Namespace",
                    "enum": namespaces,
                }
            },
            "required": ["namespace"],
        },
    )
    if result.action != "accept":
        return None
    return result.data["namespace"]


@mcp.tool(
    annotations=ToolAnnotations(title="List Pods", readOnlyHint=True),
)
async def list_pods(namespace: str = "", ctx: Context = None) -> str:
    """List pods in a Kubernetes namespace.

    If namespace is not provided, elicits a selection from the user.
    """
    if not namespace:
        namespace = await _elicit_namespace(ctx)
        if namespace is None:
            return "Operation cancelled."

    pods = core_v1().list_namespaced_pod(namespace).items
    if not pods:
        return f"No pods found in namespace '{namespace}'."

    lines = [
        f"{p.metadata.name}  {p.status.phase}  {p.metadata.creation_timestamp}"
        for p in pods
    ]
    return f"Pods in '{namespace}':\n" + "\n".join(lines)


@mcp.tool(
    annotations=ToolAnnotations(title="Get Pod Logs", readOnlyHint=True),
)
async def get_pod_logs(
    namespace: str = "",
    pod_name: str = "",
    tail_lines: int = 100,
    ctx: Context = None,
) -> str:
    """Get logs from a Kubernetes pod.

    If namespace or pod_name are not provided, elicits selections from the user.
    """
    if not namespace:
        namespace = await _elicit_namespace(ctx)
        if namespace is None:
            return "Operation cancelled."

    if not pod_name:
        pod_names = _list_pod_names(namespace)
        if not pod_names:
            return f"No pods found in namespace '{namespace}'."

        result = await ctx.elicit(
            message=f"Select pod in '{namespace}':",
            schema={
                "type": "object",
                "properties": {
                    "pod_name": {
                        "type": "string",
                        "title": "Pod",
                        "enum": pod_names,
                    }
                },
                "required": ["pod_name"],
            },
        )
        if result.action != "accept":
            return "Operation cancelled."
        pod_name = result.data["pod_name"]

    logs = core_v1().read_namespaced_pod_log(
        name=pod_name,
        namespace=namespace,
        tail_lines=tail_lines,
    )
    return logs or f"No logs found for pod '{pod_name}'."
