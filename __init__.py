# -*- coding: utf-8 -*-
"""
Aeternum Aquae QGIS Plugin Initializer
"""

def classFactory(iface):
    from .aeternum_aquae_plugin import AeternumAquaePlugin
    return AeternumAquaePlugin(iface)
