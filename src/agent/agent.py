import os
import re
import sys
from typing import List, Dict, Any, Optional

# Allow direct execution: python src/agent/agent.py
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger

class ReActAgent:
    """
    ReAct-style agent that follows the Thought-Action-Observation loop.
    Tool definitions are normalized so the agent can execute tools dynamically.
    """
    
    def __init__(self, llm: LLMProvider, tools: List[Dict[str, Any]], max_steps: int = 5):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.history = []
        self.tool_map = self._build_tool_map(tools)

    def _build_tool_map(self, tools: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Normalize tool definitions so agent can read multiple common schemas.
        Supported callable keys: callable, func, function.
        """
        tool_map: Dict[str, Dict[str, Any]] = {}
        for raw_tool in tools:
            if not isinstance(raw_tool, dict):
                continue

            name = str(raw_tool.get("name", "")).strip()
            if not name:
                continue

            description = str(raw_tool.get("description", "")).strip() or "No description provided."
            fn = raw_tool.get("callable") or raw_tool.get("func") or raw_tool.get("function")

            tool_map[name] = {
                "name": name,
                "description": description,
                "callable": fn,
            }
        return tool_map

    def get_system_prompt(self) -> str:
        """
        Build a ReAct system prompt with available tools and output rules.
        """
        if self.tool_map:
            tool_descriptions = "\n".join(
                [f"- {tool['name']}: {tool['description']}" for tool in self.tool_map.values()]
            )
        else:
            tool_descriptions = "- No tools available."
        return f"""
        You are an intelligent assistant. You have access to the following tools:
        {tool_descriptions}

        Use the following format:
        Thought: your line of reasoning.
        Action: tool_name(arguments)
        Observation: result of the tool call.
        ... (repeat Thought/Action/Observation if needed)
        Final Answer: your final response.

        Rules:
        - If a tool is needed, output exactly one Action line.
        - Keep arguments simple and pass only what the tool needs.
        - If no tool is needed, output Final Answer directly.
        """

    def _extract_final_answer(self, llm_text: str) -> Optional[str]:
        match = re.search(r"Final\s*Answer\s*:\s*(.*)", llm_text, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            return None
        return match.group(1).strip()

    def _extract_action(self, llm_text: str) -> Optional[Dict[str, str]]:
        """
        Parse action in form: Action: tool_name(arguments)
        """
        action_match = re.search(r"Action\s*:\s*([a-zA-Z_][\w]*)\((.*)\)", llm_text, flags=re.IGNORECASE | re.DOTALL)
        if not action_match:
            return None

        tool_name = action_match.group(1).strip()
        args = action_match.group(2).strip()
        return {"tool_name": tool_name, "args": args}

    def run(self, user_input: str) -> str:
        """
        Execute the ReAct loop until Final Answer or max_steps is reached.
        """
        logger.log_event("AGENT_START", {"input": user_input, "model": self.llm.model_name})
        
        current_prompt = user_input
        steps = 0
        final_answer = None

        while steps < self.max_steps:
            result = self.llm.generate(current_prompt, system_prompt=self.get_system_prompt())
            content = result.get("content", "")

            self.history.append({"step": steps + 1, "prompt": current_prompt, "llm_output": content})
            logger.log_event("AGENT_STEP", {"step": steps + 1, "output": content})

            parsed_final = self._extract_final_answer(content)
            if parsed_final:
                final_answer = parsed_final
                break

            action = self._extract_action(content)
            if not action:
                final_answer = content.strip() or "I could not produce an answer."
                break

            observation = self._execute_tool(action["tool_name"], action["args"])
            logger.log_event(
                "TOOL_EXECUTION",
                {
                    "step": steps + 1,
                    "tool": action["tool_name"],
                    "args": action["args"],
                    "observation": observation,
                },
            )

            current_prompt = (
                f"{user_input}\n\n"
                f"Previous assistant output:\n{content}\n\n"
                f"Observation: {observation}\n"
                "Continue the ReAct process. If enough information is available, provide Final Answer."
            )
            steps += 1
            
        if final_answer is None:
            final_answer = "I could not finish within max steps."

        logger.log_event("AGENT_END", {"steps": steps, "final_answer": final_answer})
        return final_answer

    def _execute_tool(self, tool_name: str, args: str) -> str:
        """
        Helper method to execute tools by name.
        """
        tool = self.tool_map.get(tool_name)
        if not tool:
            return f"Tool {tool_name} not found."

        fn = tool.get("callable")
        if not callable(fn):
            return f"Tool {tool_name} is not executable."

        try:
            cleaned_arg = args.strip()
            if (cleaned_arg.startswith('"') and cleaned_arg.endswith('"')) or (
                cleaned_arg.startswith("'") and cleaned_arg.endswith("'")
            ):
                cleaned_arg = cleaned_arg[1:-1]

            return str(fn(cleaned_arg))
        except Exception as exc:
            logger.error(f"TOOL_ERROR {tool_name}: {exc}", exc_info=True)
            return f"Tool {tool_name} execution failed: {exc}"
