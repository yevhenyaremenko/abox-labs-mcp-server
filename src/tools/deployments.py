"""Kubernetes deployment tools with MCP Elicitation for missing parameters."""

from mcp.types import ToolAnnotations

from core.server import mcp
from fastmcp import Context
from k8s_client import apps_v1, core_v1


def _list_namespaces() -> list[str]:
    return [ns.metadata.name for ns in core_v1().list_namespace().items]


def _list_deployment_names(namespace: str) -> list[str]:
    return [
        d.metadata.name
        for d in apps_v1().list_namespaced_deployment(namespace).items
    ]


@mcp.tool(
    annotations=ToolAnnotations(title="Scale Deployment", readOnlyHint=False),
)
async def scale_deployment(
    namespace: str = "",
    deployment: str = "",
    replicas: int = -1,
    ctx: Context = None,
) -> str:
    """Scale a Kubernetes deployment to the desired number of replicas.

    Elicits namespace, deployment name, and replica count when not provided.
    """
    if not namespace:
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
            return "Operation cancelled."
        namespace = result.data["namespace"]

    if not deployment:
        deployment_names = _list_deployment_names(namespace)
        if not deployment_names:
            return f"No deployments found in namespace '{namespace}'."

        result = await ctx.elicit(
            message=f"Select deployment in '{namespace}':",
            schema={
                "type": "object",
                "properties": {
                    "deployment": {
                        "type": "string",
                        "title": "Deployment",
                        "enum": deployment_names,
                    }
                },
                "required": ["deployment"],
            },
        )
        if result.action != "accept":
            return "Operation cancelled."
        deployment = result.data["deployment"]

    if replicas < 0:
        result = await ctx.elicit(
            message=f"How many replicas for '{deployment}'?",
            schema={
                "type": "object",
                "properties": {
                    "replicas": {
                        "type": "integer",
                        "title": "Replicas",
                        "minimum": 0,
                        "maximum": 20,
                    }
                },
                "required": ["replicas"],
            },
        )
        if result.action != "accept":
            return "Operation cancelled."
        replicas = result.data["replicas"]

    apps_v1().patch_namespaced_deployment_scale(
        name=deployment,
        namespace=namespace,
        body={"spec": {"replicas": replicas}},
    )
    return f"Deployment '{deployment}' in '{namespace}' scaled to {replicas} replicas."
