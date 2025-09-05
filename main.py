import asyncio
import logging
import os
import uuid

import ffmpeg
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Необходимо указать BOT_TOKEN в файле .env")

VIDEO_NOTE_SIZE = 360
MAX_DURATION = 59

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def send_welcome(message: types.Message):
    await message.reply(
        "Привет! 👋\n\n"
        "Отправь мне любое видео, и я превращу его в видео-кружок (video note).\n\n"
        "Я обрежу его до 59 секунд и сделаю квадратным без искажений."
    )


@dp.message(F.video)
async def handle_video(message: types.Message):
    processing_message = await message.reply("Начинаю обработку видео... ⏳")

    unique_id = uuid.uuid4()
    input_path = f"temp_{unique_id}_input.mp4"
    output_path = f"temp_{unique_id}_output.mp4"

    try:
        await bot.download(message.video, destination=input_path)

        logging.info(f"Начинаю конвертацию файла: {input_path}")

        input_stream = ffmpeg.input(input_path)

        processed_stream = (
            input_stream.trim(duration=MAX_DURATION)
            .filter(
                "scale",
                f"if(gte(a,1),-1,{VIDEO_NOTE_SIZE})",
                f"if(gte(a,1),{VIDEO_NOTE_SIZE},-1)",
            )
            .filter("crop", VIDEO_NOTE_SIZE, VIDEO_NOTE_SIZE)
            .output(
                output_path,
                vcodec="libx264",
                acodec="aac",
                video_bitrate="1M",
                audio_bitrate="128k",
            )
            .overwrite_output()
        )

        ffmpeg.run(processed_stream, quiet=True)

        logging.info(f"Конвертация завершена. Результат: {output_path}")

        probe = ffmpeg.probe(output_path)
        video_info = next(
            (stream for stream in probe["streams"] if stream["codec_type"] == "video"),
            None,
        )
        duration = int(float(video_info["duration"]))

        video_note = FSInputFile(output_path)
        await message.reply_video_note(
            video_note=video_note,
            duration=duration,
            length=VIDEO_NOTE_SIZE,
        )

        await bot.delete_message(
            chat_id=processing_message.chat.id, message_id=processing_message.message_id
        )

    except Exception as e:
        logging.error(f"Произошла ошибка: {e}")
        await message.reply(
            "Произошла ошибка при обработке видео. 😔 Попробуйте другое видео."
        )

    finally:
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(output_path):
            os.remove(output_path)
        logging.info("Временные файлы удалены.")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
