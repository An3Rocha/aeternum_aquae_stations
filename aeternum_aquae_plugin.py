# -*- coding: utf-8 -*-
"""
Aeternum Aquae QGIS Plugin Entry Point
"""

import os
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

class AeternumAquaePlugin:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.action = None
        self.dialog = None

    def initGui(self):
        icon_path = os.path.join(self.plugin_dir, "icon.png")
        if not os.path.exists(icon_path):
            icon = QIcon()
        else:
            icon = QIcon(icon_path)

        self.action = QAction(icon, "Aeternum Aquae - Estaciones Climatológicas", self.iface.mainWindow())
        self.action.triggered.connect(self.run)

        # Add toolbar button and menu item
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("&Aeternum Aquae", self.action)

    def unload(self):
        self.iface.removePluginMenu("&Aeternum Aquae", self.action)
        self.iface.removeToolBarIcon(self.action)

    def run(self):
        from .main_dialog import AeternumAquaeDialog
        if self.dialog is None:
            self.dialog = AeternumAquaeDialog(self.iface.mainWindow())
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()
