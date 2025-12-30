# EduHelper Bot — Технические решения и лучшие практики

> Документ сформирован на основе актуальной документации библиотек (Context7, декабрь 2024)

---

## 1. aiogram 3.x — Telegram Bot Framework

### 1.1 Архитектура и структура

**Рекомендуемый подход:**
- Использовать **Router** для модульной организации хендлеров
- Dispatcher как корневой роутер с настройками FSM
- Разделение логики по файлам: `handlers/`, `keyboards/`, `middlewares/`

```python
from aiogram import Bot, Dispatcher, Router
from aiogram.fsm.storage.redis import RedisStorage

# Создание роутера для модуля
router = Router(name="questions")

# Инициализация диспетчера с Redis storage
dp = Dispatcher(
    storage=RedisStorage.from_url("redis://localhost:6379/0"),
    fsm_strategy=FSMStrategy.USER_IN_CHAT
)

# Подключение роутеров
dp.include_router(start_router)
dp.include_router(questions_router)
dp.include_router(profile_router)
```

### 1.2 FSM (Finite State Machine) — Управление состояниями

**Лучшие практики:**

```python
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

class TaskFlow(StatesGroup):
    """Состояния для флоу обработки задачи"""
    awaiting_question = State()      # Ожидание вопроса
    interview = State()              # Интервью/уточнение
    awaiting_plan_confirm = State()  # Подтверждение плана
    processing = State()             # Обработка AI

# Использование в хендлере
@router.message(TaskFlow.interview)
async def process_interview(message: Message, state: FSMContext):
    # Получение данных из state
    data = await state.get_data()

    # Обновление данных
    await state.update_data(interview_answer=message.text)

    # Переход к следующему состоянию
    await state.set_state(TaskFlow.awaiting_plan_confirm)
```

### 1.3 Middleware — Промежуточные обработчики

```python
from aiogram import BaseMiddleware
from typing import Callable, Any, Awaitable

class RateLimitMiddleware(BaseMiddleware):
    """Middleware для ограничения запросов"""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id = data.get("event_from_user").id

        # Проверка лимита
        if await self.is_rate_limited(user_id):
            await event.answer("Слишком много запросов. Подождите.")
            return

        # Продолжение обработки
        return await handler(event, data)

# Регистрация middleware
router.message.middleware(RateLimitMiddleware())
```

### 1.4 Dependency Injection

```python
from aiogram import types, Bot
from aiogram.fsm.context import FSMContext

# Зависимости автоматически инжектируются в хендлер
async def handle_question(
    message: types.Message,
    bot: Bot,                    # Экземпляр бота
    state: FSMContext,           # FSM контекст
    user_service: UserService,   # Кастомный сервис (через workflow_data)
) -> None:
    user = await user_service.get_or_create(message.from_user.id)
    # ...
```

---

## 2. FastAPI — Admin Panel Backend

### 2.1 Структура проекта

```
admin/backend/
├── main.py              # Точка входа
├── config.py            # Настройки
├── dependencies.py      # Зависимости (DI)
├── routes/
│   ├── __init__.py
│   ├── auth.py          # Telegram OAuth + JWT
│   ├── users.py         # CRUD пользователей
│   └── stats.py         # Статистика
├── schemas/
│   ├── user.py          # Pydantic схемы
│   └── stats.py
└── services/
    └── auth_service.py
```

### 2.2 JWT Authentication с Telegram OAuth

```python
from fastapi import Depends, HTTPException, status, Security
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from jose import jwt, JWTError
from pydantic import ValidationError

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="token",
    scopes={"admin": "Full admin access", "read": "Read-only access"}
)

SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"

async def get_current_admin(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme)
):
    """Проверка JWT токена и прав доступа"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        telegram_id: int = payload.get("sub")
        if telegram_id is None:
            raise credentials_exception

        token_scopes = payload.get("scopes", [])

    except (JWTError, ValidationError):
        raise credentials_exception

    # Проверка что telegram_id в списке админов
    if telegram_id not in ADMIN_IDS:
        raise credentials_exception

    # Проверка scopes
    for scope in security_scopes.scopes:
        if scope not in token_scopes:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not enough permissions",
            )

    return telegram_id

# Использование в роуте
@router.get("/users", dependencies=[Security(get_current_admin, scopes=["admin"])])
async def list_users():
    ...
```

