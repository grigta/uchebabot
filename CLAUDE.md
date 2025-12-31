# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

EduHelper Bot — Telegram educational assistant that helps students solve academic tasks using AI (Gemini 3 Flash via OpenRouter). Features a three-stage task processing flow: interview → plan → solution.

## Development Commands

```bash
# Start all services with Cloudflare tunnel (recommended for development)
./scripts/dev-tunnel.sh

# Start services locally without tunnel
./scripts/dev-local.sh

# Individual services
python3 -m bot.main                    # Telegram bot
python3 -m admin.backend.main          # FastAPI backend (port 8000)
cd webapp && npm run dev               # Mini App dev server
cd admin/frontend && npm run dev       # Admin panel dev server

# Build webapp for production (outputs to webapp/dist/)
./scripts/build-webapp.sh

# Install dependencies
pip install -r requirements.txt
cd webapp && npm install
cd admin/frontend && npm install
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Telegram User                            │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────────────┐
│      bot/ (aiogram)     │     │   webapp/ (Vue 3 Mini App)      │
│  - handlers/question.py │     │  - View solutions               │
│  - FSM state management │     │  - KaTeX math rendering         │
│  - Voice transcription  │     │  - Served at /webapp            │
└─────────────────────────┘     └─────────────────────────────────┘
              │                               │
              ▼                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                admin/backend/ (FastAPI)                         │
│  - routes/solutions.py — Mini App API                           │
│  - routes/auth.py — Telegram OAuth + JWT                        │
│  - routes/webhook.py — YooKassa payments                        │
└─────────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Shared Layer                               │
│  - bot/database/ — SQLAlchemy models, repositories              │
│  - bot/services/openrouter.py — LLM API + voice transcription   │
│  - bot/services/user_service.py — User management               │
└─────────────────────────────────────────────────────────────────┘
```

## Key Flows

**Task Processing (bot/handlers/question.py)**:
1. User sends text/photo/voice → `F.photo | F.voice | F.text` filter
2. Interview stage: AI asks clarifying questions (skippable)
3. Plan stage: AI generates 3-5 step solution plan (confirm/edit/cancel)
4. Solution stage: AI solves task, long messages split automatically

**Voice Messages**:
- Uses faster-whisper for local transcription (CPU, "small" model)
- Transcribed text passed to Gemini 3 Flash for solving
- `bot/services/openrouter.py:transcribe_voice()` handles transcription

**Payments**:
- Telegram Stars via `bot/services/telegram_stars.py`
- YooKassa via `bot/services/yookassa_service.py`
- Packages: 50/100/500 requests or monthly subscription

## Database

SQLite for development (`./data/bot.db`), PostgreSQL for production.

**Models** (`bot/database/models.py`):
- `User` — telegram_id, daily/total requests, bonus_requests, is_banned
- `Request` — question, answer, tokens, had_image, had_voice
- `Payment` — provider, package_type, status
- `Subscription` — is_active, expires_at

**Repository Pattern**: `bot/database/repositories.py` — UserRepository, RequestRepository

## Configuration

All settings via `.env` file, loaded by Pydantic Settings in `bot/config.py`.

Key variables:
- `TELEGRAM_BOT_TOKEN`, `ADMIN_IDS` — Telegram config
- `OPENROUTER_API_KEY`, `OPENROUTER_MODEL` — AI model (google/gemini-3-flash-preview)
- `DATABASE_URL` — sqlite+aiosqlite:///./data/bot.db
- `WEBAPP_URL` — Public URL for Mini App (set by dev-tunnel.sh)

## Frontend Notes

**Webapp (Mini App)**:
- Vue 3 + TypeScript + Vite
- KaTeX for math rendering (`webapp/src/components/MarkdownRenderer.vue`)
- Telegram WebApp SDK integration
- Built files served by FastAPI at `/webapp`

**Admin Panel**:
- Vue 3 + Vuetify 3 + TypeScript
- Telegram OAuth for admin authentication
- User management, statistics, solution history

## FSM States

Defined in `bot/handlers/states.py`:
```python
class TaskFlow(StatesGroup):
    awaiting_question = State()
    interview = State()
    awaiting_plan_confirm = State()
    processing = State()
```

## Important Patterns

- **Async everywhere**: All DB operations, HTTP requests, file I/O are async
- **Middleware injection**: Database session injected via `bot/middlewares/database.py`
- **Long message splitting**: `bot/utils/text_utils.py:split_long_message()` handles Telegram's 4096 char limit
- **Content moderation**: `bot/services/moderation.py` filters jailbreak attempts
- **Retry logic**: `openrouter.py:_request_with_retry()` handles rate limits and transient errors
