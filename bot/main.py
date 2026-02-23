"""Merge-Video Telegram Bot — aiogram 3."""

import asyncio
import os
import re
import logging

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)

import aiohttp

# Config
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
API_URL = os.getenv("API_URL", "http://localhost:8000")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(storage=MemoryStorage())

YOUTUBE_REGEX = re.compile(
    r"(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)[\w-]+"
)


# --- FSM States ---

class MergeStates(StatesGroup):
    collecting = State()  # accumulating URLs
    title = State()       # asking for video title


# --- Keyboards ---

def main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Мой список"), KeyboardButton(text="🚀 Склеить")],
            [KeyboardButton(text="🔑 Авторизовать YouTube")],
        ],
        resize_keyboard=True,
    )


def cancel_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Очистить список", callback_data="clear_list")],
    ])


# --- Handlers ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🎬 <b>Merge Video Bot</b>\n\n"
        "Отправь мне ссылки на YouTube-видео — я склею их в одно "
        "и загружу на твой YouTube.\n\n"
        "1. Сначала авторизуй YouTube (кнопка ниже)\n"
        "2. Кидай ссылки\n"
        "3. Жми «Склеить»",
        reply_markup=main_kb(),
    )
    await state.set_state(MergeStates.collecting)
    await state.set_data({"urls": []})


@dp.message(F.text == "🔑 Авторизовать YouTube")
async def cmd_auth(message: types.Message):
    user_id = str(message.from_user.id)
    auth_url = f"{API_URL}/auth/youtube?user_id=tg_{user_id}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Авторизовать YouTube", url=auth_url)],
    ])
    await message.answer("Нажми кнопку ниже, чтобы авторизовать свой YouTube:", reply_markup=kb)


@dp.message(F.text == "📋 Мой список")
async def cmd_status(message: types.Message, state: FSMContext):
    data = await state.get_data()
    urls = data.get("urls", [])
    if not urls:
        await message.answer("Список пуст. Отправь YouTube-ссылки.", reply_markup=main_kb())
        return

    lines = [f"{i+1}. {url}" for i, url in enumerate(urls)]
    await message.answer(
        f"📋 <b>Видео в списке ({len(urls)}):</b>\n\n" + "\n".join(lines),
        reply_markup=main_kb(),
    )


@dp.message(F.text == "🚀 Склеить")
async def cmd_merge(message: types.Message, state: FSMContext):
    data = await state.get_data()
    urls = data.get("urls", [])
    if len(urls) < 2:
        await message.answer("Нужно минимум 2 видео. Отправь ещё ссылки.", reply_markup=main_kb())
        return
    await message.answer("Введи название для итогового видео:")
    await state.set_state(MergeStates.title)


@dp.message(MergeStates.title)
async def handle_title(message: types.Message, state: FSMContext):
    data = await state.get_data()
    urls = data.get("urls", [])
    title = message.text.strip()
    user_id = f"tg_{message.from_user.id}"

    # Check auth
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_URL}/auth/status", params={"user_id": user_id}) as resp:
            auth_data = await resp.json()
            if not auth_data.get("authorized"):
                await message.answer(
                    "⚠️ YouTube не авторизован!\nНажми «🔑 Авторизовать YouTube» сначала.",
                    reply_markup=main_kb(),
                )
                await state.set_state(MergeStates.collecting)
                return

    # Submit merge job
    async with aiohttp.ClientSession() as session:
        payload = {"urls": urls, "title": title, "user_id": user_id}
        async with session.post(f"{API_URL}/merge", json=payload) as resp:
            if resp.status != 200:
                error = await resp.text()
                await message.answer(f"❌ Ошибка: {error}", reply_markup=main_kb())
                await state.set_state(MergeStates.collecting)
                await state.set_data({"urls": []})
                return
            result = await resp.json()

    job_id = result["job_id"]
    await message.answer(
        f"✅ Задача создана!\n\n"
        f"📌 ID: <code>{job_id}</code>\n"
        f"📹 Видео: {len(urls)}\n"
        f"📝 Название: {title}\n\n"
        f"⏳ Обработка... Пришлю результат когда будет готово.",
        reply_markup=main_kb(),
    )

    # Reset state
    await state.set_state(MergeStates.collecting)
    await state.set_data({"urls": []})

    # Poll for status
    await _poll_job(message.chat.id, job_id)


@dp.message(MergeStates.collecting)
async def handle_urls(message: types.Message, state: FSMContext):
    """Catch YouTube URLs from messages."""
    text = message.text or ""
    found = YOUTUBE_REGEX.findall(text)

    if not found:
        # Try extracting full URLs from message entities
        urls = _extract_urls(message)
        if not urls:
            await message.answer("Ссылок не найдено. Отправь YouTube URL.", reply_markup=main_kb())
            return
    else:
        # Reconstruct full URLs from regex
        urls = _extract_urls(message)

    data = await state.get_data()
    current = data.get("urls", [])
    current.extend(urls)
    await state.set_data({"urls": current})

    count = len(urls)
    total = len(current)
    await message.answer(
        f"✅ Добавлено: {count} видео\n📋 Всего в списке: {total}\n\nКидай ещё или жми «🚀 Склеить»",
        reply_markup=main_kb(),
    )


@dp.callback_query(F.data == "clear_list")
async def clear_list(callback: types.CallbackQuery, state: FSMContext):
    await state.set_data({"urls": []})
    await callback.answer("Список очищен!")
    await callback.message.answer("Список очищен. Кидай новые ссылки.", reply_markup=main_kb())


# --- Helpers ---

def _extract_urls(message: types.Message) -> list[str]:
    """Extract YouTube URLs from message text and entities."""
    urls = []
    text = message.text or ""

    # From entities
    if message.entities:
        for entity in message.entities:
            if entity.type == "url":
                url = text[entity.offset:entity.offset + entity.length]
                if YOUTUBE_REGEX.search(url):
                    urls.append(url)

    # From plain text if no entities
    if not urls:
        for match in YOUTUBE_REGEX.finditer(text):
            urls.append(match.group(0))

    return urls


async def _poll_job(chat_id: int, job_id: str, interval: int = 5, timeout: int = 600):
    """Poll job status and send result when done."""
    elapsed = 0
    last_status = ""
    async with aiohttp.ClientSession() as session:
        while elapsed < timeout:
            await asyncio.sleep(interval)
            elapsed += interval
            try:
                async with session.get(f"{API_URL}/status/{job_id}") as resp:
                    data = await resp.json()

                status = data.get("status", "")
                progress = data.get("progress", "")

                # Send update if status changed
                if status != last_status and status not in ("done", "error"):
                    status_emoji = {"downloading": "⬇️", "merging": "🔄", "uploading": "⬆️"}.get(status, "⏳")
                    await bot.send_message(chat_id, f"{status_emoji} {progress}")
                    last_status = status

                if status == "done":
                    url = data.get("result_url", "")
                    await bot.send_message(
                        chat_id,
                        f"🎉 <b>Готово!</b>\n\n🔗 <a href=\"{url}\">{url}</a>",
                    )
                    return

                if status == "error":
                    error = data.get("error", "Unknown error")
                    await bot.send_message(chat_id, f"❌ Ошибка: {error}")
                    return

            except Exception as e:
                logging.error(f"Poll error: {e}")

    await bot.send_message(chat_id, "⏱ Таймаут — задача обрабатывается слишком долго.")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