### 2.3 Dependency Injection

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Генератор сессии БД"""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

async def get_user_service(
    db: AsyncSession = Depends(get_db)
) -> UserService:
    return UserService(db)

# В роуте
@router.get("/users/{user_id}")
async def get_user(
    user_id: int,
    service: UserService = Depends(get_user_service)
):
    return await service.get_by_id(user_id)
```

### 2.4 Error Handling

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    # Логирование в Loki
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )
```

---

## 3. SQLAlchemy 2.x — Async ORM

### 3.1 Модели с AsyncAttrs

```python
from sqlalchemy.ext.asyncio import AsyncAttrs, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, func
from datetime import datetime

class Base(AsyncAttrs, DeclarativeBase):
    """Базовый класс с поддержкой async атрибутов"""
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(unique=True, index=True)
    username: Mapped[str | None] = mapped_column(nullable=True)
    first_name: Mapped[str | None]
    last_name: Mapped[str | None]

    daily_requests: Mapped[int] = mapped_column(default=0)
    total_requests: Mapped[int] = mapped_column(default=0)
    total_tokens: Mapped[int] = mapped_column(default=0)

    is_banned: Mapped[bool] = mapped_column(default=False)
    custom_daily_limit: Mapped[int | None] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now()
    )

    # Relationships
    requests: Mapped[list["Request"]] = relationship(back_populates="user")

class Request(Base):
    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    question: Mapped[str]
    answer: Mapped[str]
    detected_subject: Mapped[str | None]
    model_used: Mapped[str]
    prompt_tokens: Mapped[int]
    completion_tokens: Mapped[int]
    total_tokens: Mapped[int]
    response_time_ms: Mapped[int]
    had_image: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship(back_populates="requests")
```

### 3.2 Async Engine и Session

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Создание async engine
engine = create_async_engine(
    "postgresql+asyncpg://user:password@localhost:5432/eduhelper",
    echo=False,  # True для отладки SQL
    pool_size=20,
    max_overflow=10,
)

# Фабрика сессий
# expire_on_commit=False — критично для async!
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_db():
    """Инициализация БД"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

### 3.3 Repository Pattern

```python
from sqlalchemy import select
from sqlalchemy.orm import selectinload

class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_with_requests(self, user_id: int) -> User | None:
        """Загрузка пользователя с его запросами (eager loading)"""
        result = await self.session.execute(
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.requests))
        )
        return result.scalar_one_or_none()

    async def create(self, telegram_id: int, **kwargs) -> User:
        user = User(telegram_id=telegram_id, **kwargs)
        self.session.add(user)
        await self.session.flush()
        return user

    async def increment_requests(self, user_id: int, tokens: int) -> None:
        user = await self.session.get(User, user_id)
        user.daily_requests += 1
        user.total_requests += 1
        user.total_tokens += tokens
```

### 3.4 Работа с Lazy-Loaded атрибутами (AsyncAttrs)

```python
# Проблема: в async нельзя использовать lazy loading напрямую
# Решение 1: Eager loading через selectinload
stmt = select(User).options(selectinload(User.requests))

# Решение 2: AsyncAttrs и awaitable_attrs
user = await session.get(User, user_id)
# Вместо user.requests (вызовет ошибку)
requests = await user.awaitable_attrs.requests
```

---

## 4. Pydantic 2.x — Валидация и Settings

### 4.1 BaseSettings для конфигурации

