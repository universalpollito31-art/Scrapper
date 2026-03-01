import asyncio
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from telethon import TelegramClient, events, Button
from datetime import datetime
import pytz
import traceback
from validators import DuplicateCardChecker, luhn_check
from defs import extract_cards, fetch_bin_data 

# Configuración de logs
logging.basicConfig(filename="timestamps.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Configuración del bot
API_ID = 22855641
API_HASH = "6503e59a7a3fd10c38fbe4310dbf98d5"
SEND_CHAT = -1003342534044
BOT_TOKEN = "8672650823:AAGFvGu1UD8tijmv9xLRMDNFulhu98T2ZrU"

client = TelegramClient("session", API_ID, API_HASH)
bot_client = TelegramClient("bot_session", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# Inicialización de validadores y procesadores
duplicate_checker = DuplicateCardChecker()
executor = ThreadPoolExecutor(max_workers=15)

async def send_message(chat_id, message, buttons=None, file=None):
    """Envía un mensaje al chat con manejo de errores."""
    try:
        await bot_client.send_message(chat_id, message, buttons=buttons, link_preview=False, parse_mode="HTML", file=file)
    except Exception as e:
        logging.error(f"Error enviando mensaje a {chat_id}: {e}")
        print(f"[ERROR] No se pudo enviar mensaje: {e}")

@client.on(events.NewMessage)
async def process_message(event):
    """Procesa mensajes entrantes y envía solo la primera tarjeta de cada BIN."""
    text = event.raw_text or ""
    source_name = event.chat.title if event.chat else "Desconocido"

    extracted_cards = extract_cards(text)
    bin_seen = set()  # Almacena qué BINs ya fueron procesados

    for card_info in extracted_cards:
        cc = re.sub(r"\D", "", card_info["card"])
        mes, ano, cvv = card_info["month"], card_info["year"], card_info["cvv"]

        if not (13 <= len(cc) <= 19):
            print(f"❌ Tarjeta inválida detectada y descartada: {cc}")
            continue

        bin_number = cc[:6]

        if bin_number in bin_seen:
            print(f"⚠️ Se detectaron múltiples tarjetas del mismo BIN {bin_number}, solo se enviará la primera.")
            continue

        bin_seen.add(bin_number)

        if not cc.startswith(("3", "4", "5", "6")):
            print(f"❌ Tarjeta descartada porque no empieza con 3, 4, 5 o 6: {cc}")
            continue

        if not luhn_check(cc):
            print(f"❌ Tarjeta no pasó Luhn y fue descartada: {cc}")
            continue

        current_year = datetime.now().year
        current_month = datetime.now().month
        if not (current_year <= int(ano) <= current_year + 10):
            print(f"❌ Tarjeta con año inválido detectada y descartada: {cc}")
            continue
        if int(ano) == current_year and int(mes) < current_month:
            print(f"❌ Tarjeta expirada descartada: {cc}")
            continue

        if not duplicate_checker.is_valid(cc):
            print(f"❌ Tarjeta duplicada detectada y descartada: {cc}")
            continue

        tz = pytz.timezone('America/Bogota')
        now = datetime.now(tz)
        date = now.strftime("%Y-%m-%d")
        time = now.strftime("%I:%M:%S %p")

        bin_data = await asyncio.get_event_loop().run_in_executor(executor, fetch_bin_data, bin_number)

        if bin_data.get('brand', 'Desconocido') == "Desconocido" and \
           bin_data.get('level', 'Desconocido') == "Desconocido" and \
           bin_data.get('type', 'Desconocido') == "Desconocido":
            print(f"[{date} {time}] ❌ BIN desconocido, tarjeta descartada: {cc} | Origen: {source_name}")
            continue

        message = f"""
<b>#𝐘𝐒𝐏 | 𝐒𝐜𝐫𝐚𝐩𝐩𝐞𝐫 𝐂𝐚𝐫𝐝𝐬 𝐏𝐫𝐞𝐦𝐢𝐮𝐦 [㊗️]</b>
<b>#𝐁𝐈𝐍{bin_number}</b> <code>[{date}]</code> <code>[{time}]</code>
- - - - - - - - -
<a href="https://t.me/PollixUnivers">说</a> <b>𝐂𝐚𝐫𝐝</b> ≠ <code>{cc}|{mes}|{ano}|{cvv}</code>
<a href="https://t.me/PollixUnivers">说</a> <b>𝐁𝐢𝐧 𝐢𝐧𝐟𝐨</b> ≠ <code>{bin_data.get('brand', 'Desconocido')} - {bin_data.get('level', 'Desconocido')} - {bin_data.get('type', 'Desconocido')}</code>
- - - - - - - - -
<a href="https://t.me/PollixUnivers">说</a> <b>𝐁𝐚𝐧𝐤</b> ≠ <code>{bin_data.get('bank', 'Desconocido')}</code>
<a href="https://t.me/PollixUnivers">说</a> <b>𝐂𝐨𝐮𝐧𝐭𝐫𝐲</b> ≠ <code>{bin_data.get('country_name', 'Desconocido')} {bin_data.get('country_flag', '')}</code>
- - - - - - - - -
<a href="https://t.me/PollixUnivers">说</a> <b>𝐄𝐱𝐭𝐫𝐚</b> ≠ <code>{cc[:-4]}xxxx|{mes}|{ano}|rnd</code>
- - - - - - - - -
"""

        print(f"[{date} {time}] ✅ Tarjeta enviada: {cc}|{mes}|{ano}|{cvv} | Origen: {source_name}")

        buttons = [
            Button.url("𝐎𝐖𝐍𝐄𝐑", "https://t.me/AboutMePollixUnivers"),
            Button.url("𝐑𝐄𝐅𝐄𝐒", "https://t.me/+lX5ndHgBOiJlZWVh")
        ]
        image_url = "https://i.ibb.co/d19BWHy/IMG-20260301-153014-871.jpg"
        await send_message(SEND_CHAT, message, buttons=buttons, file=image_url)

# Iniciar el bot
client.start()
client.run_until_disconnected()
