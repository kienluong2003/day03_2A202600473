import os
import sys
from typing import Optional

from dotenv import load_dotenv

# Allow running this file directly from project root.
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.llm_provider import LLMProvider
from src.core.openai_provider import OpenAIProvider
from src.core.gemini_provider import GeminiProvider
from src.core.local_provider import LocalProvider
from src.agent.agent import ReActAgent
from src.tools.get_hotel_reviews import get_hotel_reviews
from src.telemetry.metrics import tracker
from src.telemetry.logger import logger


SYSTEM_PROMPT = (
    "You are a helpful AI assistant. "
    "Answer clearly and concisely. "
    "If the request needs external tools or live data, explain your limitation honestly."
)


def _get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def create_provider() -> LLMProvider:
    provider = os.getenv("DEFAULT_PROVIDER", "openai").strip().lower()

    if provider == "openai":
        api_key = _get_required_env("OPENAI_API_KEY")
        model = os.getenv("OPENAI_MODEL", "gpt-4o")
        return OpenAIProvider(model_name=model, api_key=api_key)

    if provider == "gemini":
        api_key = _get_required_env("GEMINI_API_KEY")
        model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        return GeminiProvider(model_name=model, api_key=api_key)

    if provider == "local":
        model_path = os.getenv("LOCAL_MODEL_PATH", "./models/Phi-3-mini-4k-instruct-q4.gguf")
        return LocalProvider(model_path=model_path)

    raise ValueError(
        "Unsupported DEFAULT_PROVIDER. Use one of: openai, gemini, local"
    )


def ask_chatbot(llm: LLMProvider, user_text: str, system_prompt: Optional[str] = None) -> str:
    result = llm.generate(user_text, system_prompt=system_prompt)

    tracker.track_request(
        provider=result.get("provider", "unknown"),
        model=llm.model_name,
        usage=result.get("usage", {}),
        latency_ms=result.get("latency_ms", 0),
    )

    return result.get("content", "").strip()


def create_agent(llm: LLMProvider) -> ReActAgent:
    tools = [
        {
            "name": "get_hotel_reviews",
            "description": "Extract average rating and summary feedback from previous hotel guests by hotel id.",
            "callable": get_hotel_reviews,
        }
    ]
    max_steps = int(os.getenv("AGENT_MAX_STEPS", "5"))
    return ReActAgent(llm=llm, tools=tools, max_steps=max_steps)


def main() -> None:
    load_dotenv()

    try:
        llm = create_provider()
        agent = create_agent(llm)
    except Exception as exc:
        print(f"Initialization error: {exc}")
        return

    chat_mode = os.getenv("CHAT_MODE", "agent").strip().lower()
    if chat_mode not in {"agent", "chat"}:
        chat_mode = "agent"

    print("=== Chatbot + ReAct Agent ===")
    print("Type your question and press Enter.")
    print("Type '/mode agent' or '/mode chat' to switch mode.")
    print(f"Current mode: {chat_mode}")
    print("Type 'exit' or 'quit' to stop.\n")

    logger.log_event("CHATBOT_START", {"provider_model": llm.model_name, "mode": chat_mode})

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not user_input:
            continue

        if user_input.lower() in {"exit", "quit"}:
            print("Goodbye.")
            break

        if user_input.lower().startswith("/mode "):
            requested_mode = user_input[6:].strip().lower()
            if requested_mode in {"agent", "chat"}:
                chat_mode = requested_mode
                print(f"Switched mode to: {chat_mode}\n")
            else:
                print("Invalid mode. Use '/mode agent' or '/mode chat'.\n")
            continue

        try:
            if chat_mode == "agent":
                answer = agent.run(user_input)
            else:
                answer = ask_chatbot(llm, user_input, system_prompt=SYSTEM_PROMPT)
            print(f"Bot: {answer}\n")
        except Exception as exc:
            logger.error("CHATBOT_ERROR", exc_info=True)
            print(f"Bot error: {exc}\n")

    logger.log_event("CHATBOT_END", {"status": "terminated"})


if __name__ == "__main__":
    main()
