import os
import sys
import logging
from utils import has_ec_write_support

# Selección robusta del backend EC: prioriza debugfs, luego /dev/ec
EC_CANDIDATES = [
    '/sys/kernel/debug/ec/ec0/io',
    '/dev/ec',
]
EC_IO_FILE = next((p for p in EC_CANDIDATES if os.path.exists(p)), EC_CANDIDATES[0])

##------------------------------##
##----Class to read/write EC----##
class ECWrite:
    def __init__(self):
        self.ec_path = EC_IO_FILE
        # Info mínima en prod
        self.buffer = b''
        self.ec_file = None
        self.setupEC()
        # Buffer previo para diagnóstico de diffs
        self._last_snapshot = None

    def setupEC(self):
        last_error = None
        # Si usamos debugfs y no hay write_support, intenta habilitarlo
        if os.path.exists('/sys/module/ec_sys') and not has_ec_write_support():
            os.system('modprobe ec_sys write_support=1 > /dev/null 2>&1')

        for candidate in EC_CANDIDATES:
            if not os.path.exists(candidate):
                continue
            try:
                f = open(candidate, 'rb+')
                # prueba de lectura mínima
                try:
                    f.seek(0)
                    _ = f.read(1)
                except OSError as oe:
                    last_error = oe
                    f.close()
                    continue
                # ok
                self.ec_path = candidate
                self.ec_file = f
                return
            except Exception as e:
                last_error = e
                continue

        logging.error("No se pudo abrir interfaz EC. Último error: %s", last_error)
        sys.exit(1)

    def ec_write(self, address, value):

        try:
            self.ec_file.seek(address)
            self.ec_file.write(bytearray([value]))

        except Exception as e:
            logging.exception("Error escribiendo EC: %s", e)
            raise

    ## Copy EC contents to buffer
    def ec_refresh(self):
        try:
            self.ec_file.seek(0)
            self.buffer = self.ec_file.read()
            # print(self.buffer)
            if self.buffer == b'':
                logging.error("EC buffer vacío tras lectura")
                raise RuntimeError("EC buffer vacío") 
            
        except Exception as e:
            logging.exception("Error refrescando EC: %s", e)
            raise           

    ## Read EC contents from buffer instead of going to disk
    def ec_read(self, address):
        try:        
            # self.ec_file.seek(address)
            # return ord(self.ec_file.read(1))

            if self.buffer == b'':
                logging.error("BUFFER EMPTY!")
                raise RuntimeError("EC buffer vacío")

            return self.buffer[address]
            # return ord(self.buffer[int(address)])
        except Exception as e:
            logging.exception("Error leyendo EC: %s", e)
            raise            

    def shutdownEC(self):
        self.ec_file.close()
        
    # ---------------- Diagnóstico ----------------
    def snapshot(self):
        """Toma una instantánea de la memoria EC actual en self.buffer."""
        self.ec_refresh()
        self._last_snapshot = self.buffer
        return self._last_snapshot

    def diff_last_snapshot(self):
        """Devuelve lista de (offset, old, new) con diferencias vs última snapshot."""
        if self._last_snapshot is None:
            return []
        self.ec_refresh()
        diffs = []
        old = self._last_snapshot
        new = self.buffer
        size = min(len(old), len(new))
        for i in range(size):
            if old[i] != new[i]:
                diffs.append((i, old[i], new[i]))
        self._last_snapshot = self.buffer
        return diffs
