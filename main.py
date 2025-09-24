import os

from PyQt5 import QtWidgets, QtGui
import sys

from PyQt5.QtCore import Qt, QTimer, QProcess
from PyQt5.QtGui import QPalette, QColor


from frontend import Ui_PredatorSense
from ecwrite import *
import enum
from utils import setup_logging, parse_msr_voltage_output, get_resource_path

##------------------------------##
##--Predator EC Register Class--##
# ECState
class ECS(enum.Enum):
    # COOL_BOOST_CONTROL = '0x10'
    # COOL_BOOST_ON = '0x01'
    # COOL_BOOST_OFF = '0x00'

    GPU_FAN_MODE_CONTROL = '0x21'
    GPU_AUTO_MODE = '0x50'
    GPU_TURBO_MODE = '0x60'
    GPU_MANUAL_MODE = '0x70'
    GPU_MANUAL_SPEED_CONTROL = '0x3A'

    CPU_FAN_MODE_CONTROL = '0x22'
    CPU_AUTO_MODE = '0x54'
    CPU_TURBO_MODE = '0x58'
    CPU_MANUAL_MODE = '0x5C'
    CPU_MANUAL_SPEED_CONTROL = '0x37'

    KB_30_SEC_AUTO = '0x06'
    KB_30_AUTO_OFF = '0x00'
    KB_30_AUTO_ON = '0x1E'

    TURBO_LED_CONTROL = '0x5B'
    TURBO_LED_ON = '0x01'
    TURBO_LED_OFF = '0x00'

    CPUFANSPEEDHIGHBITS = '0x13'
    CPUFANSPEEDLOWBITS = '0x14'
    GPUFANSPEEDHIGHBITS = '0x15'
    GPUFANSPEEDLOWBITS = '0x16'

    CPUTEMP = '0xB0'
    GPUTEMP = '0xB7'
    SYSTEMP = '0xB3'

    POWERSTATUS = '0x00'
    POWERPLUGGEDIN = '0x01'
    POWERUNPLUGGED = '0x00'

    BATTERYCHARGELIMIT = '0x03'
    BATTERYLIMITON = '0x51'
    BATTERYLIMITOFF = '0x11'

    BATTERYSTATUS = '0xC1'
    BATTERYPLUGGEDINANDCHARGING = '0x02'
    BATTERYDRAINING ='0x01'
    BATTERYOFF = '0x00'

    POWEROFFUSBCHARGING = '0x08'
    USBCHARGINGON = '0x0F'
    USBCHARGINGOFF = '0x1F'

    LCDOVERDRIVE = '0x21' # (0x_0 = off, 0x_8 = on) - high bit

    PREDATORMODE = '0x2C'
    QUIETMODE = '0x00'
    DEFAULTMODE = '0x01'
    EXTREMEMODE = '0x04'
    TURBOMODE = '0x05'

    TRACKPADSTATUS = '0xA1'
    TRACKPADENABLED = '0x00'
    TRACKPADDISABLED = '0x04'

##------------------------------##
##-------Predator Fan Mode------##
# ProcessorFanState
class PFS(enum.Enum):  
    Manual = 0
    Auto = 1
    Turbo = 2    

##------------------------------##
##---------Undervolting---------##
UNDERVOLT_PATH = "<user_path>/.local/lib/python3.8/site-packages/undervolt.py"

COREOFFSET = 80 # mV
CACHEOFFSET = 80 # mV
UPDATE_INTERVAL = 1000 #1 sec interval

## Read the current undervoltage offsets
def checkUndervoltStatus(self):
    process = QProcess()
    process.start('sudo python ' + UNDERVOLT_PATH + ' -r')
    #process.waitForStarted()
    process.waitForFinished()
    #process.waitForReadyRead()
    underVoltStatus = process.readAll()
    process.close()
    
    underVoltStatus = str(underVoltStatus, 'utf-8')
    # print(underVoltStatus)
    self.undervolt = underVoltStatus

## Apply the undervoltage offsets values
def applyUndervolt(self, core, cache):
    process = QProcess()
    process.start('sudo python ' + UNDERVOLT_PATH + ' --core -' + str(core) + ' --cache -' + str(cache))
    #process.waitForStarted()
    process.waitForFinished()
    #process.waitForReadyRead()
    process.close()

    ##  Reset the min and max values on each undervolt action
    # self.minrecordedVoltage = 2.0
    # self.maxrecordedVoltage = 0

    ## Call checkUndervoltStatus() to confirm that the setting have been properly applied.
    checkUndervoltStatus(self)