```python
from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Конфигурация приложения из .env"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # Игнорировать лишние переменные
    )

    # Telegram
    telegram_bot_token: str = Field(alias="TELEGRAM_BOT_TOKEN")
    admin_ids: list[int] = Field(default_factory=list)

    # OpenRouter
    openrouter_api_key: str
    openrouter_model: str = "google/gemini-3-flash-preview"
    openrouter_max_tokens: int = 2000
    openrouter_temperature: float = 0.7
    openrouter_timeout: int = 60

    # Database
    database_url: PostgresDsn = Field(
        default="postgresql+asyncpg://user:password@localhost:5432/eduhelper"
    )

    # Redis
    redis_url: RedisDsn = Field(default="redis://localhost:6379/0")

    # Limits
    daily_request_limit: int = 20

    # Logging
    loki_url: str = "http://localhost:3100/loki/api/v1/push"
    log_level: str = "INFO"

    # Admin
    admin_jwt_secret: str

    # Debug
    debug: bool = False

# Синглтон
settings = Settings()
```

### 4.2 Модели для API

```python
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

class UserBase(BaseModel):
    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None

class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    daily_requests: int
    total_requests: int
    total_tokens: int
    is_banned: bool
    custom_daily_limit: int | None
    created_at: datetime

class UserUpdate(BaseModel):
    is_banned: bool | None = None
    custom_daily_limit: int | None = None

class StatsResponse(BaseModel):
    dau: int
    mau: int
    total_users: int
    requests_today: int
    requests_week: int
    popular_subjects: list[dict[str, int]]
```

### 4.3 Валидация с кастомными правилами

```python
from pydantic import BaseModel, field_validator, model_validator

class QuestionRequest(BaseModel):
    text: str
    image_base64: str | None = None

    @field_validator("text")
    @classmethod
    def validate_text_length(cls, v: str) -> str:
        if len(v) > 4000:
            raise ValueError("Вопрос слишком длинный (макс. 4000 символов)")
        if len(v.strip()) == 0:
            raise ValueError("Вопрос не может быть пустым")
        return v.strip()

    @model_validator(mode="after")
    def check_content(self):
        if not self.text and not self.image_base64:
            raise ValueError("Необходим текст или изображение")
        return self
```

---

## 5. Redis — State Storage и Caching

### 5.1 Async Redis Client

```python
import redis.asyncio as aioredis
from redis.asyncio import ConnectionPool

# Создание пула соединений
pool = ConnectionPool.from_url(
    "redis://localhost:6379/0",
    max_connections=20,
    decode_responses=True
)

# Создание клиента
redis_client = aioredis.Redis(connection_pool=pool)

# Альтернатива: from_url
redis_client = await aioredis.from_url(
    "redis://localhost:6379/0",
    encoding="utf-8",
    decode_responses=True
)
```

### 5.2 Операции с Redis

```python
import json
from typing import Any

class RedisService:
    def __init__(self, redis: aioredis.Redis):
        self.redis = redis

    async def set_user_state(self, user_id: int, state: str, ttl: int = 600):
        """Установка состояния пользователя с TTL"""
        key = f"user:{user_id}:state"
        await self.redis.set(key, state, ex=ttl)

    async def get_user_state(self, user_id: int) -> str | None:
        key = f"user:{user_id}:state"
        return await self.redis.get(key)

    async def set_interview_data(self, user_id: int, data: dict, ttl: int = 600):
        """Сохранение данных интервью"""
        key = f"user:{user_id}:interview_data"
        await self.redis.set(key, json.dumps(data), ex=ttl)

    async def get_interview_data(self, user_id: int) -> dict | None:
        key = f"user:{user_id}:interview_data"
        data = await self.redis.get(key)
        return json.loads(data) if data else None

    async def add_to_queue(self, user_id: int, message: dict):
        """Добавление сообщения в очередь"""
        key = f"user:{user_id}:message_queue"
        await self.redis.rpush(key, json.dumps(message))
        # Ограничение очереди до 10 сообщений
        await self.redis.ltrim(key, -10, -1)

    async def pop_from_queue(self, user_id: int) -> dict | None:
        """Извлечение сообщения из очереди"""
        key = f"user:{user_id}:message_queue"
        data = await self.redis.lpop(key)
        return json.loads(data) if data else None
```

