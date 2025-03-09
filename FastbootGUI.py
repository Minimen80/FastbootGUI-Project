import os
import json
import time
import platform
import subprocess
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from kivy.app import App
from kivy.clock import Clock, mainthread
from kivy.lang import Builder
from kivy.properties import StringProperty, ListProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.tabbedpanel import TabbedPanel
from kivy.uix.colorpicker import ColorPicker
from kivy.uix.spinner import Spinner
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.textinput import TextInput

# --- Variables globales pour le thème ---
theme_interface_color = [1, 1, 1, 1]
theme_log_color = [0.1, 0.1, 0.1, 1]
theme_text_color = [1, 1, 1, 1]

# --- Chaîne KV (interface) ---
KV = '''
#:import ScrollView kivy.uix.scrollview.ScrollView

<LogWidget@TextInput>:
    readonly: True
    multiline: True
    font_size: 14
    background_color: app.theme_log_color
    foreground_color: app.theme_text_color
    padding: [10, 10, 10, 10]
    size_hint_y: None
    height: self.minimum_height

<FileChooserPopup>:
    title: root.popup_title
    size_hint: 0.9, 0.9
    BoxLayout:
        orientation: 'vertical'
        spacing: 5
        padding: 10
        FileChooserListView:
            id: filechooser
            filters: [root.file_filter]
        BoxLayout:
            size_hint_y: 0.1
            spacing: 5
            Button:
                text: root.popup_title
                on_release: root.select_file(filechooser.selection)
            Button:
                text: "Cancel"
                on_release: root.dismiss()

<SettingsTab>:
    orientation: 'vertical'
    spacing: 10
    padding: 10
    Label:
        text: "Paramètres / Settings"
        size_hint_y: 0.1
    BoxLayout:
        orientation: 'vertical'
        size_hint_y: 0.6
        Label:
            text: "Interface Color"
            size_hint_y: 0.1
        ColorPicker:
            id: interface_picker
            size_hint_y: 0.3
        Label:
            text: "Log Color"
            size_hint_y: 0.1
        ColorPicker:
            id: log_picker
            size_hint_y: 0.3
        Label:
            text: "Text Color"
            size_hint_y: 0.1
        ColorPicker:
            id: text_picker
            size_hint_y: 0.3
    BoxLayout:
        size_hint_y: 0.15
        spacing: 5
        Label:
            text: "Language / Langue:"
            size_hint_x: 0.4
        Spinner:
            id: lang_spinner
            text: root.lang
            values: ['fr','en']
            size_hint_x: 0.6
    Button:
        text: root.colors_applied_text
        size_hint_y: 0.15
        on_release: root.apply_settings()

<HelpTab>:
    orientation: 'vertical'
    padding: 10
    spacing: 10
    ScrollView:
        Label:
            id: help_label
            text: root.help_text
            markup: True
            size_hint_y: None
            height: self.texture_size[1]

<FlashCustomOSTab>:
    orientation: 'vertical'
    padding: 10
    spacing: 10
    ScrollView:
        Label:
            id: custom_label
            text: root.instructions
            markup: True
            size_hint_y: None
            height: self.texture_size[1]

<DiagnosticTab>:
    orientation: 'vertical'
    padding: 10
    spacing: 10
    Label:
        text: "Historique des commandes exécutées"
        size_hint_y: 0.1
    ScrollView:
        LogWidget:
            id: diag_log

<FlashTab>:
    orientation: 'vertical'
    padding: 10
    spacing: 10
    BoxLayout:
        size_hint_y: 0.1
        Label:
            id: device_status
            text: root.device_status_text
            color: root.device_status_color
    BoxLayout:
        size_hint_y: 0.15
        spacing: 5
        Spinner:
            id: partition_spinner
            text: root.partition_text
            values: ["boot", "recovery", "vendor", "vendor_boot", "init_boot", "system", "vbmeta", "vendor_kernel", "vendor_kernel_boot", "ramdisk", "tee", "dtbo"]
        Spinner:
            id: slot_spinner
            text: root.slot_text
            values: [root.no_slot_text, root.slot_a_text, root.slot_b_text]
    BoxLayout:
        size_hint_y: 0.15
        spacing: 5
        Button:
            text: root.browse_text
            on_release: root.open_filechooser()
        Button:
            text: root.flash_text
            on_release: root.flash_device()
        Button:
            text: root.reboot_text
            on_release: root.reboot_device()
        Button:
            text: root.lock_bootloader_text
            on_release: root.lock_bootloader()
        Button:
            text: root.unlock_bootloader_text
            on_release: root.unlock_bootloader()
        Button:
            text: root.fastboot_getvar_text
            on_release: root.getvar_device()
        Button:
            text: root.clear_log_text
            on_release: root.log_clear()
        Button:
            text: root.save_log_text
            on_release: root.log_save()
    BoxLayout:
        size_hint_y: 0.15
        spacing: 5
        Button:
            text: "adb reboot bootloader"
            on_release: root.adb_reboot_bootloader()
        Button:
            text: "adb reboot recovery"
            on_release: root.adb_reboot_recovery()
    BoxLayout:
        size_hint_y: 0.15
        spacing: 5
        Button:
            text: "fastboot oem unlock"
            on_release: root.fastboot_oem_unlock()
        Button:
            text: "fastboot oem lock"
            on_release: root.fastboot_oem_lock()
    ScrollView:
        size_hint_y: 0.4
        do_scroll_x: True
        do_scroll_y: True
        LogWidget:
            id: flash_log

<SideloadTab>:
    orientation: 'vertical'
    padding: 10
    spacing: 10
    BoxLayout:
        size_hint_y: 0.15
        spacing: 5
        Label:
            text: "Mode sideload:"
            size_hint_x: 0.4
        Spinner:
            id: sideload_mode_spinner
            text: "adb -b sideload"
            values: ["adb -a sideload", "adb -b sideload"]
            size_hint_x: 0.6
    BoxLayout:
        size_hint_y: 0.15
        spacing: 5
        Button:
            text: root.browse_text
            on_release: root.open_filechooser()
        Button:
            text: root.sideload_text
            on_release: root.execute_sideload()
        Button:
            text: root.clear_log_text
            on_release: root.log_clear()
        Button:
            text: root.save_log_text
            on_release: root.log_save()
    ScrollView:
        size_hint_y: 0.4
        do_scroll_x: True
        do_scroll_y: True
        LogWidget:
            id: sideload_log

<MainTabbedPanel>:
    do_default_tab: False
    TabbedPanelItem:
        text: root.flash_tab_text
        FlashTab:
            id: flash_tab
    TabbedPanelItem:
        text: root.sideload_tab_text
        SideloadTab:
            id: sideload_tab
    TabbedPanelItem:
        text: root.custom_tab_text
        FlashCustomOSTab:
            id: custom_tab
    TabbedPanelItem:
        text: root.settings_tab_text
        SettingsTab:
            id: settings_tab
    TabbedPanelItem:
        text: root.help_tab_text
        HelpTab:
            id: help_tab
    TabbedPanelItem:
        text: "Diagnostic"
        DiagnosticTab:
            id: diag_tab
'''

