import re
import requests
import time
import logging
from datetime import datetime
from validators import luhn_check  # ✅ Ahora importamos luhn_check desde validators.py

# Configuración de logs para depuración
LOG_FILE = "bot.log"
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Expresión regular para detectar tarjetas en cualquier formato
CARD_PATTERN = re.compile(
    r"(\d{4}[^\d]*\d{4}[^\d]*\d{4}[^\d]*\d{3,4})[^\d]*(\d{1,2})[^\d]*(\d{2,4})[^\d]*(\d{3,4})"
)

BIN_URL = "https://bins.antipublic.cc/bins/{}"
BIN_CACHE = {}  # Caché de BIN para evitar consultas repetidas
CACHE_EXPIRATION = 3600  # 1 hora en segundos

def normalize_date(month, year):
    """Convierte mes y año a formato estándar (MM/YYYY)."""
    current_year = datetime.now().year
    current_century = (current_year // 100) * 100  # Obtiene el siglo actual (ej: 2000)

    # Asegurar que el mes tenga dos dígitos
    month = f"{int(month):02d}"

    # Si el año tiene 2 dígitos, convertirlo a 4
    year = int(year)
    if year < 100:
        year += current_century if year + current_century >= current_year else current_century + 100

    return month, str(year)

def extract_cards(text):
    """Extrae tarjetas sin importar el formato en que estén escritas."""
    text = re.sub(r"[\n\r]+", " ", text)  # Reemplazar saltos de línea con espacios
    matches = CARD_PATTERN.findall(text)
    
    valid_cards = []
    for match in matches:
        # Limpiar números de la tarjeta, eliminando cualquier caracter extraño
        card_number = re.sub(r"[^\d]", "", match[0])
        month = match[1]
        year = match[2]
        cvv = match[3]

        # Validar que mes y año sean valores numéricos
        if not (month.isdigit() and year.isdigit()):
            logging.warning(f"❌ Tarjeta con fecha inválida descartada: {card_number}")
            continue

        month, year = normalize_date(month, year)

        # Validar mes correcto
        if not (1 <= int(month) <= 12):
            logging.warning(f"❌ Tarjeta con mes inválido descartada: {card_number}")
            continue

        # Validar longitud de la tarjeta (entre 13 y 19 dígitos)
        if not (13 <= len(card_number) <= 19):
            logging.warning(f"❌ Tarjeta con longitud inválida descartada: {card_number}")
            continue

        # Validar que la tarjeta pase el algoritmo de Luhn
        if not luhn_check(card_number):
            logging.warning(f"❌ Tarjeta no pasó Luhn descartada: {card_number}")
            continue

        valid_cards.append({"card": card_number, "month": month, "year": year, "cvv": cvv})

    return valid_cards

def fetch_bin_data(bin_number):
    """Obtiene información del BIN con caché y validación previa."""
    
    # Validar que el BIN empiece con 3, 4, 5 o 6 antes de hacer la consulta
    if not bin_number.startswith(("3", "4", "5", "6")):
        logging.warning(f"❌ BIN inválido detectado y descartado: {bin_number}")
        return {}

    # Verificar caché antes de hacer una consulta
    if bin_number in BIN_CACHE:
        cached_data, timestamp = BIN_CACHE[bin_number]
        if time.time() - timestamp < CACHE_EXPIRATION:
            return cached_data

    retries = 3
    for attempt in range(retries):
        try:
            response = requests.get(BIN_URL.format(bin_number), timeout=3)
            if response.status_code == 200:
                BIN_CACHE[bin_number] = (response.json(), time.time())  # Guardar en caché
                return BIN_CACHE[bin_number][0]
            else:
                logging.warning(f"Intento {attempt + 1}: Error en respuesta de BIN {bin_number} - Código {response.status_code}")
        except requests.RequestException as e:
            logging.error(f"Intento {attempt + 1}: Error en consulta de BIN {bin_number}: {e}")
            time.sleep(1)

    return {}  # Si después de los intentos no se obtiene respuesta