## Global process better perf instead of creating and destroying every update cycle.
voltage_process = QProcess()
## Update the current VCore
def checkVoltage(self):
    # process = QProcess()
    # process.start('sudo rdmsr 0x198 -p 0 -u --bitfield 47:32') # Processor 0
    # # process.start('sudo rdmsr 0x198 -a -u --bitfield 47:32') # All processors
    # process.waitForStarted()
    # process.waitForFinished()
    # process.waitForReadyRead()
    # voltage = process.readAll()
    # process.close()

    ## https://askubuntu.com/questions/876286/how-to-monitor-the-vcore-voltage
    voltage_process.start('sudo rdmsr 0x198 -a -u --bitfield 47:32') # All processors 
    voltage_process.waitForFinished()
    voltage_raw = voltage_process.readAll()

    parsed_voltage = 0.0
    if voltage_raw:
        try:
            raw_str = voltage_raw.data().decode('utf-8', errors='ignore')
        except Exception:
            raw_str = ''

        voltage_value = parse_msr_voltage_output(raw_str)
        if voltage_value is not None:
            parsed_voltage = voltage_value

    self.voltage = parsed_voltage

    if self.voltage < self.minrecordedVoltage:
        self.minrecordedVoltage = self.voltage
    if self.voltage > self.maxrecordedVoltage:
        self.maxrecordedVoltage = self.voltage

