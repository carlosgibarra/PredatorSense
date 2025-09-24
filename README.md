## Linux PredatorSense™ for P-T314-51S
### Control de velocidad de ventiladores, modos de juego y undervolting en Linux. Esta aplicación está diseñada para Acer Predator Helios 300 (modelo P-T314-51S).

![Predator Sense](LinuxPredatorSense.png)

## Descargo de responsabilidad:
* Secure Boot **SÍ** es compatible si solo usas el paquete ```acpi_ec```.
* Secure Boot **NO** es compatible si quieres controlar offsets de voltaje CPU usando los paquetes ```msr-tools``` y ```undervolt```.
* Usar esta aplicación con otras laptops puede dañarlas potencialmente. Procede bajo tu propio riesgo.

## Instalación:

### Opción 1: Binario precompilado (Recomendado)
```bash
# Clonar el repositorio
git clone https://github.com/tu-usuario/Linux-PredatorSense.git
cd Linux-PredatorSense/

# Construir el binario
python3 -m venv build_env
source build_env/bin/activate
pip install PyQt5 PyQtChart pyinstaller
pyinstaller --clean --noconfirm main.spec

# Instalar (requiere root)
sudo ./configure.sh

# Ejecutar
predator-sense
```

### Opción 2: Desarrollo
```bash
# Clonar el repositorio
git clone https://github.com/tu-usuario/Linux-PredatorSense.git
cd Linux-PredatorSense/

# Instalar dependencias
pip install PyQt5 PyQtChart

# Ejecutar en modo desarrollo
sudo python3 main.py
```

## Uso:

### Línea de comandos
- Se requiere ```sudo``` para acceder a los registros Super I/O EC y aplicar offsets de undervolt.
- Ejecutar el script principal como root:
  ```
  sudo python3 main.py
  ```

### Aplicación instalada
- Una vez instalado con `sudo ./configure.sh`, puedes ejecutar:
  ```
  predator-sense
  ```
- La aplicación aparecerá en el menú de aplicaciones como "Linux PredatorSense"

### Características principales:
- **Control de ventiladores**: Modos automático, manual y turbo para CPU y GPU
- **Monitoreo en tiempo real**: Temperaturas, velocidades de ventiladores y voltaje
- **Modos Predator**: Quiet, Default, Extreme y Turbo
- **Undervolting**: Control de voltaje CPU (opcional)
- **Gráficos en tiempo real**: Visualización de sensores en la pestaña Monitoring

### NVIDIA-POWERD
- Después de cambiar modos Predator **PUEDES NECESITAR REINICIAR EL SERVICIO NVIDIA-POWERD PARA DETECTAR NUEVO TGP**
```
sudo systemctl restart nvidia-powerd
``` 
- Puedes verificar el TGP actual de la GPU con:
```
nvidia-smi
```

## Dependencias del sistema:

### Ubuntu / Linux Mint:
```bash
# Dependencias Python
sudo apt install python3-pyqt5 python3-pyqt5.qtchart

# Módulo EC (requerido)
git clone https://github.com/musikid/acpi_ec/
cd acpi_ec
sudo ./install.sh
sudo modprobe acpi_ec

# Opcional: Undervolting
pip install git+https://github.com/georgewhewell/undervolt.git
sudo apt install msr-tools
```

### Fedora:
```bash
# Dependencias Python
sudo dnf install python3-qt5 python3-pyqtchart

# Módulo EC (requerido)
sudo dnf install dkms
git clone https://github.com/musikid/acpi_ec/
cd acpi_ec
sudo ./install.sh
sudo modprobe acpi_ec

# Opcional: Undervolting
pip install git+https://github.com/georgewhewell/undervolt.git
sudo dnf install msr-tools
```

### openSUSE Tumbleweed:
```bash
# Dependencias Python
sudo zypper install python3-qt5 python3-PyQtChart

# Módulo EC (requerido)
sudo zypper install dkms
git clone https://github.com/musikid/acpi_ec/
cd acpi_ec
sudo ./install.sh
sudo modprobe acpi_ec

# Opcional: Undervolting
pip install git+https://github.com/georgewhewell/undervolt.git
sudo zypper install msr-tools
```

## Mejoras implementadas:

### Funcionalidad:
- ✅ **Parser de voltaje mejorado**: Manejo robusto de múltiples formatos de salida de `rdmsr`
- ✅ **Control de ventiladores**: Sliders manuales y modos automático/turbo completamente funcionales
- ✅ **Logging estandarizado**: Sistema de logging profesional sin prints de debug en producción
- ✅ **Manejo de errores robusto**: La aplicación no se cuelga ante problemas con el EC
- ✅ **Recursos empaquetados**: Iconos y fuentes incluidos correctamente en el binario

### Técnicas:
- ✅ **Binario PyInstaller**: Empaquetado con todas las dependencias PyQt5 incluidas
- ✅ **Instalación automática**: Script que configura módulos del kernel y permisos
- ✅ **Detección automática de backend EC**: Soporte para `/dev/ec` y `/sys/kernel/debug/ec/ec0/io`
- ✅ **Gráficos en tiempo real**: Visualización de sensores con PyQtChart

## Fork Information:
Este es un fork mejorado de [PredatorSense por mohsunb](https://github.com/mohsunb/PredatorSense), optimizado para el modelo **P-T314-51S** con mejoras significativas en estabilidad, funcionalidad y experiencia de usuario.

## Licencia:
Mismo licenciamiento que el proyecto original.