### 5.3 Redis для aiogram FSM Storage

```python
from aiogram.fsm.storage.redis import RedisStorage

# Использование RedisStorage из aiogram
storage = RedisStorage.from_url(
    "redis://localhost:6379/0",
    state_ttl=600,    # TTL для состояний
    data_ttl=600,     # TTL для данных
)

dp = Dispatcher(storage=storage)
```

### 5.4 Graceful Shutdown

```python
async def on_shutdown():
    """Корректное закрытие соединений"""
    await redis_client.close()
    await pool.disconnect()
```

---

## 6. aiohttp — HTTP Client для OpenRouter

### 6.1 Настройка ClientSession

```python
import aiohttp
from aiohttp import ClientTimeout

class OpenRouterClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://openrouter.ai/api/v1"
        self.timeout = ClientTimeout(total=60)
        self._session: aiohttp.ClientSession | None = None

    async def get_session(self) -> aiohttp.ClientSession:
        """Ленивая инициализация сессии"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=self.timeout,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
            )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
```

### 6.2 Retry Logic

```python
import asyncio
from typing import Any

class OpenRouterClient:
    # ... (предыдущий код)

    async def _request_with_retry(
        self,
        method: str,
        endpoint: str,
        json_data: dict | None = None,
        attempts: int = 3
    ) -> dict[str, Any]:
        """Запрос с автоматическим retry"""
        session = await self.get_session()
        url = f"{self.base_url}{endpoint}"

        for attempt in range(attempts):
            try:
                async with session.request(method, url, json=json_data) as resp:
                    if resp.status == 429:  # Rate limit
                        retry_after = int(resp.headers.get("Retry-After", 5))
                        await asyncio.sleep(retry_after)
                        continue

                    resp.raise_for_status()
                    return await resp.json()

            except aiohttp.ClientConnectionError:
                if attempt + 1 == attempts:
                    raise
                await asyncio.sleep(0.5 * (attempt + 1))

            except asyncio.TimeoutError:
                if attempt + 1 == attempts:
                    raise
                await asyncio.sleep(1)

        raise Exception("Max retry attempts exceeded")
```

### 6.3 Запрос к OpenRouter с поддержкой изображений

```python
import base64

class OpenRouterClient:
    # ... (предыдущий код)

    async def chat_completion(
        self,
        messages: list[dict],
        image_base64: str | None = None,
        model: str = "google/gemini-3-flash-preview",
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> dict:
        """Отправка запроса к Chat Completion API"""

        # Формирование content с изображением
        if image_base64:
            content = [
                {"type": "text", "text": messages[-1]["content"]},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}"
                    }
                }
            ]
            messages[-1]["content"] = content

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        return await self._request_with_retry(
            "POST",
            "/chat/completions",
            json_data=payload
        )
```

---

## 7. Vue 3 + Vuetify 3 — Admin Panel Frontend

### 7.1 Структура проекта

```
admin/frontend/
├── src/
│   ├── main.ts
│   ├── App.vue
│   ├── plugins/
│   │   └── vuetify.ts
│   ├── router/
│   │   └── index.ts
│   ├── stores/
│   │   ├── auth.ts
│   │   └── users.ts
│   ├── views/
│   │   ├── LoginView.vue
│   │   ├── DashboardView.vue
│   │   └── UsersView.vue
│   ├── components/
│   │   ├── AppLayout.vue
│   │   ├── StatsCard.vue
│   │   └── UsersTable.vue
│   └── api/
│       └── client.ts
├── package.json
└── vite.config.ts
```

### 7.2 Конфигурация Vuetify 3

