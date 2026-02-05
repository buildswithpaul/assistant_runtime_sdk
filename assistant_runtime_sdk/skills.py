# Assistant Runtime SDK - Skill Provider
# Copyright (C) 2025 Paul Clinton
# AGPL-3.0 License

"""
Skill Provider - Bridges MCP resources to Strands Agent.

When MCP server has resources enabled, tools have minimal descriptions
with hints like "See fac://tools/create_document for usage guide."

This module provides the get_skill tool that allows LLMs to fetch
the full documentation on-demand, reducing context token usage by ~90%.

Usage:
    from assistant_runtime_sdk import AssistantRuntimeClient
    from assistant_runtime_sdk.skills import SkillProvider

    client = AssistantRuntimeClient(tenant_id, tenant_secret)
    skills = SkillProvider(client, user_id="user@example.com")

    # Add to Strands agent tools
    from strands import Agent
    agent = Agent(
        tools=[*mcp_tools, skills.get_skill_tool()]
    )
"""

from typing import Dict, Optional, TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from .client import AssistantRuntimeClient
    from .async_client import AsyncAssistantRuntimeClient


class SkillProvider:
    """
    Provides the get_skill tool for Strands agents.

    The get_skill tool allows LLMs to fetch detailed documentation for any tool
    before using it. This enables a pattern where tools have minimal descriptions
    (saving context tokens) and the LLM can request full documentation on-demand.

    Attributes:
        _client: Assistant Runtime client instance for API calls
        _user_id: User identifier for API authentication
        _cache: Optional in-memory cache for skill documentation

    Example:
        >>> from assistant_runtime_sdk import AssistantRuntimeClient
        >>> from assistant_runtime_sdk.skills import SkillProvider
        >>>
        >>> client = AssistantRuntimeClient(tenant_id, tenant_secret)
        >>> skills = SkillProvider(client, user_id="user@example.com")
        >>>
        >>> # Get the tool function to add to agent
        >>> skill_tool = skills.get_skill_tool()
        >>>
        >>> # Or use directly
        >>> docs = skills.fetch_skill("create_document")
        >>> print(docs)
    """

    def __init__(
        self,
        client: "AssistantRuntimeClient",
        user_id: str,
        cache_enabled: bool = True,
    ):
        """
        Initialize the SkillProvider.

        Args:
            client: Assistant Runtime client instance (sync or async)
            user_id: User identifier for API authentication
            cache_enabled: Whether to cache skill documentation (default: True)
        """
        self._client = client
        self._user_id = user_id
        self._cache: Optional[Dict[str, str]] = {} if cache_enabled else None

    def get_skill_tool(self) -> Callable[[str], str]:
        """
        Returns the get_skill tool function decorated for Strands.

        The returned function can be passed directly to the Strands Agent's
        tools parameter. It will be available to the LLM as a callable tool.

        Returns:
            A Strands-compatible tool function

        Example:
            >>> skills = SkillProvider(client, user_id)
            >>> agent = Agent(tools=[skills.get_skill_tool()])
        """
        try:
            from strands import tool
        except ImportError:
            raise ImportError(
                "strands-agents is required for get_skill_tool(). "
                "Install it with: pip install strands-agents"
            )

        @tool
        def get_skill(tool_name: str) -> str:
            """Get detailed documentation for a tool before using it.

            Call this when you see a tool with a minimal description that says
            "See fac://tools/... for usage guide" to get the full documentation.

            Args:
                tool_name: The name of the tool (e.g., "create_document", "list_documents")

            Returns:
                Detailed markdown documentation including:
                - Full description of what the tool does
                - All parameters with types and descriptions
                - Usage examples
                - Important notes and warnings
            """
            return self.fetch_skill(tool_name)

        return get_skill

    def fetch_skill(self, tool_name: str) -> str:
        """
        Fetch skill documentation for a tool (sync).

        This is the core method that retrieves documentation from the
        resources API. Results are cached if caching is enabled.

        Args:
            tool_name: Name of the tool to get documentation for

        Returns:
            Markdown documentation string, or error message if not found
        """
        # Check cache first
        if self._cache is not None and tool_name in self._cache:
            return self._cache[tool_name]

        # Build URI - the MCP server uses fac://tools/{tool_name} format
        uri = f"fac://tools/{tool_name}"

        try:
            result = self._client.read_resource(self._user_id, uri)

            if result and result.get("content"):
                content = result["content"]

                # Cache the result
                if self._cache is not None:
                    self._cache[tool_name] = content

                return content

            # Check for error response
            if result and result.get("error"):
                return f"Error fetching documentation for '{tool_name}': {result.get('error')}"

        except Exception as e:
            return f"Could not retrieve documentation for '{tool_name}': {str(e)}"

        return (
            f"No documentation available for tool '{tool_name}'. "
            "The tool may not have detailed docs, or the resources feature may be disabled on the MCP server."
        )

    def clear_cache(self) -> None:
        """Clear the skill documentation cache."""
        if self._cache is not None:
            self._cache.clear()

    def preload_skills(self, tool_names: list[str]) -> None:
        """
        Preload documentation for a list of tools.

        Useful for warming up the cache with commonly used tools
        before starting a conversation.

        Args:
            tool_names: List of tool names to preload
        """
        for name in tool_names:
            self.fetch_skill(name)

    def get_cached_skills(self) -> list[str]:
        """
        Get list of tool names currently in cache.

        Returns:
            List of cached tool names, or empty list if caching disabled
        """
        if self._cache is not None:
            return list(self._cache.keys())
        return []


