import re
from typing import List, Dict, Any
import json
import logging
from typing import List, Dict, Any, Optional
from src.core.llm_provider import LLMProvider

# Simple logger fallback nếu chưa có telemetry module
try:
    from src.telemetry.logger import logger
except ImportError:
    class _SimpleLogger:
        def log_event(self, event, data=None):
            logging.info(f"[{event}] {data}")
    logger = _SimpleLogger()



class ReActAgent:
    def __init__(self, llm: LLMProvider, tools: List[Dict[str, Any]], max_steps: int = 5):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.history = []

        # Registry: map tool name -> callable
        self._tool_registry: Dict[str, Any] = {t["name"]: t["fn"] for t in tools if "fn" in t}

    def get_system_prompt(self) -> str:
        tool_descriptions = "\n".join(
            [f"- {t['name']}: {t['description']}\n  Example: {t['name']}({t.get('args_example','')})"
             for t in self.tools]
        )
        return f"""You are a helpful hotel booking assistant. You have access to the following tools:

{tool_descriptions}

Use EXACTLY this format:
Thought: your line of reasoning.
Action: tool_name("arg1", "arg2")
Observation: result of the tool call.
... (repeat Thought/Action/Observation as needed)
Final Answer: your final response to the user.

Rules:
- Always produce a Thought before an Action.
- Only call tools that are listed above.
- When you have enough information, write Final Answer.
"""

    def run(self, user_input: str) -> str:
        logger.log_event("AGENT_START", {"input": user_input, "model": self.llm.model_name})

        # Seed the conversation with the user message
        self.history.append({"role": "user", "content": user_input})
        steps = 0
        full_trace = []

        while steps < self.max_steps:
            # 1. Ask the LLM for the next Thought/Action (or Final Answer)
            result = self.llm.generate(
                self.history,
                system_prompt=self.get_system_prompt(),
            )

            # Append raw assistant output to history
            self.history.append({"role": "assistant", "content": result})
            logger.log_event("LLM_OUTPUT", {"step": steps, "output": result})

            # 2. Check for Final Answer first
            final = re.search(r"Final Answer:\s*(.+)", result, re.DOTALL)
            if final:
                answer = final.group(1).strip()
                logger.log_event("AGENT_END", {"steps": steps, "answer": answer})
                return answer

            # 3. Parse Action: tool_name("arg1", "arg2")
            action_match = re.search(r"Action:\s*(\w+)\((.*?)\)", result, re.DOTALL)
            if action_match:
                tool_name = action_match.group(1).strip()
                raw_args  = action_match.group(2).strip()

                # Execute the tool
                observation = self._execute_tool(tool_name, raw_args)
                logger.log_event("TOOL_CALL", {"tool": tool_name, "args": raw_args, "result": observation})

                # Feed the observation back as a user message so the LLM continues
                self.history.append({
                    "role": "user",
                    "content": f"Observation: {observation}",
                })

            steps += 1

        logger.log_event("AGENT_END", {"steps": steps, "answer": "max steps reached"})
        return "I reached the maximum number of reasoning steps without a final answer."

    def _execute_tool(self, tool_name: str, raw_args: str) -> str:
        if tool_name not in self._tool_registry:
            return f"Tool '{tool_name}' not found."

        # Parse comma-separated string args, stripping quotes
        args = [a.strip().strip('"').strip("'") for a in raw_args.split(",") if a.strip()]

        try:
            result = self._tool_registry[tool_name](*args)
            return str(result)
        except Exception as e:
            return f"Error running {tool_name}: {e}"