##------------------------------##
##-------Main QT Window---------##
class MainWindow(QtWidgets.QDialog, Ui_PredatorSense):

    def __init__(self):
        self.turboEnabled = False
        self.cpufanspeed = 0
        self.gpufanspeed = 0
        self.cpuTemp = 0
        self.gpuTemp = 0
        self.sysTemp = 0
        self.voltage = 0.5
        self.underVolt = ""
        self.minrecordedVoltage = 2.0 # V # Max operating voltage for Intel desktop 13th gen
        self.maxrecordedVoltage = 0 # V

        self.powerPluggedIn = False
        self.onBatteryPower = False
        self.displayOverdrive = False
        self.predatorMode = ECS.DEFAULTMODE.value
        self.usbCharging = ECS.USBCHARGINGON.value

        self.cpuMode = ECS.CPU_AUTO_MODE.value
        self.gpuMode = ECS.GPU_AUTO_MODE.value
        self.cpuFanMode = PFS.Auto
        self.gpuFanMode = PFS.Auto
        self.KB30Timeout = ECS.KB_30_AUTO_OFF.value
        self.trackpad = ECS.TRACKPADENABLED.value
        self.batteryChargeLimit = ECS.BATTERYLIMITOFF.value

        ## Setup the QT window
        super(MainWindow, self).__init__()
        self.setupUI(self)

        checkUndervoltStatus(self)
        self.ECHandler = ECWrite()
        self.ECHandler.ec_refresh()
        
        self.checkPowerTempFan()
        self.checkPredatorStatus()
        self.setupGUI()

        # Setup new timer to periodically read the EC regsiters and update UI
        self.setUpdateUITimer()

    ## ----------------------------------------------------
    ## Initialise the frame, check all registers and set the appropriate widgets
    def setupGUI(self):
        # if self.cb:
        #     self.coolboost_checkbox.setChecked(True)
        # self.coolboost_checkbox.clicked['bool'].connect(self.toggleCB)

        self.global_auto.clicked.connect(self.setDefaultMode)
        self.global_turbo.clicked.connect(self.setTurboMode)

        self.cpu_auto.clicked.connect(self.cpuauto)
        self.cpu_manual.clicked.connect(self.cpusetmanual)
        self.cpu_turbo.clicked.connect(self.cpumax)
        self.gpu_auto.clicked.connect(self.gpuauto)
        self.gpu_manual.clicked.connect(self.gpusetmanual)
        self.gpu_turbo.clicked.connect(self.gpumax)
        self.cpuManualSlider.valueChanged.connect(self.cpumanual)
        self.gpuManualSlider.valueChanged.connect(self.gpumanual)
        self.exit_button.clicked.connect(self.shutdown)
        self.reset_button.clicked.connect(lambda: applyUndervolt(self, 0, 0))
        self.undervolt_button.clicked.connect(lambda: applyUndervolt(self, COREOFFSET, CACHEOFFSET))

        ## ----------------------------------------------------

        ## We can toggle the register but it does not seem to actually disble the trackpad
        # if self.trackpad == int(TRACKPADENABLED, 0):
        #     self.trackpadCB.setChecked(False)
        # elif self.trackpad == int(TRACKPADDISABLED, 0):
        #     self.trackpadCB.setChecked(True)
        # else:
        #     print("Error read EC register for Trackpad: " + str(self.trackpad))
    
        ## Set the 30 sec backlight timer
        if self.KB30Timeout == int(ECS.KB_30_AUTO_OFF.value, 0):
            self.KBTimerCB.setChecked(False)
        else:
            self.KBTimerCB.setChecked(True)

        ## Set the LCD overdrive indicator
        # Check if the lower 4 bits equals 8
        overdriveEnabled = self.displayOverdrive & (1 << 3)
        if overdriveEnabled == 0:
            self.LCDOverdriveCB.setChecked(False)
        else:
            self.LCDOverdriveCB.setChecked(True)

        ## Set the USB charging indicator
        if self.usbCharging == int(ECS.USBCHARGINGON.value, 0):
            self.usbChargingCB.setChecked(True)
        elif self.usbCharging == int(ECS.USBCHARGINGOFF.value, 0):
            self.usbChargingCB.setChecked(False)
        else:
            print("Error read EC register for USB Charging: " + str(self.usbCharging))

        ## Set the charge limit indicator
        if self.batteryChargeLimit == int(ECS.BATTERYLIMITON.value, 0):
            self.chargeLimit.setChecked(True)
            self.batteryChargeLimitValue.setText("On ")
        elif self.batteryChargeLimit == int(ECS.BATTERYLIMITOFF.value, 0):
            self.chargeLimit.setChecked(False)
            self.batteryChargeLimitValue.setText("Off")
        else:
            print("Error read EC register for Charge Limit: " + str(self.batteryChargeLimit))                   

        self.setPredatorMode()
        self.setFanMode()

        ## ----------------------------------------------------

        self.quietModeCB.clicked['bool'].connect(self.setQuietMode)
        self.defaultModeCB.clicked['bool'].connect(self.setDefaultMode)
        self.extremeModeCB.clicked['bool'].connect(self.setExtremeMode)
        self.turboModeCB.clicked['bool'].connect(self.setTurboMode)

        # self.trackpadCB.clicked['bool'].connect(self.toggletrackpad)
        self.KBTimerCB.clicked['bool'].connect(self.togglekbauto)
        self.LCDOverdriveCB.clicked['bool'].connect(self.toggleLCDOverdrive)
        self.usbChargingCB.clicked['bool'].connect(self.toggleUSBCharging)
        self.chargeLimit.clicked['bool'].connect(self.togglePowerLimit)

    # Set the current fan and turbo mode
    def setFanMode(self):
        if self.cpuMode == int(ECS.CPU_AUTO_MODE.value, 0):
            self.cpuFanMode = PFS.Auto
            self.cpu_auto.setChecked(True)
        elif self.cpuMode == int(ECS.CPU_TURBO_MODE.value, 0) or self.cpuMode == int('0xA8', 0):
            self.cpuFanMode = PFS.Turbo
            self.cpu_turbo.setChecked(True)
            self.turboEnabled = True
        elif self.cpuMode == int(ECS.CPU_MANUAL_MODE.value, 0):
            self.cpuFanMode = PFS.Manual
            self.cpu_manual.setChecked(True)
        else:
            print("Warning: Unknow CPU fan mode value '" + str(self.cpuMode) + "'")
            # self.cpuauto()
        
        if self.gpuMode == int(ECS.GPU_AUTO_MODE.value, 0) or self.gpuMode == int('0x00', 0):
            self.gpuFanMode = PFS.Auto
            self.gpu_auto.setChecked(True)
        elif self.gpuMode == int(ECS.GPU_TURBO_MODE.value, 0):
            self.gpuFanMode = PFS.Turbo
            self.gpu_turbo.setChecked(True)
        elif self.gpuMode == int(ECS.GPU_MANUAL_MODE.value, 0):
            self.gpuFanMode = PFS.Manual
            self.gpu_manual.setChecked(True)
        else:
            print("Warning: Unknow GPU fan mode value '" + str(self.gpuMode) + "'")
            # self.gpuauto()

        # if cpuTurboEnabled and gpuTurboEnabled:
        if self.turboEnabled:
            self.global_turbo.setChecked(True)
            self.cpu_turbo.setChecked(True)
            self.gpu_turbo.setChecked(True)
            self.predatorMode = int(ECS.TURBOMODE.value, 0) 
            self.setTurboMode()

    # Create a timer to update the UI
    def setUpdateUITimer(self):
        self.my_timer = QTimer()
        self.my_timer.timeout.connect(self.updatePredatorStatus)
        self.my_timer.start(UPDATE_INTERVAL)

    ## ----------------------------------------------------
    ## Read the various EC registers and update the GUI
    def checkPredatorStatus(self):
        # self.cb = self.ECHandler.ec_read(int(COOL_BOOST_CONTROL, 0)) == 1
        self.cpuMode = self.ECHandler.ec_read(int(ECS.CPU_FAN_MODE_CONTROL.value, 0))
        self.gpuMode = self.ECHandler.ec_read(int(ECS.GPU_FAN_MODE_CONTROL.value, 0))
        self.KB30Timeout = self.ECHandler.ec_read(int(ECS.KB_30_SEC_AUTO.value, 0))
        self.usbCharging = self.ECHandler.ec_read(int(ECS.POWEROFFUSBCHARGING.value, 0))
        self.displayOverdrive = self.ECHandler.ec_read(int(ECS.LCDOVERDRIVE.value, 0))
        self.predatorMode = self.ECHandler.ec_read(int(ECS.PREDATORMODE.value, 0))
        self.batteryChargeLimit = self.ECHandler.ec_read(int(ECS.BATTERYCHARGELIMIT.value, 0))
        self.trackpad = self.ECHandler.ec_read(int(ECS.TRACKPADSTATUS.value, 0))

        self.cpuFanSpeed = self.ECHandler.ec_read(int(ECS.CPU_MANUAL_SPEED_CONTROL.value, 0))
        self.gpuFanSpeed = self.ECHandler.ec_read(int(ECS.GPU_MANUAL_SPEED_CONTROL.value, 0))
        self.cpuManualSlider.setSliderPosition(int(self.cpuFanSpeed / 10))
        self.gpuManualSlider.setSliderPosition(int(self.gpuFanSpeed / 10))

    ## ----------------------------------------------------
    ## Read the newest register updates
    def checkPowerTempFan(self):
        ## Refresh the EC registers first before reading values
        # -optimisation, read EC registers once per update, prevents hangs/unresponsive GUI 
        try:
            self.ECHandler.ec_refresh()
        except Exception:
            # Si se rompe la lectura del EC, no abortar la app, solo no actualizar este ciclo
            return

        self.cpuMode = self.ECHandler.ec_read(int(ECS.CPU_FAN_MODE_CONTROL.value, 0))
        self.gpuMode = self.ECHandler.ec_read(int(ECS.GPU_FAN_MODE_CONTROL.value, 0))
        self.powerPluggedIn = self.ECHandler.ec_read(int(ECS.POWERSTATUS.value, 0))
        self.onBatteryPower = self.ECHandler.ec_read(int(ECS.BATTERYSTATUS.value, 0))
        self.predatorMode = self.ECHandler.ec_read(int(ECS.PREDATORMODE.value, 0))
        self.batteryChargeLimit = self.ECHandler.ec_read(int(ECS.BATTERYCHARGELIMIT.value, 0))
        # Lecturas de diagnóstico de valores manuales (no afectan rendimiento)
        try:
            cpu_manual_val = self.ECHandler.ec_read(int(ECS.CPU_MANUAL_SPEED_CONTROL.value, 0))
            gpu_manual_val = self.ECHandler.ec_read(int(ECS.GPU_MANUAL_SPEED_CONTROL.value, 0))
            logging.debug(
                "EC modos: CPU=0x%02X GPU=0x%02X pred=0x%02X | manual: CPU=%d GPU=%d",
                self.cpuMode,
                self.gpuMode,
                self.predatorMode,
                cpu_manual_val,
                gpu_manual_val,
            )
        except Exception:
            pass

        self.cpuTemp = self.ECHandler.ec_read(int(ECS.CPUTEMP.value, 0))
        self.gpuTemp = self.ECHandler.ec_read(int(ECS.GPUTEMP.value, 0))
        self.sysTemp = self.ECHandler.ec_read(int(ECS.SYSTEMP.value, 0))

        cpufanspeedHighBits = self.ECHandler.ec_read(int(ECS.CPUFANSPEEDHIGHBITS.value, 0))
        cpufanspeedLowBits = self.ECHandler.ec_read(int(ECS.CPUFANSPEEDLOWBITS.value, 0))
        ## example
        # cpufanspeed = '0x068B'
        # 1675
        # Alto:0x13, Bajo:0x14 → valor = (alto << 8) | bajo
        self.cpufanspeed = (cpufanspeedHighBits << 8) | cpufanspeedLowBits

        gpufanspeedHighBits = self.ECHandler.ec_read(int(ECS.GPUFANSPEEDHIGHBITS.value, 0))
        gpufanspeedLowBits = self.ECHandler.ec_read(int(ECS.GPUFANSPEEDLOWBITS.value, 0))
        self.gpufanspeed = (gpufanspeedHighBits << 8) | gpufanspeedLowBits
        # print("cpufanspeed: " + str(cpufanspeed))
        # print("gpufanspeed: " + gpufanspeed)

    ## ---------Radio Button callback functions------------
    def setQuietMode(self):
        self.ECHandler.ec_write(int(ECS.PREDATORMODE.value, 0), int(ECS.QUIETMODE.value, 0))
        self.setGlobalAuto()

    def setDefaultMode(self):
        self.ECHandler.ec_write(int(ECS.PREDATORMODE.value, 0), int(ECS.DEFAULTMODE.value, 0))
        self.setGlobalAuto() 

    def setExtremeMode(self):
        self.ECHandler.ec_write(int(ECS.PREDATORMODE.value, 0), int(ECS.EXTREMEMODE.value, 0))
        self.setGlobalAuto()

    def setTurboMode(self):
        self.ECHandler.ec_write(int(ECS.PREDATORMODE.value, 0), int(ECS.TURBOMODE.value, 0))
        self.setGlobalTurbo()

    def setGlobalAuto(self):
        if self.turboEnabled:
            self.turboEnabled = False

            self.cpuauto()
            self.gpuauto()

            self.global_auto.setChecked(True)
            self.cpu_auto.setChecked(True)
            self.gpu_auto.setChecked(True)

    def setGlobalTurbo(self):
        if not self.turboEnabled:        
            self.turboEnabled = True

            self.cpumax()
            self.gpumax()

            self.global_turbo.setChecked(True)
            self.cpu_turbo.setChecked(True)
            self.gpu_turbo.setChecked(True)

    def cpuauto(self):
        self.ECHandler.ec_write(int(ECS.CPU_FAN_MODE_CONTROL.value, 0), int(ECS.CPU_AUTO_MODE.value, 0))
        self.cpuFanMode = PFS.Auto
        self.ledset()
        logging.debug("CPU modo -> AUTO (reg 0x22)")

    def cpumax(self):
        self.ECHandler.ec_write(int(ECS.CPU_FAN_MODE_CONTROL.value, 0), int(ECS.CPU_TURBO_MODE.value, 0))
        self.cpuFanMode = PFS.Turbo
        self.ledset()
        logging.debug("CPU modo -> TURBO (reg 0x22)")

    def cpusetmanual(self):
        self.ECHandler.ec_write(int(ECS.CPU_FAN_MODE_CONTROL.value, 0), int(ECS.CPU_MANUAL_MODE.value, 0))
        self.cpuFanMode = PFS.Manual
        # Aplicar inmediatamente el valor del slider cuando entra a manual
        level = self.cpuManualSlider.value()
        logging.info("CPU manual activado. Aplicando nivel slider=%d (valor=%d)", level, level * 10)
        self.ECHandler.ec_write(int(ECS.CPU_MANUAL_SPEED_CONTROL.value, 0), level * 10)
        # Confirmación inmediata leyendo los valores actuales desde EC
        current_mode = self.ECHandler.ec_read(int(ECS.CPU_FAN_MODE_CONTROL.value, 0))
        current_value = self.ECHandler.ec_read(int(ECS.CPU_MANUAL_SPEED_CONTROL.value, 0))
        logging.debug("CPU manual confirmación -> modo=0x%02X valor=%d", current_mode, current_value)

    def cpumanual(self, level):
        # print(str(level * 10), end=', ')
        # print(hex(level * 10))
        logging.debug("CPU slider cambiado a nivel=%d (valor=%d)", level, level * 10)
        # Diagnóstico: snapshot antes
        try:
            self.ECHandler.snapshot()
        except Exception:
            pass
        # Reafirmar modo manual por si el EC volvió a AUTO/TURBO
        self.ECHandler.ec_write(int(ECS.CPU_FAN_MODE_CONTROL.value, 0), int(ECS.CPU_MANUAL_MODE.value, 0))
        self.ECHandler.ec_write(int(ECS.CPU_MANUAL_SPEED_CONTROL.value, 0), level * 10)        
        # Confirmar lectura
        current_value = self.ECHandler.ec_read(int(ECS.CPU_MANUAL_SPEED_CONTROL.value, 0))
        logging.debug("CPU valor manual leído tras write=%d", current_value)
        # Diagnóstico: diffs de EC
        try:
            diffs = self.ECHandler.diff_last_snapshot()
            if diffs:
                logging.debug("EC diffs CPU (%d cambios): %s", len(diffs), diffs[:8])
            else:
                logging.debug("EC sin cambios tras escribir CPU manual")
        except Exception:
            pass

    def gpuauto(self):
        self.ECHandler.ec_write(int(ECS.GPU_FAN_MODE_CONTROL.value, 0), int(ECS.GPU_AUTO_MODE.value, 0))
        self.gpuFanMode = PFS.Auto
        logging.debug("GPU modo -> AUTO (reg 0x21)")

    def gpumax(self):
        self.ECHandler.ec_write(int(ECS.GPU_FAN_MODE_CONTROL.value, 0), int(ECS.GPU_TURBO_MODE.value, 0))
        self.gpuFanMode = PFS.Turbo
        logging.debug("GPU modo -> TURBO (reg 0x21)")

    def gpusetmanual(self):
        self.ECHandler.ec_write(int(ECS.GPU_FAN_MODE_CONTROL.value, 0), int(ECS.GPU_MANUAL_MODE.value, 0))
        self.gpuFanMode = PFS.Manual        
        level = self.gpuManualSlider.value()
        logging.info("GPU manual activado. Aplicando nivel slider=%d (valor=%d)", level, level * 10)
        self.ECHandler.ec_write(int(ECS.GPU_MANUAL_SPEED_CONTROL.value, 0), level * 10)
        # Confirmación
        current_mode = self.ECHandler.ec_read(int(ECS.GPU_FAN_MODE_CONTROL.value, 0))
        current_value = self.ECHandler.ec_read(int(ECS.GPU_MANUAL_SPEED_CONTROL.value, 0))
        logging.debug("GPU manual confirmación -> modo=0x%02X valor=%d", current_mode, current_value)

    def gpumanual(self, level):
        # print(level * 10, end=', ')
        # print(hex(level * 10))
        logging.debug("GPU slider cambiado a nivel=%d (valor=%d)", level, level * 10)
        try:
            self.ECHandler.snapshot()
        except Exception:
            pass
        self.ECHandler.ec_write(int(ECS.GPU_FAN_MODE_CONTROL.value, 0), int(ECS.GPU_MANUAL_MODE.value, 0))
        self.ECHandler.ec_write(int(ECS.GPU_MANUAL_SPEED_CONTROL.value, 0), level * 10)
        current_value = self.ECHandler.ec_read(int(ECS.GPU_MANUAL_SPEED_CONTROL.value, 0))
        logging.debug("GPU valor manual leído tras write=%d", current_value)
        try:
            diffs = self.ECHandler.diff_last_snapshot()
            if diffs:
                logging.debug("EC diffs GPU (%d cambios): %s", len(diffs), diffs[:8])
            else:
                logging.debug("EC sin cambios tras escribir GPU manual")
        except Exception:
            pass

    ## Toggle coolboost register
    # def toggleCB(self, tog):
    #     print('CoolBoost Toggle: ', end='')
    #     if tog:
    #         print('On')
    #         self.ECHandler.ec_write(int(COOL_BOOST_CONTROL, 0), int(COOL_BOOST_ON, 0))
    #     else:
    #         print('Off')
    #         self.ECHandler.ec_write(int(COOL_BOOST_CONTROL, 0), int(COOL_BOOST_OFF, 0))

    # Toggle 30 seconds keyboard backlight timer
    def togglekbauto(self, tog):
        if not tog:
            self.ECHandler.ec_write(int(ECS.KB_30_SEC_AUTO.value, 0), int(ECS.KB_30_AUTO_OFF.value, 0))
        else:
            self.ECHandler.ec_write(int(ECS.KB_30_SEC_AUTO.value, 0), int(ECS.KB_30_AUTO_ON.value, 0))

    # Toggle LCD Overdrive
    def toggleLCDOverdrive(self, tog):
        if tog:
            self.displayOverdrive = self.ECHandler.ec_read(int(ECS.LCDOVERDRIVE.value, 0))
            displayOverdriveMask = self.displayOverdrive + (1 << 3)
            self.ECHandler.ec_write(int(ECS.LCDOVERDRIVE.value, 0), displayOverdriveMask)
        else:
            displayOverdriveMask = self.displayOverdrive - (1 << 3)
            self.ECHandler.ec_write(int(ECS.LCDOVERDRIVE.value, 0), displayOverdriveMask)
    
    # USB charging whilst off
    def toggleUSBCharging(self, tog):
        if tog:
            self.ECHandler.ec_write(int(ECS.POWEROFFUSBCHARGING.value, 0), int(ECS.USBCHARGINGON.value, 0))
        else:
            self.ECHandler.ec_write(int(ECS.POWEROFFUSBCHARGING.value, 0), int(ECS.USBCHARGINGOFF.value, 0))

    ## We can toggle the register but it does nothing to actually disble the trackpad
    # def toggletrackpad(self, tog):
    #     if not tog:
    #         self.ECHandler.ec_write(int(ECS.TRACKPADSTATUS.value, 0), int(ECS.TRACKPADENABLED.value, 0))
    #     else:
    #         self.ECHandler.ec_write(int(ECS.TRACKPADSTATUS.value, 0), int(ECS.TRACKPADDISABLED.value, 0))

    # Toggle Power Limit
    def togglePowerLimit(self, tog):
        if tog:
            self.ECHandler.ec_write(int(ECS.BATTERYCHARGELIMIT.value, 0), int(ECS.BATTERYLIMITON.value, 0))
        else:
            self.ECHandler.ec_write(int(ECS.BATTERYCHARGELIMIT.value, 0), int(ECS.BATTERYLIMITOFF.value, 0))

    ## ----------------------------------------------------
    # Toggle the Turbo Led
    def ledset(self):
        turboLedEnabled = self.ECHandler.ec_read(int(ECS.TURBO_LED_CONTROL.value, 0)) == int(ECS.TURBO_LED_ON.value, 0)
        if self.turboEnabled:
            if not turboLedEnabled:
                self.ECHandler.ec_write(int(ECS.TURBO_LED_CONTROL.value, 0), int(ECS.TURBO_LED_ON.value, 0))     
        else:
            if turboLedEnabled:
                self.ECHandler.ec_write(int(ECS.TURBO_LED_CONTROL.value, 0), int(ECS.TURBO_LED_OFF.value, 0))         

    # Update the Battery status
    def setBatteryStatus(self):
        batteryStat = 'Discharging'
        if self.onBatteryPower == int(ECS.BATTERYPLUGGEDINANDCHARGING.value, 0):
            batteryStat = "Charging"
        elif self.onBatteryPower == int(ECS.BATTERYDRAINING.value, 0):
            batteryStat = "Discharging"
        elif self.onBatteryPower == int(ECS.BATTERYOFF.value, 0):
            batteryStat = "Battery Not In Use"
        else:
            print("Error read EC register for Battery Status: " + str(hex(self.onBatteryPower)))

        self.batteryStatusValue.setText(batteryStat)

        ## Set the battery charge indicator
        if self.batteryChargeLimit == int(ECS.BATTERYLIMITON.value, 0):
            self.batteryChargeLimitValue.setText("On")
        elif self.batteryChargeLimit == int(ECS.BATTERYLIMITOFF.value, 0):
            self.batteryChargeLimitValue.setText("Off")

    # Update the Predator state
    def setPredatorMode(self):
        # print("predatorModeValue: " + str(self.predatorMode))
        if self.predatorMode == int(ECS.QUIETMODE.value, 0):
            self.predatorModeValue.setText("Quiet\t")
            self.quietModeCB.setChecked(True)
        elif self.predatorMode == int(ECS.DEFAULTMODE.value, 0):
            self.predatorModeValue.setText("Default\t")
            self.defaultModeCB.setChecked(True)
        elif self.predatorMode == int(ECS.EXTREMEMODE.value, 0):
            self.predatorModeValue.setText("Extreme\t")
            self.extremeModeCB.setChecked(True)
        elif self.predatorMode == int(ECS.TURBOMODE.value, 0):
            self.predatorModeValue.setText("Turbo\t")
            self.turboModeCB.setChecked(True)
        else:
            print("Error read EC register for Predator Mode: " + str(self.predatorMode))

        # self.predatorModeValue.adjustSize()

    # Update the UI state
    def updatePredatorStatus(self):
        checkVoltage(self)
        # print(self.voltage)
        minmaxVoltages = str("%1.2f" % self.minrecordedVoltage) + " / " + str("%1.2f" % self.maxrecordedVoltage)
        # print(minmaxVoltages)
        self.voltageValue.setText(str("%1.2f" % self.voltage))
        self.voltageMinMaxValue.setText(minmaxVoltages)

        self.undervoltStatus.setText(self.undervolt)

        self.checkPowerTempFan()

        # print(self.cpuMode)
        # print(self.gpuMode)
        # print(int(ECS.CPU_TURBO_MODE.value, 0))
        # print(int(ECS.GPU_TURBO_MODE.value, 0))
        # print("-----------")

        if (self.cpuMode == int(ECS.CPU_TURBO_MODE.value, 0) or self.cpuMode == int('0xA8', 0)) and self.gpuMode == int(ECS.GPU_TURBO_MODE.value, 0):
            if not self.turboEnabled:
                self.setTurboMode()

        if self.cpuMode == int(ECS.CPU_AUTO_MODE.value, 0) and self.gpuMode == int(ECS.GPU_AUTO_MODE.value, 0):
            if self.turboEnabled:
                self.setDefaultMode()
           
        self.setBatteryStatus()
        self.setPredatorMode()

        self.voltageChart.update_data(float("%1.2f" %  self.voltage))
        self.cpuChart.update_data(self.cpuTemp)
        self.gpuChart.update_data(self.gpuTemp)
        self.sysChart.update_data(self.sysTemp)
        self.cpuFanChart.update_data(self.cpufanspeed)
        self.gpuFanChart.update_data(self.gpufanspeed)

        # print("Sensors: %s, %s, %s, %s, %s, %s, %s" % (str(self.cpufanspeed), str(self.gpufanspeed), 
        #     str(self.cpuTemp), str(self.gpuTemp), str(self.sysTemp), str(self.powerPluggedIn), str(batteryStat)))

        self.cpuFanSpeedValue.setText(str(self.cpufanspeed) + " RPM")
        self.gpuFanSpeedValue.setText(str(self.gpufanspeed) + " RPM")
        self.cpuTempValue.setText(str(self.cpuTemp) + "°")
        self.gpuTempValue.setText(str(self.gpuTemp) + "°")
        self.sysTempValue.setText(str(self.sysTemp) + "°")

        self.powerStatusValue.setText(str(self.powerPluggedIn))

        # self.updateUI(Ui_PredatorSense, str(self.cpufanspeed), str(self.gpufanspeed),
        #     str(self.cpuTemp), str(self.gpuTemp), str(self.sysTemp), str(self.powerPluggedIn), str(batteryStat))        

    ## ----------------------------------------------------
    # Exit the program cleanly
    def shutdown(self):
        self.ECHandler.shutdownEC()
        voltage_process.close()
        # app.exit(0)
        exit(0)

