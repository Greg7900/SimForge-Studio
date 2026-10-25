Firmwares des pédales / Pedal firmwares
=======================================
Source : https://github.com/ChrGri/DIY-Sim-Racing-FFB-Pedal (commit 7564dad, 23/10/2026)
Auteurs / Authors : ChrGri et contributeurs / and contributors.
Licence : CC BY-NC-SA 4.0 (voir / see LICENSE.txt) — usage non commercial / non-commercial use only.

Modification (pedal_pcb_v6, bridge_esp32s3) : uniquement les fichiers de compilation (bibliothèques récupérées
depuis GitHub au lieu du registre PlatformIO). Code du firmware inchangé.
Change: build files only (libraries fetched from GitHub instead of the PlatformIO registry). Firmware code unchanged.

pedal_pcb_v6/   env ControlBoard_V6 (PCB_VERSION 13) - firmware 26.43.07, config v174
pedal_pcb_v6_un_cable/  version SimForge / SimForge build : env ControlBoard_V6_OneCable (simforge_changes.diff)
                - un seul câble : réglages + manette sur l'USB natif (USE_CDC_INSTEAD_OF_UART, comme les cartes V7/V8)
                  / one cable: settings + joystick on native USB (USE_CDC_INSTEAD_OF_UART, as on V7/V8 boards)
                - bip d'identification aussi par USB / identify beep also over USB
                - version : 3e nombre + 100 (26.43.107) / version: patch + 100
                Flasher par le port UART (CH343) ; retour arrière = flasher pedal_pcb_v6 par ce même port.
                Flash through the UART port (CH343); to go back, flash pedal_pcb_v6 through that same port.
bridge_esp32s3/ env Bridge_esp32s3usbotg - optionnel / optional

Flashage manuel / Manual flashing (esptool) :
  esptool --chip esp32s3 --port COMx --baud 921600 write_flash 0x0 bootloader.bin 0x8000 partitions.bin 0xe000 boot_app0.bin 0x10000 firmware.bin
ou / or the single image: write_flash 0x0 pedal_pcb_v6_full_0x0.bin
(L'ESP32 utilise des .bin, pas des .hex / ESP32 uses .bin files, not .hex.)