```typescript
// src/plugins/vuetify.ts
import { createVuetify } from 'vuetify'
import { md3 } from 'vuetify/blueprints'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

export default createVuetify({
  blueprint: md3,
  components,
  directives,
  theme: {
    defaultTheme: 'light',
    themes: {
      light: {
        colors: {
          primary: '#1976D2',
          secondary: '#424242',
          accent: '#82B1FF',
          error: '#FF5252',
          info: '#2196F3',
          success: '#4CAF50',
          warning: '#FFC107',
        },
      },
      dark: {
        colors: {
          primary: '#2196F3',
          secondary: '#424242',
        },
      },
    },
  },
  defaults: {
    VBtn: {
      rounded: 'lg',
      variant: 'elevated',
    },
    VCard: {
      rounded: 'lg',
      elevation: 2,
    },
    VTextField: {
      variant: 'outlined',
      density: 'comfortable',
    },
    VDataTable: {
      density: 'comfortable',
    },
  },
})
```

### 7.3 Layout компонент

```vue
<!-- src/components/AppLayout.vue -->
<template>
  <v-app>
    <v-app-bar color="primary" height="56">
      <v-app-bar-nav-icon @click="drawer = !drawer" />
      <v-app-bar-title>EduHelper Admin</v-app-bar-title>
      <v-spacer />
      <v-btn icon="mdi-logout" @click="logout" />
    </v-app-bar>

    <v-navigation-drawer v-model="drawer">
      <v-list>
        <v-list-item
          v-for="item in menuItems"
          :key="item.path"
          :to="item.path"
          :prepend-icon="item.icon"
          :title="item.title"
        />
      </v-list>
    </v-navigation-drawer>

    <v-main>
      <v-container fluid>
        <slot />
      </v-container>
    </v-main>
  </v-app>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'

const drawer = ref(true)
const authStore = useAuthStore()

const menuItems = [
  { path: '/dashboard', icon: 'mdi-view-dashboard', title: 'Dashboard' },
  { path: '/users', icon: 'mdi-account-group', title: 'Users' },
  { path: '/stats', icon: 'mdi-chart-bar', title: 'Statistics' },
]

const logout = () => authStore.logout()
</script>
```

### 7.4 Data Table для пользователей

```vue
<!-- src/components/UsersTable.vue -->
<template>
  <v-data-table
    :headers="headers"
    :items="users"
    :loading="loading"
    :search="search"
    class="elevation-1"
  >
    <template #top>
      <v-toolbar flat>
        <v-text-field
          v-model="search"
          prepend-icon="mdi-magnify"
          label="Search"
          single-line
          hide-details
          class="mx-4"
        />
      </v-toolbar>
    </template>

    <template #item.is_banned="{ item }">
      <v-chip :color="item.is_banned ? 'error' : 'success'" size="small">
        {{ item.is_banned ? 'Banned' : 'Active' }}
      </v-chip>
    </template>

    <template #item.actions="{ item }">
      <v-btn
        icon="mdi-pencil"
        size="small"
        variant="text"
        @click="editUser(item)"
      />
      <v-btn
        :icon="item.is_banned ? 'mdi-account-check' : 'mdi-account-cancel'"
        size="small"
        variant="text"
        :color="item.is_banned ? 'success' : 'error'"
        @click="toggleBan(item)"
      />
    </template>
  </v-data-table>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const search = ref('')
const loading = ref(false)

const headers = [
  { title: 'ID', key: 'id' },
  { title: 'Telegram ID', key: 'telegram_id' },
  { title: 'Username', key: 'username' },
  { title: 'Requests Today', key: 'daily_requests' },
  { title: 'Total Requests', key: 'total_requests' },
  { title: 'Status', key: 'is_banned' },
  { title: 'Actions', key: 'actions', sortable: false },
]

defineProps<{
  users: Array<any>
}>()

const emit = defineEmits(['edit', 'toggle-ban'])

const editUser = (user: any) => emit('edit', user)
const toggleBan = (user: any) => emit('toggle-ban', user)
</script>
```

---

## 8. Docker — Контейнеризация

### 8.1 Multi-stage Dockerfile для бота

```dockerfile
# Dockerfile
FROM python:3.11-slim as builder

WORKDIR /app

# Установка зависимостей для сборки
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Копирование и установка зависимостей
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Создание non-root пользователя
RUN useradd --create-home --shell /bin/bash appuser

# Копирование wheels из builder
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache /wheels/*

# Копирование кода
COPY bot/ ./bot/

# Смена пользователя
USER appuser

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import asyncio; asyncio.run(__import__('bot.main').main.health_check())"

CMD ["python", "-m", "bot.main"]
```

