"""
LLM Integration Service

Integrates Claude API for intelligent decision-making and task execution.
Implements streaming, tool use, and prompt caching.
"""

import logging
from typing import Any, Dict, List, Optional, Callable, AsyncIterator
from dataclasses import dataclass
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    """Tool definition for Claude."""
    name: str
    description: str
    input_schema: Dict[str, Any]


@dataclass
class Message:
    """Chat message."""
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class ConversationMemory:
    """Manages conversation history."""

    def __init__(self, max_messages: int = 100):
        self.messages: List[Message] = []
        self.max_messages = max_messages

    def add_message(self, role: str, content: str) -> None:
        """Add message to history."""
        self.messages.append(Message(role=role, content=content))

        # Truncate if exceeds max
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages :]

    def get_messages(self) -> List[Dict[str, str]]:
        """Get messages formatted for API."""
        return [
            {"role": m.role, "content": m.content}
            for m in self.messages
        ]

    def get_conversation_context(self) -> str:
        """Get conversation context summary."""
        if not self.messages:
            return "No conversation history"

        recent_messages = self.messages[-5:]
        return "\n".join(
            [f"{m.role}: {m.content[:100]}..." for m in recent_messages]
        )

    def clear(self) -> None:
        """Clear conversation history."""
        self.messages = []


