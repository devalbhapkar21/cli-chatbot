
#Imports
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import openai
from dotenv import load_dotenv
from openai import OpenAI

CONFIG_PATH = Path(__file__).parent / "config.json"



# Configuration

@dataclass
class Config:
    system_prompt: str
    model: str = "gpt-5.4-nano"
    max_completion_tokens: int = 2000
    timeout_seconds: float = 30
    max_retries: int = 3
    retry_base_delay_seconds: float = 2


def load_config(path: Path = CONFIG_PATH) -> Config:
    """Load settings from config.json. Exits with a clear message on problems."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        sys.exit(f"Config file not found: {path}")
    except json.JSONDecodeError as e:
        sys.exit(f"Invalid JSON in {path}: {e}")

    if not data.get("system_prompt"):
        sys.exit("config.json must contain a non-empty 'system_prompt'.")

    try:
        return Config(**data)
    except TypeError as e:
        sys.exit(f"Bad config.json: {e}")



# API layer (retries and error handling)

class ChatError(Exception):
    """Raised when a request ultimately fails. Message is user-friendly."""


def _describe(error: Exception) -> str:
    if isinstance(error, openai.APITimeoutError):
        return "Request timed out."
    if isinstance(error, openai.RateLimitError):
        return "Rate limit reached."
    if isinstance(error, openai.APIConnectionError):
        return "Could not connect to the API."
    return "Server error."


def _retry_delay(attempt: int, base: float, error=None) -> float:
    """Exponential backoff, honoring the server's Retry-After header if present."""
    response = getattr(error, "response", None)
    if response is not None:
        retry_after = response.headers.get("retry-after")
        if retry_after:
            try:
                return float(retry_after)
            except ValueError:
                pass
    return base * (2 ** attempt)


def _build_messages(config: Config, history: list) -> list:
    """Prepend the configured system prompt; history itself never stores it."""
    return [{"role": "system", "content": config.system_prompt}, *history]


def _extract_text(response) -> str:
    """Pull reply text out of the response, failing clearly if it is empty."""
    choice = response.choices[0]
    text = choice.message.content or ""
    if not text.strip():
        if choice.finish_reason == "length":
            raise ChatError(
                "The model used its whole token budget before replying. "
                "Increase 'max_completion_tokens' in config.json."
            )
        raise ChatError("The model returned an empty reply.")
    return text


def get_reply(client: OpenAI, config: Config, history: list) -> str:
    """Send the conversation to the API and return the reply text.

    Retries on timeouts, connection errors, rate limits, and 5xx errors.
    Fails immediately on invalid API keys, exhausted quota, and other client errors.
    """
    for attempt in range(config.max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=config.model,
                max_completion_tokens=config.max_completion_tokens,
                messages=_build_messages(config, history),
            )
            return _extract_text(response)

        except openai.AuthenticationError:
            raise ChatError(
                "Invalid API key. Check OPENAI_API_KEY in your .env file."
            )
        except openai.PermissionDeniedError:
            raise ChatError("Your API key does not have permission for this request.")
        except openai.BadRequestError as e:
            raise ChatError(f"The request was rejected: {e.message}")

        except (
            openai.APITimeoutError,
            openai.APIConnectionError,
            openai.RateLimitError,
            openai.InternalServerError,
        ) as e:
            # A 429 with this code means billing/quota, not a temporary limit.
            if getattr(e, "code", None) == "insufficient_quota":
                raise ChatError(
                    "Your OpenAI quota is exhausted. Check your plan and billing."
                )
            if attempt == config.max_retries:
                raise ChatError(
                    f"{_describe(e)} Gave up after {config.max_retries} retries."
                )
            delay = _retry_delay(attempt, config.retry_base_delay_seconds, e)
            print(
                f"[{_describe(e)} Retrying in {delay:.0f}s "
                f"({attempt + 1}/{config.max_retries})...]"
            )
            time.sleep(delay)

        except openai.APIStatusError as e:
            raise ChatError(f"API error ({e.status_code}): {e.message}")

    raise ChatError("Request failed.")  # unreachable, keeps type checkers happy



# Conversation handling

HELP_TEXT = """Commands:
  /reset  Clear the conversation history
  /help   Show this message
  /quit   Exit (Ctrl+C also works)"""


def handle_command(command: str, history: list) -> bool:
    """Handle a slash command. Returns True if the chat should exit."""
    if command in {"/quit", "/exit"}:
        return True
    if command == "/reset":
        history.clear()
        print("Conversation history cleared.\n")
    elif command == "/help":
        print(HELP_TEXT + "\n")
    else:
        print(f"Unknown command '{command}'. Type /help for options.\n")
    return False


def chat_turn(client: OpenAI, config: Config, history: list, user_input: str) -> None:
    """Run one turn. History only changes if the whole turn succeeds."""
    history.append({"role": "user", "content": user_input})
    try:
        reply = get_reply(client, config, history)
    except ChatError as e:
        history.pop()  # drop the unanswered message so roles stay alternating
        print(f"Error: {e}\n")
        return
    history.append({"role": "assistant", "content": reply})
    print(f"Bot: {reply}\n")



# Entry point

def main() -> None:
    load_dotenv()
    config = load_config()
    # max_retries=0 disables the SDK's built-in retries; we handle them ourselves.
    client = OpenAI(timeout=config.timeout_seconds, max_retries=0)
    history: list = []

    print(f"Chatbot ready (model: {config.model}). Type /help for commands.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.startswith("/"):
            if handle_command(user_input.lower(), history):
                print("Goodbye!")
                break
            continue

        chat_turn(client, config, history, user_input)


if __name__ == "__main__":
    main()
