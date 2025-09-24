#!/usr/bin/env bash
set -euo pipefail

if [ "$EUID" -ne 0 ]; then
	echo -e "\033[0;31m./configure.sh requiere privilegios de root\033[0m"
	exit 1
fi

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_SOURCE="$PROJECT_DIR/dist/main"
BIN_REAL="/usr/bin/predator-sense-no-launch"
BIN_WRAPPER="/usr/bin/predator-sense"
DESKTOP_FILE="/usr/share/applications/predator-sense.desktop"
ICON_SRC_PNG="$PROJECT_DIR/LinuxPredatorSense.png"
ICON_DST="/usr/share/pixmaps/predator-sense.png"
FONTS_SRC="$PROJECT_DIR/fonts"
FONTS_DST="/usr/local/share/fonts/predatorsense"

# Montar debugfs si no está montado
if ! mountpoint -q /sys/kernel/debug; then
	mount -t debugfs debugfs /sys/kernel/debug || true
fi
# Cargar módulos para EC (intentar ambos métodos)
modprobe ec_sys write_support=1 || true
modprobe acpi_ec || true
modprobe acpi_ec_ecdt || true

if [ -f "$BIN_SOURCE" ]; then
	echo -e "\033[0;32mInstalando ejecutable...\033[0m"
	install -Dm755 "$BIN_SOURCE" "$BIN_REAL"
	install -Dm755 /dev/stdin "$BIN_WRAPPER" <<'EOF'
#!/usr/bin/env bash
exec pkexec env DISPLAY=$DISPLAY XAUTHORITY=$XAUTHORITY /usr/bin/predator-sense-no-launch "$@"
EOF

	echo -e "\033[0;32mCreando acceso de escritorio...\033[0m"
	install -Dm644 /dev/stdin "$DESKTOP_FILE" <<'EOF'
[Desktop Entry]
Type=Application
Name=Linux PredatorSense
Comment=Control de ventiladores Acer Predator
Exec=/usr/bin/predator-sense
Icon=predator-sense
Terminal=false
Categories=System;Utility;
EOF

	echo -e "\033[0;32mInstalando icono...\033[0m"
	if [ -f "$ICON_SRC_PNG" ]; then
		install -Dm644 "$ICON_SRC_PNG" "$ICON_DST"
	else
		# Fallback a ico si no existe el PNG
		install -Dm644 "$PROJECT_DIR/app_icon.ico" "/usr/share/icons/predator-sense"
	fi

	echo -e "\033[0;32mInstalando fuentes personalizadas...\033[0m"
	if [ -d "$FONTS_SRC" ]; then
		install -d "$FONTS_DST"
		cp -f "$FONTS_SRC"/* "$FONTS_DST"/
		fc-cache -f > /dev/null 2>&1 || true
	fi

	echo -e "\033[0;32mPredatorSense instalado correctamente\033[0m.\nUse \033[0;33mpredator-sense\033[0m o el lanzador del menú."
else
	echo -e "\033[0;31mNo se encontró $BIN_SOURCE.\nEjecute la compilación primero (consulte README.md).\033[0m"
	exit 1
fi