### 8.2 Docker Compose для разработки

```yaml
# docker-compose.yml
version: '3.8'

services:
  bot:
    build:
      context: .
      dockerfile: Dockerfile
    restart: unless-stopped
    env_file:
      - .env
    depends_on:
      redis:
        condition: service_healthy
      db:
        condition: service_healthy
    networks:
      - eduhelper

  admin-backend:
    build:
      context: .
      dockerfile: admin/backend/Dockerfile
    restart: unless-stopped
    env_file:
      - .env
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
    networks:
      - eduhelper
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  admin-frontend:
    build:
      context: ./admin/frontend
      args:
        VITE_API_URL: ${ADMIN_API_URL:-http://localhost:8000}
    restart: unless-stopped
    ports:
      - "3000:80"
    networks:
      - eduhelper

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis_data:/data
    networks:
      - eduhelper
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    command: redis-server --appendonly yes

  db:
    image: postgres:15-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: eduhelper
      POSTGRES_USER: ${DB_USER:-eduhelper}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - eduhelper
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-eduhelper}"]
      interval: 10s
      timeout: 5s
      retries: 5

  loki:
    image: grafana/loki:2.9.0
    ports:
      - "3100:3100"
    volumes:
      - loki_data:/loki
      - ./loki-config.yaml:/etc/loki/local-config.yaml
    command: -config.file=/etc/loki/local-config.yaml
    networks:
      - eduhelper

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD:-admin}
    networks:
      - eduhelper
    depends_on:
      - loki

networks:
  eduhelper:
    driver: bridge

volumes:
  redis_data:
  postgres_data:
  loki_data:
  grafana_data:
```

---

## 9. Логирование — Grafana Loki

### 9.1 Структурированное логирование

```python
import logging
import json
from datetime import datetime
from typing import Any
import aiohttp

class LokiHandler(logging.Handler):
    """Async handler для отправки логов в Loki"""

    def __init__(self, loki_url: str, labels: dict[str, str]):
        super().__init__()
        self.loki_url = loki_url
        self.labels = labels
        self._buffer: list[dict] = []
        self._session: aiohttp.ClientSession | None = None

    def emit(self, record: logging.LogRecord):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }

        # Добавление extra данных
        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id
        if hasattr(record, "event"):
            log_entry["event"] = record.event
        if hasattr(record, "data"):
            log_entry["data"] = record.data

        self._buffer.append(log_entry)

    async def flush_async(self):
        if not self._buffer:
            return

        if self._session is None:
            self._session = aiohttp.ClientSession()

        payload = {
            "streams": [{
                "stream": self.labels,
                "values": [
                    [str(int(datetime.utcnow().timestamp() * 1e9)), json.dumps(entry)]
                    for entry in self._buffer
                ]
            }]
        }

        try:
            async with self._session.post(self.loki_url, json=payload) as resp:
                if resp.status != 204:
                    print(f"Loki error: {await resp.text()}")
        except Exception as e:
            print(f"Failed to send logs to Loki: {e}")
        finally:
            self._buffer.clear()

# Настройка логгера
def setup_logging(loki_url: str, service: str):
    logger = logging.getLogger("eduhelper")
    logger.setLevel(logging.INFO)

    # Console handler
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    ))
    logger.addHandler(console)

    # Loki handler
    loki = LokiHandler(loki_url, {"service": service, "app": "eduhelper"})
    logger.addHandler(loki)

    return logger
```

### 9.2 Использование логгера

```python
logger = logging.getLogger("eduhelper")

# Логирование с контекстом
logger.info(
    "Request processed",
    extra={
        "user_id": 123456789,
        "event": "request_processed",
        "data": {
            "question_length": 500,
            "response_time_ms": 1200,
            "model": "gemini-3-flash-preview"
        }
    }
)
```

---