setup_logging()
app = QtWidgets.QApplication(sys.argv)
application = MainWindow()
app.setApplicationName("Linux PredatorSense")
application.setFixedSize(application.WIDTH, application.HEIGHT) # Makes the window not resizeable
application.setWindowIcon(QtGui.QIcon(get_resource_path('app_icon.ico')))
## Set global window opacity
# application.setWindowOpacity(0.97)

app.setStyle('Breeze')
# Dark theme implementation
palette = QPalette()
palette.setColor(QPalette.Window, QColor(53, 53, 53))
palette.setColor(QPalette.WindowText, Qt.white)
palette.setColor(QPalette.Base, QColor(25, 25, 25))
palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
palette.setColor(QPalette.ToolTipBase, Qt.black)
palette.setColor(QPalette.ToolTipText, Qt.white)
palette.setColor(QPalette.Text, Qt.white)
palette.setColor(QPalette.Button, QColor(53, 53, 53))
palette.setColor(QPalette.ButtonText, Qt.white)
palette.setColor(QPalette.BrightText, Qt.red)
palette.setColor(QPalette.Link, QColor(42, 130, 218))
palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
palette.setColor(QPalette.HighlightedText, Qt.black)
app.setPalette(palette)

application.show()
app.exec()
sys.exit()