class AsyncSkillProvider:
    """
    Async version of SkillProvider for use with AsyncAssistantRuntimeClient.

    Provides the same functionality as SkillProvider but with async methods
    for use in async contexts.

    Example:
        >>> async with AsyncAssistantRuntimeClient(tenant_id, tenant_secret) as client:
        ...     skills = AsyncSkillProvider(client, user_id="user@example.com")
        ...     skill_tool = skills.get_skill_tool()
        ...     # Add to async agent
    """

    def __init__(
        self,
        client: "AsyncAssistantRuntimeClient",
        user_id: str,
        cache_enabled: bool = True,
    ):
        """
        Initialize the AsyncSkillProvider.

        Args:
            client: AsyncAssistantRuntimeClient instance
            user_id: User identifier for API authentication
            cache_enabled: Whether to cache skill documentation (default: True)
        """
        self._client = client
        self._user_id = user_id
        self._cache: Optional[Dict[str, str]] = {} if cache_enabled else None

    def get_skill_tool(self) -> Callable[[str], str]:
        """
        Returns the async get_skill tool function decorated for Strands.

        Returns:
            A Strands-compatible async tool function
        """
        try:
            from strands import tool
        except ImportError:
            raise ImportError(
                "strands-agents is required for get_skill_tool(). "
                "Install it with: pip install strands-agents"
            )

        @tool
        async def get_skill(tool_name: str) -> str:
            """Get detailed documentation for a tool before using it.

            Call this when you see a tool with a minimal description that says
            "See fac://tools/... for usage guide" to get the full documentation.

            Args:
                tool_name: The name of the tool (e.g., "create_document", "list_documents")

            Returns:
                Detailed markdown documentation including:
                - Full description of what the tool does
                - All parameters with types and descriptions
                - Usage examples
                - Important notes and warnings
            """
            return await self.fetch_skill(tool_name)

        return get_skill

    async def fetch_skill(self, tool_name: str) -> str:
        """
        Fetch skill documentation for a tool (async).

        Args:
            tool_name: Name of the tool to get documentation for

        Returns:
            Markdown documentation string, or error message if not found
        """
        # Check cache first
        if self._cache is not None and tool_name in self._cache:
            return self._cache[tool_name]

        uri = f"fac://tools/{tool_name}"

        try:
            result = await self._client.read_resource(self._user_id, uri)

            if result and result.get("content"):
                content = result["content"]

                if self._cache is not None:
                    self._cache[tool_name] = content

                return content

            if result and result.get("error"):
                return f"Error fetching documentation for '{tool_name}': {result.get('error')}"

        except Exception as e:
            return f"Could not retrieve documentation for '{tool_name}': {str(e)}"

        return (
            f"No documentation available for tool '{tool_name}'. "
            "The tool may not have detailed docs, or the resources feature may be disabled."
        )

    def clear_cache(self) -> None:
        """Clear the skill documentation cache."""
        if self._cache is not None:
            self._cache.clear()

    async def preload_skills(self, tool_names: list[str]) -> None:
        """
        Preload documentation for a list of tools (async).

        Args:
            tool_names: List of tool names to preload
        """
        for name in tool_names:
            await self.fetch_skill(name)

    def get_cached_skills(self) -> list[str]:
        """
        Get list of tool names currently in cache.

        Returns:
            List of cached tool names, or empty list if caching disabled
        """
        if self._cache is not None:
            return list(self._cache.keys())
        return []
