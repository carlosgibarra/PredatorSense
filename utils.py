import logging
import os
import re
import sys
from typing import List, Optional


# Constantes
MSR_VOLTAGE_DIVIDER: float = 8192.0


def setup_logging() -> None:
    """Configura logging básico. Nivel configurable vía env DEBUG=1."""
    level = logging.DEBUG if os.getenv("DEBUG") else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def _extract_integers_from_line(line: str) -> List[int]:
    """Extrae enteros positivos desde una línea cualquiera.

    Admite líneas con prefijos/etiquetas como "CPU 0: 5386" o "Voltage: 5386".
    Ignora caracteres no numéricos.
    """
    # Prioriza la parte tras el último ':' si existe
    value_part = line.split(":")[-1] if ":" in line else line
    # Captura secuencias de dígitos
    return [int(match) for match in re.findall(r"\d+", value_part)]


def parse_msr_voltage_output(raw: str) -> Optional[float]:
    """Convierte la salida cruda de rdmsr en voltaje en voltios.

    - Soporta múltiples líneas (por CPU).
    - Extrae todos los números por línea, toma el promedio global y lo divide por MSR_VOLTAGE_DIVIDER.
    - Devuelve None si no se encuentran números.
    """
    if not raw:
        return None

    numbers: List[int] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        numbers.extend(_extract_integers_from_line(line))

    if not numbers:
        return None

    average_raw = sum(numbers) / float(len(numbers))
    return average_raw / MSR_VOLTAGE_DIVIDER


def has_ec_write_support() -> bool:
    """Devuelve True si el parámetro write_support del módulo ec_sys está habilitado."""
    param_path = "/sys/module/ec_sys/parameters/write_support"
    try:
        with open(param_path, "r") as f:
            value = f.read().strip()
        return value in {"Y", "1", "y", "yes", "Yes"}
    except FileNotFoundError:
        # Puede que estemos usando /dev/ec o que ec_sys no esté cargado
        return False
    except Exception:
        return False


def get_resource_path(relative_path: str) -> str:
    """Obtiene la ruta absoluta a un recurso, compatible con PyInstaller.

    - En ejecución empaquetada: usa sys._MEIPASS
    - En desarrollo: basada en el directorio del archivo actual
    """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