## 10. Рекомендации по безопасности

### 10.1 Защита от инъекций

```python
# Никогда не используйте f-strings для SQL!
# Плохо:
# await session.execute(f"SELECT * FROM users WHERE id = {user_id}")

# Хорошо: используйте параметризованные запросы
from sqlalchemy import select, text

# ORM style
stmt = select(User).where(User.telegram_id == telegram_id)

# Text queries с параметрами
stmt = text("SELECT * FROM users WHERE telegram_id = :telegram_id")
result = await session.execute(stmt, {"telegram_id": telegram_id})
```

### 10.2 Защита API endpoints

```python
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer
import hmac
import hashlib

security = HTTPBearer()

def verify_telegram_auth(data: dict, bot_token: str) -> bool:
    """Проверка данных Telegram Login Widget"""
    check_hash = data.pop("hash", None)
    if not check_hash:
        return False

    # Формирование строки для проверки
    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(data.items())
    )

    # Создание секретного ключа
    secret_key = hashlib.sha256(bot_token.encode()).digest()

    # Вычисление hash
    computed_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(computed_hash, check_hash)
```

### 10.3 Rate Limiting

```python
from collections import defaultdict
from datetime import datetime, timedelta
import asyncio

class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window = timedelta(seconds=window_seconds)
        self.requests: dict[int, list[datetime]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def is_allowed(self, user_id: int) -> bool:
        async with self._lock:
            now = datetime.utcnow()
            cutoff = now - self.window

            # Очистка старых запросов
            self.requests[user_id] = [
                t for t in self.requests[user_id] if t > cutoff
            ]

            if len(self.requests[user_id]) >= self.max_requests:
                return False

            self.requests[user_id].append(now)
            return True

# Использование
rate_limiter = RateLimiter(max_requests=20, window_seconds=86400)  # 20/день
```

---

## 11. Тестирование

### 11.1 Pytest + pytest-asyncio

```python
# tests/conftest.py
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

@pytest_asyncio.fixture
async def db_session():
    """Фикстура для тестовой БД"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        yield session

    await engine.dispose()

@pytest.fixture
def mock_openrouter(mocker):
    """Mock для OpenRouter API"""
    return mocker.patch(
        "bot.services.openrouter.OpenRouterClient.chat_completion",
        return_value={
            "choices": [{"message": {"content": "Test response"}}],
            "usage": {"total_tokens": 100}
        }
    )
```

### 11.2 Тестирование хендлеров aiogram

```python
# tests/test_handlers.py
import pytest
from aiogram.types import Message, User, Chat
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_start_handler(db_session, mocker):
    """Тест /start команды"""
    from bot.handlers.start import cmd_start

    # Создание mock сообщения
    message = MagicMock(spec=Message)
    message.from_user = User(id=123456789, is_bot=False, first_name="Test")
    message.chat = Chat(id=123456789, type="private")
    message.answer = AsyncMock()

    # Вызов хендлера
    await cmd_start(message, state=AsyncMock())

    # Проверка
    message.answer.assert_called_once()
    call_text = message.answer.call_args[0][0]
    assert "Привет" in call_text
```

---

## 12. Полезные зависимости (requirements.txt)

```txt
# Bot
aiogram==3.13.0
aiohttp==3.10.0
redis==5.0.0

# Database
sqlalchemy[asyncio]==2.0.25
asyncpg==0.29.0
aiosqlite==0.19.0
alembic==1.13.1

# API
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-jose[cryptography]==3.3.0
passlib[argon2]==1.7.4

# Validation
pydantic==2.5.3
pydantic-settings==2.1.0

# Utils
python-dotenv==1.0.0
httpx==0.26.0

# Logging
python-json-logger==2.0.7

# Dev/Test
pytest==7.4.4
pytest-asyncio==0.23.3
pytest-cov==4.1.0
pytest-mock==3.12.0
black==23.12.1
ruff==0.1.11
mypy==1.8.0
```

---

*Документ обновлён: Декабрь 2024*
*Источник: Context7 MCP + официальная документация*
