# CLI Chatbot

A command-line chatbot built on the OpenAI API (default model: `gpt-5.4-nano`) using the chat completions API from Open AI

## Features

- **Full conversation history** is kept and sent on every turn, so the bot remembers earlier messages.
- **Configurable system prompt** loaded from `config.json` (nothing hardcoded).
- **Graceful error handling** with automatic retries and exponential backoff for timeouts, connection errors, rate limits, and server errors. Invalid API keys fail immediately with a clear message.
- **`/reset` command** to clear the conversation.

## Requirements

- Python 3.9+
- An OpenAI API key (https://platform.openai.com/api-keys)

## Setup

```bash
# 1. Clone the repo
git clone https://github.com/YOUR-USERNAME/cli-chatbot.git
cd cli-chatbot

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate          # macOS / Linux
.venv\Scripts\Activate.ps1         # Windows PowerShell

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your API key
cp .env.example .env               # Windows: copy .env.example .env
# then edit .env and set OPENAI_API_KEY=your-key-here
```

## Usage

```bash
python chatbot.py
```

| Command  | Action                            |
|----------|-----------------------------------|
| `/reset` | Clear the conversation history    |
| `/help`  | Show available commands           |
| `/quit`  | Exit (Ctrl+C / Ctrl+D also work)  |

Example:

```
You: My name is Sam.
Bot: Nice to meet you, Sam!

You: What's my name?
Bot: Your name is Sam.

You: /reset
Conversation history cleared.

You: What's my name?
Bot: I don't know your name yet. Could you tell me?
```

## Configuration

Edit `config.json`:

| Key                        | Description                                            | Default        |
|----------------------------|--------------------------------------------------------|----------------|
| `system_prompt`            | Instructions that set the bot's behavior (required)    | -              |
| `model`                    | Model name                                             | `gpt-5.4-nano` |
| `max_completion_tokens`    | Token cap per reply (includes hidden reasoning tokens) | `2000`         |
| `timeout_seconds`          | Per-request timeout                                    | `30`           |
| `max_retries`              | Retries after a retryable failure                      | `3`            |
| `retry_base_delay_seconds` | Base delay for exponential backoff (2s, 4s, 8s...)     | `2`            |

Changes take effect the next time you start the bot.

> `gpt-5.4-nano` is a reasoning model, so part of `max_completion_tokens` can be spent on hidden reasoning. If you see an error about the token budget, raise this value.

## Error handling

| Error                      | Behavior                                                      |
|----------------------------|---------------------------------------------------------------|
| Timeout / connection error | Retried with backoff, then a friendly error                   |
| Rate limit (429)           | Retried, honoring the `Retry-After` header if sent            |
| Server error (5xx)         | Retried with backoff                                          |
| Invalid API key (401)      | Fails immediately with instructions to check `.env`           |
| Quota exhausted (429)      | Fails immediately and points to billing (retrying won't help) |
| Bad request (400)          | Fails immediately and shows the reason                        |

If a turn fails, your message is removed from history so the conversation stays valid and you can simply try again.

## Project structure

```
cli-chatbot/
├── chatbot.py        # Application code
├── config.json       # System prompt and settings
├── requirements.txt  # Dependencies
├── .env.example      # Template for your API key
├── .gitignore
└── README.md
```

## Code overview

- `load_config()` reads and validates `config.json`.
- `get_reply()` calls the API and owns all retry logic.
- `chat_turn()` updates history only when a turn succeeds.
- `handle_command()` processes `/reset`, `/help`, `/quit`.
- `main()` is just setup plus the input loop.