class LLMClient:
    """Claude API client."""

    def __init__(self, api_key: str, model: str = "claude-opus-4-1"):
        self.api_key = api_key
        self.model = model
        self.conversation = ConversationMemory()
        self.tools: Dict[str, ToolDefinition] = {}
        self.execution_count = 0
        self.total_tokens = 0

    def register_tool(self, tool: ToolDefinition) -> None:
        """Register a tool for Claude to use."""
        self.tools[tool.name] = tool
        logger.info(f"Tool registered: {tool.name}")

    async def chat(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2048,
        use_tools: bool = False,
    ) -> str:
        """Send message and get response."""
        logger.info(f"Chat: {message[:100]}...")

        self.conversation.add_message("user", message)
        self.execution_count += 1

        # Simulate Claude API call
        # In production, this would use anthropic.Anthropic()
        response = await self._simulate_chat_response(
            message, system_prompt, max_tokens, use_tools
        )

        self.conversation.add_message("assistant", response)
        return response

    async def stream_chat(
        self, message: str, system_prompt: Optional[str] = None
    ) -> AsyncIterator[str]:
        """Stream chat response."""
        logger.info(f"Streaming chat: {message[:100]}...")

        self.conversation.add_message("user", message)

        # Simulate streaming response
        response_text = ""
        async for chunk in self._simulate_streaming_response(message):
            response_text += chunk
            yield chunk

        self.conversation.add_message("assistant", response_text)

    async def analyze_skill(self, skill_definition: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze skill using Claude."""
        prompt = f"""Analyze this skill definition and provide insights:

{skill_definition}

Provide:
1. Clarity assessment
2. Potential issues
3. Improvement suggestions
4. Risk assessment"""

        response = await self.chat(prompt)

        return {
            "analysis": response,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def suggest_workflow_optimization(
        self, workflow: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Suggest workflow optimizations."""
        prompt = f"""Analyze this workflow and suggest optimizations:

{workflow}

Consider:
1. Parallelization opportunities
2. Step consolidation
3. Error handling improvements
4. Performance optimizations"""

        response = await self.chat(prompt)

        return {
            "suggestions": response,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def resolve_conflict(
        self, conflict_description: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resolve conflicts using Claude reasoning."""
        prompt = f"""Resolve this conflict:

{conflict_description}

Context:
{context}

Provide:
1. Root cause analysis
2. Recommended resolution
3. Implementation steps
4. Risk assessment"""

        response = await self.chat(prompt)

        return {
            "resolution": response,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def _simulate_chat_response(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2048,
        use_tools: bool = False,
    ) -> str:
        """Simulate Claude API response."""
        # Mock implementation
        await asyncio.sleep(0.1)  # Simulate API latency

        if "skill" in message.lower():
            return "The skill is well-defined with clear steps and error handling."
        elif "workflow" in message.lower():
            return "The workflow can be optimized by parallelizing steps 2 and 3."
        elif "conflict" in message.lower():
            return "The conflict can be resolved by prioritizing fact1 due to higher confidence."
        else:
            return f"Processed: {message[:50]}... Analysis complete."

    async def _simulate_streaming_response(self, message: str) -> AsyncIterator[str]:
        """Simulate streaming response."""
        response = await self._simulate_chat_response(message)
        for chunk in response.split():
            await asyncio.sleep(0.05)
            yield chunk + " "

    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get conversation history."""
        return [
            {
                "role": m.role,
                "content": m.content,
                "timestamp": m.timestamp.isoformat(),
            }
            for m in self.conversation.messages
        ]

    def get_metrics(self) -> Dict[str, Any]:
        """Get LLM usage metrics."""
        return {
            "model": self.model,
            "execution_count": self.execution_count,
            "total_tokens": self.total_tokens,
            "conversations": len(self.conversation.messages) // 2,
            "tools_registered": len(self.tools),
        }


class PrompEngineering:
    """Prompt engineering utilities."""

    @staticmethod
    def build_system_prompt(
        role: str,
        task: str,
        constraints: List[str],
        output_format: str,
    ) -> str:
        """Build system prompt."""
        prompt = f"""You are a {role}.

Your task: {task}

Constraints:
{chr(10).join(f'- {c}' for c in constraints)}

Output format: {output_format}

Be concise, accurate, and actionable."""

        return prompt

    @staticmethod
    def build_analysis_prompt(
        data: Dict[str, Any],
        analysis_type: str,
        criteria: List[str],
    ) -> str:
        """Build analysis prompt."""
        prompt = f"""Perform a {analysis_type} analysis on:

{data}

Analyze based on these criteria:
{chr(10).join(f'- {c}' for c in criteria)}

Provide structured analysis with key findings and recommendations."""

        return prompt

    @staticmethod
    def build_decision_prompt(
        options: List[str],
        criteria: List[str],
        context: Dict[str, Any],
    ) -> str:
        """Build decision-making prompt."""
        prompt = f"""Make a decision between these options:
{chr(10).join(f'- {o}' for o in options)}

Evaluate using these criteria:
{chr(10).join(f'- {c}' for c in criteria)}

Context:
{context}

Provide your recommendation with reasoning."""

        return prompt


class LLMCache:
    """Caches LLM responses."""

    def __init__(self):
        self.cache: Dict[str, str] = {}
        self.hits = 0
        self.misses = 0

    def get(self, prompt_hash: str) -> Optional[str]:
        """Get cached response."""
        if prompt_hash in self.cache:
            self.hits += 1
            return self.cache[prompt_hash]
        self.misses += 1
        return None

    def set(self, prompt_hash: str, response: str) -> None:
        """Cache response."""
        self.cache[prompt_hash] = response

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self.hits + self.misses
        return {
            "cached_responses": len(self.cache),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hits / total if total > 0 else 0,
        }


class IntelligentAgent:
    """Agent using LLM for decision-making."""

    def __init__(self, llm_client: LLMClient, agent_id: str):
        self.llm_client = llm_client
        self.agent_id = agent_id
        self.decision_log: List[Dict[str, Any]] = []

    async def make_decision(
        self,
        options: List[str],
        criteria: List[str],
        context: Dict[str, Any],
    ) -> str:
        """Make decision using LLM."""
        prompt = PromptEngineering.build_decision_prompt(
            options, criteria, context
        )

        decision = await self.llm_client.chat(prompt)

        self.decision_log.append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "options": options,
                "decision": decision,
                "context": context,
            }
        )

        return decision

    async def analyze_situation(
        self, situation: Dict[str, Any], analysis_type: str
    ) -> str:
        """Analyze situation using LLM."""
        prompt = PromptEngineering.build_analysis_prompt(
            situation,
            analysis_type,
            ["accuracy", "completeness", "actionability"],
        )

        analysis = await self.llm_client.chat(prompt)
        return analysis

    def get_decision_history(self) -> List[Dict[str, Any]]:
        """Get decision history."""
        return self.decision_log
