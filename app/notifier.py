import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.enums import ParseMode

from app.config import settings
from app.db import get_message, update_message_status, save_feedback, get_stats
from app.profile import profile
from app.pipeline import notification_queue
from app.models import MessageStatus

logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=settings.bot_token)
dp = Dispatcher()


# --- 1. Отправка уведомлений из очереди ---

async def notification_worker():
    """
    Бесконечный цикл: берет id сообщения из очереди (notification_queue)
    и отправляет карточку в личный чат.
    """
    logger.info("Воркер уведомлений запущен.")
    while True:
        try:
            # Ждем, пока в очереди появится id
            msg_id = await notification_queue.get()
            
            # Достаем полные данные из БД
            msg = await get_message(msg_id)
            if not msg:
                logger.warning(f"Сообщение {msg_id} не найдено в БД.")
                notification_queue.task_done()
                continue

            # Формируем текст карточки
            text = f"🔥 <b>Новый опрос (score: {msg['score']})</b>\n\n"
            text += f"{msg['text'][:500]}...\n\n"
            
            # Добавляем ссылки, если есть
            if msg['links']:
                text += "🔗 <b>Ссылки:</b>\n"
                for link in msg['links']:
                    text += f"- {link}\n"
            
            # Добавляем источник (если знаем)
            text += f"\n📢 Источник: <code>{msg['source_tg_id']}</code>"

            # Кнопки обратной связи
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Открыл", callback_data=f"open_{msg_id}"),
                    InlineKeyboardButton(text="❌ Пропустить", callback_data=f"skip_{msg_id}")
                ],
                [
                    InlineKeyboardButton(text="🚫 Спам", callback_data=f"spam_{msg_id}")
                ]
            ])

            # Отправляем
            await bot.send_message(
                chat_id=settings.my_chat_id,
                text=text,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            
            # Меняем статус в БД, что мы его отправили
            await update_message_status(msg_id, MessageStatus.SENT)
            
            notification_queue.task_done()
            logger.info(f"Уведомление для id={msg_id} отправлено.")

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Ошибка в notification_worker: {e}")
            await asyncio.sleep(5)  # Пауза при ошибке, чтобы не спамить логи


# --- 2. Обработка команд ---

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("Привет! Я Survey Hunter. Буду присылать тебе подходящие опросы.")

@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    stats = await get_stats()
    text = (
        f"📊 <b>Статистика:</b>\n"
        f"Всего собрано: {stats.get('total', 0)}\n"
        f"Отправлено: {stats.get(MessageStatus.SENT, 0)}\n"
        f"Открыто: {stats.get(MessageStatus.OPENED, 0)}\n"
        f"Пропущено: {stats.get(MessageStatus.SKIPPED, 0)}\n"
        f"Спам: {stats.get(MessageStatus.SPAM, 0)}"
    )
    await message.answer(text, parse_mode=ParseMode.HTML)

@dp.message(Command("profile"))
async def cmd_profile(message: Message):
    personal = profile.get_personal()
    interests = profile.get_interests()
    text = (
        f"👤 <b>Твой профиль:</b>\n"
        f"Возраст: {personal.get('age', '?')}\n"
        f"Пол: {personal.get('gender', '?')}\n"
        f"Город: {personal.get('city', '?')}\n"
        f"Интересы: {', '.join(interests) if interests else 'не указаны'}"
    )
    await message.answer(text, parse_mode=ParseMode.HTML)


# --- 3. Обработка нажатий на inline-кнопки ---

@dp.callback_query(F.data.startswith("open_"))
async def cb_open(callback: CallbackQuery):
    msg_id = int(callback.data.split("_")[1])
    await update_message_status(msg_id, MessageStatus.OPENED)
    await save_feedback(msg_id, "opened")
    await callback.message.edit_reply_markup(reply_markup=None)  # Убираем кнопки
    await callback.answer("Отмечено как открытое ✅")

@dp.callback_query(F.data.startswith("skip_"))
async def cb_skip(callback: CallbackQuery):
    msg_id = int(callback.data.split("_")[1])
    await update_message_status(msg_id, MessageStatus.SKIPPED)
    await save_feedback(msg_id, "skipped")
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("Пропущено ❌")

@dp.callback_query(F.data.startswith("spam_"))
async def cb_spam(callback: CallbackQuery):
    msg_id = int(callback.data.split("_")[1])
    await update_message_status(msg_id, MessageStatus.SPAM)
    await save_feedback(msg_id, "spam")
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("Отмечено как спам 🚫")