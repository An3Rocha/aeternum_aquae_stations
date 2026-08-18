# -*- coding: utf-8 -*-
"""
Main GUI Dialog for Aeternum Aquae QGIS Plugin
Compatible with QGIS 3 and QGIS 4 (PyQt5 / PyQt6)
"""

from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QDoubleSpinBox, QCheckBox, QTabWidget, QWidget, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QProgressBar, QLineEdit, QSplitter, QFileDialog, QRadioButton, QButtonGroup,
    QScrollArea, QGridLayout
)
from qgis.PyQt.QtCore import Qt, QThread, pyqtSignal, QVariant
from qgis.PyQt.QtGui import QIcon, QFont, QColor

from qgis.core import (
    QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry, QgsField,
    QgsPointXY, QgsCoordinateReferenceSystem, QgsCoordinateTransform,
    QgsWkbTypes, QgsVectorFileWriter, QgsMapLayerProxyModel
)
from qgis.gui import QgsMapLayerComboBox

import json
from .api_client import SupabaseClient
from .intensity_engine import IntensityEngine


# Define organized columns categories
ALL_COLUMNS = [
    ("Información General", [
        ("station_id", "ID de Estación", True),
        ("nombre", "Nombre", True),
        ("municipio", "Municipio", True),
        ("state", "Estado", True),
        ("altitude", "Altitud (msnm)", True),
        ("cuenca", "Cuenca Hidrológica", True),
        ("situacion", "Situación Operativa", False),
        ("tipo_est", "Tipo de Estación", False),
        ("time_begin", "Fecha Inicio Registro", False),
        ("time_end", "Fecha Fin Registro", False),
        ("anios_validos", "Años Válidos", True),
        ("pct_completitud_general", "% Completitud", True),
        ("dias_imputados", "Días Imputados", False),
        ("pct_dias_imputados", "% Días Imputados", False),
    ]),
    ("Variables Climatológicas Anuales y Mensuales", [
        ("precip_prom_anual", "Precipitación Promedio Anual (mm)", True),
        ("tmed_promedio_anual_historica", "Temp. Media Promedio Anual (°C)", False),
        ("tmin_promedio_historica", "Temp. Mínima Histórica (°C)", False),
        ("tmax_promedio_historica", "Temp. Máxima Histórica (°C)", False),
        ("evap_total_anual_historica", "Evaporación Total Anual (mm)", False),
        ("enero", "Enero (mm)", False),
        ("febrero", "Febrero (mm)", False),
        ("marzo", "Marzo (mm)", False),
        ("abril", "Abril (mm)", False),
        ("mayo", "Mayo (mm)", False),
        ("junio", "Junio (mm)", False),
        ("julio", "Julio (mm)", False),
        ("agosto", "Agosto (mm)", False),
        ("septiembre", "Septiembre (mm)", False),
        ("octubre", "Octubre (mm)", False),
        ("noviembre", "Noviembre (mm)", False),
        ("diciembre", "Diciembre (mm)", False),
        ("precip_acum_historica", "Precip. Acumulada Histórica (JSON)", False),
    ]),
    ("Periodos de Retorno y Ajuste Estadístico", [
        ("tr2", "TR 2 años (mm)", True),
        ("tr5", "TR 5 años (mm)", True),
        ("tr10", "TR 10 años (mm)", True),
        ("tr25", "TR 25 años (mm)", True),
        ("tr50", "TR 50 años (mm)", True),
        ("tr100", "TR 100 años (mm)", True),
        ("modelo", "Modelo de Distribución", False),
        ("parametros", "Parámetros de Ajuste", False),
        ("annual_maxima", "Máximos Anuales", False),
        ("estimador_tipo", "Tipo Estimador", False),
        ("estimador_valor", "Valor Estimador", False),
        ("ecm", "Error Cuadrático Medio (ECM)", False),
    ]),
    ("Ecuación de Chen y Fórmulas IDF", [
        ("chen_a", "Coeficiente Chen a", True),
        ("chen_b", "Coeficiente Chen b", True),
        ("chen_c", "Coeficiente Chen c", True),
        ("x", "Parámetro Chen x", True),
        ("k_factor", "Factor K", False),
        ("formula_i", "Fórmula de Intensidad i(t, Tr)", True),
    ])
]


class StationsFetchWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, client, filter_mode, state, municipio, layer_geojson, buffer_meters, selected_cols, calc_intensities, durations, trs, filter_processed=True):
        super().__init__()
        self.client = client
        self.filter_mode = filter_mode
        self.state = state
        self.municipio = municipio
        self.layer_geojson = layer_geojson
        self.buffer_meters = buffer_meters
        self.selected_cols = selected_cols
        self.calc_intensities = calc_intensities
        self.durations = durations
        self.trs = trs
        self.filter_processed = filter_processed

    def run(self):
        try:
            self.progress.emit("Consultando datos en Supabase...")
            if self.filter_mode == "polygon" and self.layer_geojson:
                data = self.client.query_stations_spatial(
                    geojson_geometry=self.layer_geojson,
                    buffer_meters=self.buffer_meters,
                    state=None,
                    municipio=None
                )
            else:
                data = self.client.query_stations_spatial(
                    geojson_geometry=None,
                    buffer_meters=0,
                    state=self.state,
                    municipio=self.municipio
                )
            
            raw_features = data.get("features", [])
            
            # Filtrar estaciones sin procesamiento estadístico / parámetros IDF si se solicita
            if self.filter_processed:
                features = [
                    f for f in raw_features
                    if (
                        f.get("properties", {}).get("formula_i")
                        or (
                            f.get("properties", {}).get("chen_a") is not None
                            and f.get("properties", {}).get("chen_b") is not None
                            and f.get("properties", {}).get("chen_c") is not None
                        )
                        or f.get("properties", {}).get("tr2") is not None
                        or f.get("properties", {}).get("modelo") is not None
                    )
                ]
                self.progress.emit(f"Recibidas {len(raw_features)} estaciones. {len(features)} con ajuste estadístico. Procesando...")
            else:
                features = raw_features
                self.progress.emit(f"Recibidas {len(features)} estaciones. Procesando atributos...")

            # Process column filter and dynamic intensities
            processed_features = []
            for feat in features:
                props = feat.get("properties", {})
                filtered_props = {}
                
                # Keep selected columns
                for col in self.selected_cols:
                    if col in props:
                        filtered_props[col] = props[col]
                
                # Dynamic intensities if requested
                if self.calc_intensities:
                    calc_dict = IntensityEngine.compute_custom_intensities(props, self.durations, self.trs)
                    filtered_props.update(calc_dict)

                processed_features.append({
                    "geometry": feat.get("geometry"),
                    "properties": filtered_props
                })

            self.finished.emit({
                "count": len(processed_features),
                "features": processed_features,
                "selected_cols": self.selected_cols,
                "calc_intensities": self.calc_intensities,
                "durations": self.durations,
                "trs": self.trs
            })
        except Exception as e:
            self.error.emit(str(e))


class AeternumAquaeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Aeternum Aquae - Extracción y Análisis de Estaciones")
        self.resize(720, 520)
        self.setMinimumSize(540, 420)
        self.client = SupabaseClient()
        self.column_checkboxes = {}
        self.setup_ui()
        self.load_states()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(6)

        # Header Banner (compact)
        header = QLabel("<b>🌊 Aeternum Aquae: Estaciones Climatológicas (Supabase)</b>")
        header.setStyleSheet("color: #1a5276; font-size: 14px;")
        main_layout.addWidget(header)

        # Tab Widget
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs, stretch=1)

        # TAB 1: Filtros de Consulta Espacial
        tab_filters = QWidget()
        tab_filters_layout = QVBoxLayout(tab_filters)
        tab_filters_layout.setSpacing(8)

        # Group 1: Método de Selección
        gb_mode = QGroupBox("1. Criterio de Selección Espacial / Administrativa")
        gb_mode_layout = QVBoxLayout(gb_mode)
        gb_mode_layout.setSpacing(4)

        self.rb_state = QRadioButton("Por Estado / Municipio")
        self.rb_state.setChecked(True)
        self.rb_polygon = QRadioButton("Por Capa de Proyecto / Polígono (Área de Interés)")
        self.rb_all = QRadioButton("Todo México (Toda la Base de Datos)")

        self.mode_group = QButtonGroup()
        self.mode_group.addButton(self.rb_state, 1)
        self.mode_group.addButton(self.rb_polygon, 2)
        self.mode_group.addButton(self.rb_all, 3)
        self.mode_group.buttonClicked.connect(self.on_mode_changed)

        gb_mode_layout.addWidget(self.rb_state)
        gb_mode_layout.addWidget(self.rb_polygon)
        gb_mode_layout.addWidget(self.rb_all)
        tab_filters_layout.addWidget(gb_mode)

        # Group 2: Opciones de Estado/Municipio
        self.gb_admin = QGroupBox("Filtro por Estado y Municipio")
        gb_admin_layout = QHBoxLayout(self.gb_admin)

        gb_admin_layout.addWidget(QLabel("Estado:"))
        self.cb_state = QComboBox()
        self.cb_state.addItem("Todos")
        self.cb_state.currentIndexChanged.connect(self.on_state_changed)
        gb_admin_layout.addWidget(self.cb_state, stretch=1)

        gb_admin_layout.addWidget(QLabel("Municipio:"))
        self.cb_municipio = QComboBox()
        self.cb_municipio.addItem("Todos")
        gb_admin_layout.addWidget(self.cb_municipio, stretch=1)
        tab_filters_layout.addWidget(self.gb_admin)

        # Group 3: Opciones por Capa / Polígono de Proyecto
        self.gb_polygon = QGroupBox("Filtro por Polígono / Capa de Proyecto con Buffer")
        gb_poly_layout = QVBoxLayout(self.gb_polygon)
        gb_poly_layout.setSpacing(6)

        layer_row = QHBoxLayout()
        layer_row.addWidget(QLabel("Capa Poligonal:"))
        self.cb_layer = QgsMapLayerComboBox()
        self.cb_layer.setFilters(QgsMapLayerProxyModel.Filter.PolygonLayer)
        layer_row.addWidget(self.cb_layer, stretch=1)

        self.chk_selected_only = QCheckBox("Solo geometrías seleccionadas")
        layer_row.addWidget(self.chk_selected_only)
        gb_poly_layout.addLayout(layer_row)

        buffer_row = QHBoxLayout()
        buffer_row.addWidget(QLabel("Buffer de Expansión (para interpolación IDW/Kriging):"))
        self.spin_buffer = QDoubleSpinBox()
        self.spin_buffer.setRange(0, 500)
        self.spin_buffer.setValue(10.0)
        self.spin_buffer.setSuffix(" km")
        buffer_row.addWidget(self.spin_buffer)
        buffer_row.addStretch()
        gb_poly_layout.addLayout(buffer_row)

        self.gb_polygon.setEnabled(False)
        tab_filters_layout.addWidget(self.gb_polygon)
        tab_filters_layout.addStretch()
        self.tabs.addTab(tab_filters, "📍 1. Filtros y Área")

        # TAB 2: Selección de Columnas (con ScrollArea y Grid de 2 columnas)
        tab_cols = QWidget()
        tab_cols_layout = QVBoxLayout(tab_cols)
        tab_cols_layout.setContentsMargins(6, 6, 6, 6)

        btn_cols_row = QHBoxLayout()
        btn_all = QPushButton("Seleccionar Todas")
        btn_all.clicked.connect(self.select_all_columns)
        btn_none = QPushButton("Deseleccionar Todas")
        btn_none.clicked.connect(self.deselect_all_columns)
        btn_basic = QPushButton("Solo Básicas")
        btn_basic.clicked.connect(self.select_basic_columns)
        btn_idf = QPushButton("Solo Parámetros IDF / Chen")
        btn_idf.clicked.connect(self.select_idf_columns)

        btn_cols_row.addWidget(btn_all)
        btn_cols_row.addWidget(btn_none)
        btn_cols_row.addWidget(btn_basic)
        btn_cols_row.addWidget(btn_idf)
        tab_cols_layout.addLayout(btn_cols_row)

        # Scroll Area for columns
        scroll_cols = QScrollArea()
        scroll_cols.setWidgetResizable(True)
        scroll_cols.setStyleSheet("QScrollArea { border: none; }")

        cols_container = QWidget()
        cols_container_layout = QVBoxLayout(cols_container)
        cols_container_layout.setSpacing(8)

        for category_name, cols in ALL_COLUMNS:
            cat_group = QGroupBox(category_name)
            cat_grid = QGridLayout(cat_group)
            cat_grid.setSpacing(4)
            
            for idx, (col_key, col_label, default_checked) in enumerate(cols):
                chk = QCheckBox(f"{col_label}  [{col_key}]")
                chk.setChecked(default_checked)
                self.column_checkboxes[col_key] = chk
                row = idx // 2
                col = idx % 2
                cat_grid.addWidget(chk, row, col)

            cols_container_layout.addWidget(cat_group)

        cols_container_layout.addStretch()
        scroll_cols.setWidget(cols_container)
        tab_cols_layout.addWidget(scroll_cols)
        self.tabs.addTab(tab_cols, "📋 2. Columnas a Extraer")

        # TAB 3: Motor de Cálculo Extensible de Intensidades
        tab_calc = QWidget()
        tab_calc_layout = QVBoxLayout(tab_calc)

        self.chk_enable_calc = QCheckBox("⚡ Calcular Intensidades IDF automáticamente al cargar la capa")
        self.chk_enable_calc.setChecked(True)
        tab_calc_layout.addWidget(self.chk_enable_calc)

        self.chk_filter_processed = QCheckBox("🎯 Excluir estaciones sin procesamiento de ajuste probabilístico / parámetros IDF")
        self.chk_filter_processed.setChecked(True)
        self.chk_filter_processed.setToolTip(
            "Omite aquellas estaciones que no alcanzaron el mínimo de años con registros válidos "
            "y que por ende no cuentan con coeficientes de Chen ni ajuste de distribución estadística."
        )
        tab_calc_layout.addWidget(self.chk_filter_processed)

        gb_calc_params = QGroupBox("Parámetros de Cálculo de Intensidad i (mm/hr)")
        gb_calc_layout = QVBoxLayout(gb_calc_params)

        dur_row = QHBoxLayout()
        dur_row.addWidget(QLabel("Duraciones d (minutos):"))
        self.txt_durations = QLineEdit("5, 10, 15, 30, 60, 120, 360, 720, 1440")
        dur_row.addWidget(self.txt_durations)
        gb_calc_layout.addLayout(dur_row)

        tr_row = QHBoxLayout()
        tr_row.addWidget(QLabel("Periodos de Retorno Tr (años):"))
        self.txt_trs = QLineEdit("2, 5, 10, 25, 50, 100")
        tr_row.addWidget(self.txt_trs)
        gb_calc_layout.addLayout(tr_row)

        info_calc = QLabel(
            "<b>Nota técnica:</b> El motor calcula automáticamente la intensidad en mm/hr "
            "evaluando la fórmula de la estación <i>formula_i</i> o aplicando la ecuación general de Chen "
            "a partir de <i>chen_a, chen_b, chen_c, x</i>."
        )
        info_calc.setWordWrap(True)
        gb_calc_layout.addWidget(info_calc)
        tab_calc_layout.addWidget(gb_calc_params)
        tab_calc_layout.addStretch()
        self.tabs.addTab(tab_calc, "🧮 3. Cálculo de Intensidades")

        # Bottom Controls: Progress & Action Buttons (Permanently Pinned at Bottom)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(14)
        main_layout.addWidget(self.progress_bar)

        self.lbl_status = QLabel("Listo.")
        self.lbl_status.setStyleSheet("color: #555; font-size: 11px;")
        main_layout.addWidget(self.lbl_status)

        action_row = QHBoxLayout()
        self.btn_load_qgis = QPushButton("📥 Cargar en Proyecto QGIS")
        self.btn_load_qgis.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 6px 14px; border-radius: 4px;")
        self.btn_load_qgis.clicked.connect(self.on_load_qgis)

        self.btn_cancel = QPushButton("Cerrar")
        self.btn_cancel.setStyleSheet("padding: 6px 12px;")
        self.btn_cancel.clicked.connect(self.close)

        action_row.addStretch()
        action_row.addWidget(self.btn_load_qgis)
        action_row.addWidget(self.btn_cancel)
        main_layout.addLayout(action_row)

    def on_mode_changed(self):
        is_state = self.rb_state.isChecked()
        is_poly = self.rb_polygon.isChecked()
        self.gb_admin.setEnabled(is_state)
        self.gb_polygon.setEnabled(is_poly)

    def load_states(self):
        try:
            states_data = self.client.get_states()
            self.cb_state.clear()
            self.cb_state.addItem("Todos")
            for item in states_data:
                st_name = item.get("state")
                cnt = item.get("count", 0)
                if st_name:
                    self.cb_state.addItem(f"{st_name} ({cnt})", st_name)
        except Exception as e:
            self.lbl_status.setText(f"Error al conectar con Supabase: {e}")

    def on_state_changed(self):
        state_code = self.cb_state.currentData()
        self.cb_municipio.clear()
        self.cb_municipio.addItem("Todos")
        if not state_code or state_code == "Todos":
            return
        try:
            muns = self.client.get_municipios(state_code)
            for m in muns:
                mun_name = m.get("municipio")
                cnt = m.get("count", 0)
                if mun_name:
                    self.cb_municipio.addItem(f"{mun_name} ({cnt})", mun_name)
        except Exception as e:
            self.lbl_status.setText(f"Error al cargar municipios: {e}")

    def select_all_columns(self):
        for chk in self.column_checkboxes.values():
            chk.setChecked(True)

    def deselect_all_columns(self):
        for chk in self.column_checkboxes.values():
            chk.setChecked(False)

    def select_basic_columns(self):
        basic_keys = {"station_id", "nombre", "municipio", "state", "altitude", "precip_prom_anual", "anios_validos"}
        for k, chk in self.column_checkboxes.items():
            chk.setChecked(k in basic_keys)

    def select_idf_columns(self):
        idf_keys = {"station_id", "nombre", "municipio", "state", "chen_a", "chen_b", "chen_c", "x", "formula_i", "tr2", "tr5", "tr10", "tr25", "tr50", "tr100"}
        for k, chk in self.column_checkboxes.items():
            chk.setChecked(k in idf_keys)

    def get_selected_column_keys(self):
        return [k for k, chk in self.column_checkboxes.items() if chk.isChecked()]

    def extract_polygon_geojson(self):
        layer = self.cb_layer.currentLayer()
        if not layer:
            raise ValueError("Por favor selecciona una capa poligonal válida en el proyecto QGIS.")
        
        # Transform to WGS84 EPSG:4326
        crs_src = layer.crs()
        crs_dest = QgsCoordinateReferenceSystem("EPSG:4326")
        transform = QgsCoordinateTransform(crs_src, crs_dest, QgsProject.instance())

        features = layer.selectedFeatures() if self.chk_selected_only.isChecked() else list(layer.getFeatures())
        if not features:
            raise ValueError("No se encontraron geometrías en la capa seleccionada.")

        # Combine geometries if multiple
        combined_geom = None
        for f in features:
            g = f.geometry()
            if g and not g.isEmpty():
                g.transform(transform)
                if combined_geom is None:
                    combined_geom = QgsGeometry(g)
                else:
                    combined_geom = combined_geom.combine(g)

        if not combined_geom or combined_geom.isEmpty():
            raise ValueError("No se pudo obtener una geometría poligonal válida.")

        return json.loads(combined_geom.asJson())

    def on_load_qgis(self):
        selected_cols = self.get_selected_column_keys()
        if not selected_cols:
            QMessageBox.warning(self, "Advertencia", "Por favor selecciona al menos una columna para extraer.")
            return

        filter_mode = "state"
        state = None
        municipio = None
        layer_geojson = None
        buffer_meters = 0

        if self.rb_state.isChecked():
            filter_mode = "state"
            state = self.cb_state.currentData()
            municipio = self.cb_municipio.currentData()
        elif self.rb_polygon.isChecked():
            filter_mode = "polygon"
            try:
                layer_geojson = self.extract_polygon_geojson()
                buffer_meters = self.spin_buffer.value() * 1000.0 # Convert km to meters
            except Exception as e:
                QMessageBox.critical(self, "Error de Geometría", str(e))
                return
        else:
            filter_mode = "all"

        calc_intensities = self.chk_enable_calc.isChecked()
        durations = []
        trs = []
        if calc_intensities:
            try:
                durations = [float(x.strip()) for x in self.txt_durations.text().split(",") if x.strip()]
                trs = [float(x.strip()) for x in self.txt_trs.text().split(",") if x.strip()]
            except ValueError:
                QMessageBox.warning(self, "Error", "Las duraciones y periodos de retorno deben ser números separados por comas.")
                return

        self.btn_load_qgis.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.lbl_status.setText("Conectando con Supabase...")

        filter_processed = self.chk_filter_processed.isChecked()

        self.worker = StationsFetchWorker(
            self.client, filter_mode, state, municipio, layer_geojson, buffer_meters,
            selected_cols, calc_intensities, durations, trs, filter_processed
        )
        self.worker.progress.connect(self.lbl_status.setText)
        self.worker.error.connect(self.on_fetch_error)
        self.worker.finished.connect(self.on_fetch_finished)
        self.worker.start()

    def on_fetch_error(self, err_msg):
        self.btn_load_qgis.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.lbl_status.setText("Error en la consulta.")
        QMessageBox.critical(self, "Error de Conexión", f"Ocurrió un error al consultar Supabase:\n{err_msg}")

    @staticmethod
    def create_qgs_field(col_name, sample_val):
        """Creates a QgsField with appropriate data type for QGIS 3 and QGIS 4"""
        is_int = isinstance(sample_val, int) and not isinstance(sample_val, bool)
        is_float = isinstance(sample_val, float)

        try:
            from qgis.PyQt.QtCore import QMetaType
            if is_int:
                return QgsField(col_name, QMetaType.Type.Int)
            elif is_float:
                return QgsField(col_name, QMetaType.Type.Double)
            else:
                return QgsField(col_name, QMetaType.Type.QString)
        except (ImportError, AttributeError):
            if is_int:
                return QgsField(col_name, QVariant.Int)
            elif is_float:
                return QgsField(col_name, QVariant.Double)
            else:
                return QgsField(col_name, QVariant.String)

    def on_fetch_finished(self, result):
        self.btn_load_qgis.setEnabled(True)
        self.progress_bar.setVisible(False)
        count = result.get("count", 0)
        features = result.get("features", [])

        if count == 0:
            self.lbl_status.setText("No se encontraron estaciones para los criterios seleccionados.")
            QMessageBox.information(self, "Resultado", "No se encontraron estaciones para los filtros indicados.")
            return

        # Create QGIS Vector Layer in Memory (EPSG:4326)
        layer_name = "Estaciones Supabase"
        if self.rb_state.isChecked() and self.cb_state.currentData():
            layer_name += f" - {self.cb_state.currentData()}"
        elif self.rb_polygon.isChecked():
            layer_name += f" - Buffer {self.spin_buffer.value()}km"

        layer = QgsVectorLayer("Point?crs=epsg:4326", layer_name, "memory")
        pr = layer.dataProvider()

        # Add fields
        sample_props = features[0]["properties"]
        fields = []
        for col_name in sample_props.keys():
            val = sample_props[col_name]
            fields.append(self.create_qgs_field(col_name, val))

        pr.addAttributes(fields)
        layer.updateFields()

        # Add features
        qgis_features = []
        for feat in features:
            geom_data = feat.get("geometry")
            if not geom_data or "coordinates" not in geom_data:
                continue
            coords = geom_data["coordinates"]
            qf = QgsFeature()
            qf.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(coords[0], coords[1])))
            
            attr_vals = []
            for col_name in sample_props.keys():
                v = feat["properties"].get(col_name)
                if isinstance(v, (dict, list)):
                    attr_vals.append(json.dumps(v, ensure_ascii=False))
                else:
                    attr_vals.append(v)
            qf.setAttributes(attr_vals)
            qgis_features.append(qf)

        pr.addFeatures(qgis_features)
        layer.updateExtents()

        # Add to QGIS project
        QgsProject.instance().addMapLayer(layer)
        self.lbl_status.setText(f"¡Éxito! Se cargaron {len(qgis_features)} estaciones al proyecto.")
        QMessageBox.information(
            self, "Carga Completa",
            f"Se cargaron exitosamente {len(qgis_features)} estaciones en la capa '{layer_name}'.\n"
            f"Atributos extraídos: {len(sample_props.keys())} columnas."
        )