# --- Charger la KV ---
Builder.load_string(KV)

# --- Traductions complètes (Français / English) ---
translations_dict = {
    "fr": {
        "menu_partition": "Partitions à flasher",
        "choose_slot": "Choisir un Slot",
        "no_slot": "Aucun Slot",
        "slot_a": "Slot A",
        "slot_b": "Slot B",
        "browse": "Parcourir",
        "flash": "Flasher",
        "reboot": "Reboot",
        "lock_bootloader": "Lock Bootloader",
        "unlock_bootloader": "Unlock Bootloader",
        "fastboot_getvar": "Fastboot GetVar All",
        "sideload": "Sideload",
        "flash_custom_os": "Flash Custom OS",
        "settings": "Paramètres",
        "help": "Aide",
        "device_fastboot_connected": "Device Connectée via Fastboot",
        "device_adb_connected": "Appareil connecté via ADB",
        "no_device": "Aucun appareil connecté",
        "flash_started": "Flash démarré",
        "flash_completed": "Flash terminé",
        "command_error": "Erreur de commande",
        "colors_applied": "Couleurs appliquées",
        "clear_log": "Effacer le log",
        "save_log": "Sauvegarder le log",
        "flash_tab": "Flash",
        "sideload_tab": "Sideload",
        "custom_tab": "Flash Custom OS",
        "settings_tab": "Paramètres",
        "help_tab": "Aide",
        "error_no_device": "Erreur : Aucun appareil détecté",
        "command_reboot_sent": "Commande Reboot envoyée",
        "command_lock_sent": "Commande Lock Bootloader envoyée",
        "command_unlock_sent": "Commande Unlock Bootloader envoyée",
        "command_getvar_sent": "Commande fastboot getvar envoyée",
        "file_selected": "Fichier sélectionné",
        "command_flash_sent": "Commande Flash envoyée",
        "custom_os_instructions": "Instructions pour flasher un firmware Custom:\n\n"
            "Ce module vous permet d'installer un firmware personnalisé sur votre appareil. Il est destiné à l'installation de ROMs custom, à la modification du bootloader et à d'autres réglages avancés du système.\n\n"
            "Utilisation :\n"
            " - Vérifiez que l'appareil est détecté en mode fastboot ou adb.\n"
            " - Sélectionnez les images à flasher (boot.img, dtbo.img, vendor_boot, etc.) selon les instructions affichées.\n"
            " - Suivez l'ordre recommandé : flashez d'abord les images disponibles, puis redémarrez en recovery pour utiliser 'Apply Update'.\n"
            " - Vous pouvez également utiliser adb sideload pour installer un package complet.\n\n"
            "Utilisations possibles :\n"
            " - Installation d'une ROM personnalisée\n"
            " - Mise à jour de composants spécifiques du système\n"
            " - Dépannage avancé et restauration de l'appareil\n"
            "Sauvegardez vos données avant toute opération de flash."
    },
    "en": {
        "menu_partition": "Partitions to Flash",
        "choose_slot": "Choose a Slot",
        "no_slot": "No Slot",
        "slot_a": "Slot A",
        "slot_b": "Slot B",
        "browse": "Browse",
        "flash": "Flash",
        "reboot": "Reboot",
        "lock_bootloader": "Lock Bootloader",
        "unlock_bootloader": "Unlock Bootloader",
        "fastboot_getvar": "Fastboot GetVar All",
        "sideload": "Sideload",
        "flash_custom_os": "Flash Custom OS",
        "settings": "Settings",
        "help": "Help",
        "device_fastboot_connected": "Device Connected via Fastboot",
        "device_adb_connected": "Device connected via ADB",
        "no_device": "No device connected",
        "flash_started": "Flashing started",
        "flash_completed": "Flashing completed",
        "command_error": "Command error",
        "colors_applied": "Colors applied",
        "clear_log": "Clear Log",
        "save_log": "Save Log",
        "flash_tab": "Flash",
        "sideload_tab": "Sideload",
        "custom_tab": "Flash Custom OS",
        "settings_tab": "Settings",
        "help_tab": "Help",
        "error_no_device": "Error: No device detected",
        "command_reboot_sent": "Reboot command sent",
        "command_lock_sent": "Lock Bootloader command sent",
        "command_unlock_sent": "Unlock Bootloader command sent",
        "command_getvar_sent": "Fastboot getvar command sent",
        "file_selected": "File selected",
        "command_flash_sent": "Flash command sent",
        "custom_os_instructions": "Instructions for flashing a Custom Firmware:\n\n"
            "This module allows you to install a custom firmware on your device. It is designed for installing custom ROMs, modifying the bootloader, and other advanced system adjustments.\n\n"
            "Usage:\n"
            " - Ensure your device is detected in fastboot or adb mode.\n"
            " - Select the images to flash (boot.img, dtbo.img, vendor_boot, etc.) as indicated by the instructions displayed.\n"
            " - Follow the recommended order: first flash the available images, then reboot into recovery to use 'Apply Update'.\n"
            " - You can also use adb sideload to install a complete package.\n\n"
            "Possible uses include:\n"
            " - Installing a custom ROM\n"
            " - Updating specific system components\n"
            " - Advanced troubleshooting and device restoration\n"
            "Make sure to back up your data before any flash operation."
    }
}
current_lang = "fr"
def t(key):
    return translations_dict[current_lang].get(key, key)

