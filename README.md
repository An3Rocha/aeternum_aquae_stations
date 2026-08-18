# Aeternum Aquae - Estaciones Climatológicas (México)

[![QGIS Version](https://img.shields.io/badge/QGIS-3.0%2B-589632.svg?logo=qgis&logoColor=white)](https://qgis.org/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Version](https://img.shields.io/badge/Version-1.0.0-orange.svg)](https://github.com/An3Rocha/aeternum_aquae_stations/releases)
[![Python 3](https://img.shields.io/badge/Python-3.x-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)

**Aeternum Aquae - Estaciones Climatológicas** es un complemento oficial para **QGIS** desarrollado para la consulta, extracción espacial y procesamiento hidrológico de la red nacional de estaciones climatológicas de México alojadas en **Supabase** (PostGIS). 

El plugin permite realizar análisis espaciales avanzados como generación de buffers para interpolación hidrológica, selección granular de atributos y cálculo dinámico de curvas de **Intensidad-Duración-Frecuencia (IDF)** mediante la ecuación de Chen y parametrizaciones locales por estación.

---

## 🚀 Características Principales

- 🗺️ **Filtrado Geográfico Multinivel:**
  - Búsqueda por **Estado** y **Municipio**.
  - Filtrado por **Polígono de Proyecto** activo en el lienzo de QGIS (cuencas, predios, municipios de estudio).
- ⭕ **Buffer de Interpolación Hidrológica:**
  - Expansión espacial configurable en kilómetros ($0$ a $100+\text{ km}$) para capturar estaciones circundantes al área del proyecto, facilitando métodos de interpolación como Kriging, IDW o Polígonos de Thiessen.
- 📊 **Selección Granular de Atributos:**
  - Descarga optimizada seleccionando únicamente las columnas requeridas (identificadores, coordenadas, elevación, parámetros de Chen, fórmulas IDF, etc.).
- ⚡ **Motor Dinámico de Cálculo IDF:**
  - Cálculo instantáneo de intensidades de precipitación ($i$ en $\text{mm/hr}$) para múltiples periodos de retorno ($Tr$: 2, 5, 10, 20, 25, 50, 100 años) y duraciones ($d$: 5 a 120 minutos).
  - Soporte para evaluación de la **Ecuación de Chen** y fórmulas analíticas específicas por estación utilizando un motor AST matemático seguro.
- 🎯 **Carga Vectorial Directa:**
  - Creación automática de capas vectoriales en memoria (`memory:points`) proyectadas en EPSG:4326 (WGS 84) listas para visualización cartográfica y geoprocesamiento.

---

## 📥 Instalación

### Método 1: Desde el Repositorio Oficial de QGIS (Recomendado)
1. Abra **QGIS**.
2. En la barra de menú, diríjase a `Complementos` -> `Administrar e instalar complementos...`.
3. Busque `Aeternum Aquae` o `Estaciones Climatológicas`.
4. Haga clic en **Instalar complemento**.

### Método 2: Instalación manual mediante archivo ZIP
1. Descargue el archivo `aeternum_aquae_stations.zip` desde la sección de [Releases](https://github.com/An3Rocha/aeternum_aquae_stations/releases).
2. En QGIS, vaya a `Complementos` -> `Administrar e instalar complementos...` -> pestaña **Instalar a partir de ZIP**.
3. Seleccione el archivo `.zip` descargado y haga clic en **Instalar complemento**.

---

## 🛠️ Guía de Uso

1. **Abrir el complemento:**
   - Haga clic en el icono de **Aeternum Aquae** en la barra de herramientas o encuéntrelo en el menú `Complementos` -> `Aeternum Aquae` -> `Consultar Estaciones Climatológicas`.

2. **Seleccionar Criterio de Consulta:**
   - **Por División Política:** Seleccione el Estado y Municipio deseados en las listas desplegables.
   - **Por Capa de Proyecto:** Seleccione una capa poligonal activa en su proyecto QGIS y defina el radio de **Buffer de interpolación (km)** si desea incluir estaciones cercanas fuera del límite exacto.

3. **Configurar Columnas y Cálculo de Intensidades IDF:**
   - Marque las columnas que desea incluir en la capa de salida.
   - Active la casilla **"Calcular Intensidades IDF dinámicamente"** y seleccione las duraciones y periodos de retorno requeridos para su estudio hidrológico.

4. **Ejecutar y Visualizar:**
   - Haga clic en **Consultar y Cargar en QGIS**. Las estaciones se representarán como una nueva capa de puntos con su tabla de atributos completa.

---

## 📂 Estructura del Complemento

```text
aeternum_aquae_stations/
├── __init__.py                # Inicializador de QGIS (classFactory)
├── aeternum_aquae_plugin.py   # Registro en la UI, menús y acciones de QGIS
├── api_client.py              # Cliente de comunicación REST con Supabase
├── icon.png                   # Icono oficial del complemento (32x32 / 64x64)
├── intensity_engine.py        # Motor matemático de cálculo IDF (Chen / AST Parser)
├── LICENSE                    # Licencia GNU General Public License v3.0
├── main_dialog.py             # Interfaz gráfica interactiva y flujo de carga
├── metadata.txt               # Metadatos del complemento para plugins.qgis.org
└── README.md                  # Documentación del proyecto
```

---

## 👤 Autor

* **Andrés Rocha Pérez**
* **Repositorio:** [https://github.com/An3Rocha/aeternum_aquae_stations](https://github.com/An3Rocha/aeternum_aquae_stations)
* **Reporte de Problemas / Issues:** [https://github.com/An3Rocha/aeternum_aquae_stations/issues](https://github.com/An3Rocha/aeternum_aquae_stations/issues)
* **Correo de contacto:** [andres.rocha12@outlook.com](mailto:andres.rocha12@outlook.com)

---

## 📄 Licencia

Este proyecto está distribuido bajo la licencia **GNU General Public License v3.0 (GPL-3.0)**. Consulte el archivo [`LICENSE`](LICENSE) para obtener los términos completos.
