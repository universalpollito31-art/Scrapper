import json
import os
import re
import logging
from datetime import datetime, timedelta
from collections import defaultdict

# Configuración de logs y archivos
LOG_FILE = "bot.log"
LAST_CLEAN_FILE = "last_clean.json"
FILES_TO_CLEAN = ["bot.log", "processed_cards.json", "stats.json", "last_clean.json"]
CLEAN_INTERVAL_HOURS = 24  # Tiempo en horas para eliminar archivos

def clean_old_files():
    """Borra automáticamente archivos después de 24 horas."""
    now = datetime.now()

    # Verificar si ya existe un registro de la última limpieza
    if os.path.exists(LAST_CLEAN_FILE):
        try:
            with open(LAST_CLEAN_FILE, "r") as f:
                last_clean = json.load(f).get("last_clean", None)
                if last_clean:
                    last_clean_time = datetime.strptime(last_clean, "%Y-%m-%d %H:%M:%S")
                    if (now - last_clean_time).total_seconds() < CLEAN_INTERVAL_HOURS * 3600:
                        return  # No limpiar si aún no pasaron 24 horas
        except (json.JSONDecodeError, ValueError):
            pass  # Si hay error en el archivo, limpiamos igual

    # Eliminar los archivos generados por el bot
    for file in FILES_TO_CLEAN:
        if os.path.exists(file):
            os.remove(file)
            print(f"[INFO] Archivo eliminado: {file}")

    # Guardar la fecha y hora de la última limpieza
    with open(LAST_CLEAN_FILE, "w") as f:
        json.dump({"last_clean": now.strftime("%Y-%m-%d %H:%M:%S")}, f)

    print("[INFO] Se han eliminado los archivos antiguos automáticamente.")

# Ejecutar la limpieza antes de configurar logging
clean_old_files()

# Configuración de logging
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class DuplicateCardChecker:
    def __init__(self, filename="processed_cards.json", expiration_hours=24):
        self.filename = filename
        self.expiration_hours = expiration_hours
        self.processed_cards = set()
        self.bin_count = defaultdict(int)
        self._initialize()

    def _initialize(self):
        """Carga tarjetas previas y elimina solo las expiradas correctamente."""
        if os.path.exists(self.filename):
            try:
                with open(self.filename, "r") as f:
                    data = json.load(f)
                    self.processed_cards = set(data.get("processed_cards", []))
                    self.bin_count = defaultdict(int, data.get("bin_count", {}))

                # Filtrar solo tarjetas válidas
                current_time = datetime.now()
                filtered_cards = set()

                for card in self.processed_cards:
                    if len(card) < 13 or len(card) > 19:  # Validar longitud
                        logging.warning(f"Tarjeta mal formateada eliminada: {card}")
                        continue
                    
                    filtered_cards.add(card)

                self.processed_cards = filtered_cards

            except (json.JSONDecodeError, IOError) as e:
                logging.error(f"Error cargando archivo de tarjetas: {e}")
                self.processed_cards.clear()
                self.bin_count.clear()

    def is_valid(self, card_number):
        """Verifica si una tarjeta es válida y no ha sido procesada antes."""
        card_number = re.sub(r"[^\d]", "", card_number)

        if not (13 <= len(card_number) <= 19):  # Validar longitud de tarjeta
            logging.warning(f"❌ Tarjeta inválida detectada: {card_number}")
            return False

        if not luhn_check(card_number):  # Validar con algoritmo de Luhn
            logging.warning(f"❌ Tarjeta no pasó Luhn: {card_number}")
            return False

        bin_number = card_number[:6]

        if card_number in self.processed_cards:  # Evitar duplicados
            logging.warning(f"❌ Tarjeta duplicada detectada: {card_number}")
            return False

        self._register_card(card_number)
        return True

    def _register_card(self, card_number):
        """Registra la tarjeta en la base de datos y actualiza el conteo de BIN."""
        bin_number = card_number[:6]
        self.processed_cards.add(card_number)
        self.bin_count[bin_number] += 1
        self._save_cards()

    def _save_cards(self):
        """Guarda las tarjetas procesadas en el archivo con manejo de errores."""
        try:
            with open(self.filename, "w") as f:
                json.dump(
                    {
                        "processed_cards": list(self.processed_cards),
                        "bin_count": dict(self.bin_count),
                    },
                    f,
                    indent=2
                )
        except IOError:
            logging.error("Error guardando archivo de tarjetas procesadas.")

def luhn_check(card_number):
    """Valida una tarjeta con el algoritmo de Luhn."""
    try:
        digits = list(map(int, card_number))
        checksum = sum(
            d if i % 2 == 0 else (d * 2 if d * 2 < 10 else d * 2 - 9)
            for i, d in enumerate(reversed(digits))
        )
        return checksum % 10 == 0
    except ValueError:
        logging.error(f"❌ Error en la validación de Luhn: {card_number}")
        return False