# --- Persistance des paramètres ---
SETTINGS_FILE = "user_settings.json"
default_settings = {
    "interface_color": [1, 1, 1, 1],
    "log_color": [0.1, 0.1, 0.1, 1],
    "text_color": [1, 1, 1, 1],
    "lang": "fr"
}
def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default_settings.copy()
    else:
        return default_settings.copy()
def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f)
    except Exception as e:
        print("Error saving settings:", e)

# --- Exécution des commandes en temps réel ---
def run_command_realtime(cmd, log_callback, diag_callback=None):
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, bufsize=1, universal_newlines=True)
        for line in iter(process.stdout.readline, ''):
            if line:
                log_callback(line.strip())
                if diag_callback:
                    diag_callback("CMD: " + cmd + " >> " + line.strip())
        process.stdout.close()
        process.wait()
        err = process.stderr.read()
        if err:
            log_callback(err.strip())
            if diag_callback:
                diag_callback("CMD ERROR: " + cmd + " >> " + err.strip())
    except Exception as e:
        log_callback(t("command_error") + ": " + str(e))
        if diag_callback:
            diag_callback(t("command_error") + ": " + str(e))

# --- Popup de sélection de fichier ---
class FileChooserPopup(Popup):
    popup_title = StringProperty(t("browse"))
    file_filter = StringProperty("*.zip")
    def __init__(self, callback, file_exts, **kwargs):
        super().__init__(**kwargs)
        self.callback = callback
        self.file_filter = "*" + file_exts
    def select_file(self, selection):
        if selection:
            self.callback(selection[0])
        self.dismiss()

# --- Widgets et onglets personnalisés ---
class SettingsTab(BoxLayout):
    lang = StringProperty(current_lang)
    colors_applied_text = StringProperty(t("colors_applied"))
    def on_kv_post(self, base_widget):
        self.ids.lang_spinner.bind(text=self.on_lang_change)
    def on_lang_change(self, spinner, new_lang):
        App.get_running_app().update_translations(new_lang)
    def apply_settings(self):
        settings = {
            "interface_color": self.ids.interface_picker.color,
            "log_color": self.ids.log_picker.color,
            "text_color": self.ids.text_picker.color,
            "lang": self.ids.lang_spinner.text
        }
        save_settings(settings)
        App.get_running_app().update_theme(settings)
        App.get_running_app().update_translations(settings["lang"])

class HelpTab(BoxLayout):
    help_text = StringProperty(
        "Instructions d'utilisation / Usage Instructions:\n\n"
        "1. Dans l'onglet Flash, sélectionnez la partition, le slot et le fichier à flasher, puis appuyez sur 'Flasher'.\n"
        "2. Dans l'onglet Sideload, choisissez un fichier .zip, sélectionnez le mode (adb -a ou adb -b) et lancez la commande.\n"
        "3. Utilisez les boutons de reboot, lock/unlock et fastboot getvar pour gérer l'appareil.\n"
        "4. Les logs s'affichent en temps réel dans une zone scrollable, avec possibilité d'effacer et de sauvegarder.\n"
        "5. L'onglet Diagnostic affiche l'historique des commandes exécutées pour le debug.\n"
        "6. Tous les appels de commandes s'exécutent en multi-thread."
    )

class FlashCustomOSTab(BoxLayout):
    instructions = StringProperty()
    def on_kv_post(self, base_widget):
        if current_lang == "fr":
            self.instructions = translations_dict["fr"].get("custom_os_instructions")
        else:
            self.instructions = translations_dict["en"].get("custom_os_instructions")

class DiagnosticTab(BoxLayout):
    pass

class FlashTab(BoxLayout):
    device_status_text = StringProperty(t("no_device"))
    device_status_color = ListProperty([1, 0, 0, 1])
    partition_text = StringProperty(t("menu_partition"))
    slot_text = StringProperty(t("choose_slot"))
    no_slot_text = StringProperty(t("no_slot"))
    slot_a_text = StringProperty(t("slot_a"))
    slot_b_text = StringProperty(t("slot_b"))
    browse_text = StringProperty(t("browse"))
    flash_text = StringProperty(t("flash"))
    reboot_text = StringProperty(t("reboot"))
    lock_bootloader_text = StringProperty(t("lock_bootloader"))
    unlock_bootloader_text = StringProperty(t("unlock_bootloader"))
    fastboot_getvar_text = StringProperty(t("fastboot_getvar"))
    clear_log_text = StringProperty(t("clear_log"))
    save_log_text = StringProperty(t("save_log"))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_file = None
        threading.Thread(target=self.device_detection, daemon=True).start()

    def open_filechooser(self):
        popup = FileChooserPopup(callback=self.file_selected, file_exts=".img")
        popup.open()

    def file_selected(self, path):
        self.selected_file = path
        self.ids.flash_log.text += "\n" + t("file_selected") + ": " + path

    def flash_device(self):
        if self.device_status_text == t("no_device"):
            self.ids.flash_log.text += "\n" + t("error_no_device")
            return
        if self.selected_file:
            partition = self.ids.partition_spinner.text
            slot = self.ids.slot_spinner.text
            cmd = 'fastboot flash {} "{}"'.format(partition, self.selected_file)
            self.ids.flash_log.text += "\n" + t("command_flash_sent") + " pour " + partition + " (" + slot + ")"
            executor.submit(run_command_realtime, cmd, self.update_log, self.update_diag)
        else:
            self.ids.flash_log.text += "\nAucun fichier sélectionné."

    def reboot_device(self):
        if self.device_status_text == t("no_device"):
            self.ids.flash_log.text += "\n" + t("error_no_device")
            return
        cmd = "fastboot reboot"
        self.ids.flash_log.text += "\n" + t("command_reboot_sent")
        executor.submit(run_command_realtime, cmd, self.update_log, self.update_diag)

    def lock_bootloader(self):
        if self.device_status_text == t("no_device"):
            self.ids.flash_log.text += "\n" + t("error_no_device")
            return
        cmd = "fastboot flashing lock"
        self.ids.flash_log.text += "\n" + t("command_lock_sent")
        executor.submit(run_command_realtime, cmd, self.update_log, self.update_diag)

    def unlock_bootloader(self):
        if self.device_status_text == t("no_device"):
            self.ids.flash_log.text += "\n" + t("error_no_device")
            return
        cmd = "fastboot flashing unlock"
        self.ids.flash_log.text += "\n" + t("command_unlock_sent")
        executor.submit(run_command_realtime, cmd, self.update_log, self.update_diag)

    def getvar_device(self):
        if self.device_status_text == t("no_device")