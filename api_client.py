# -*- coding: utf-8 -*-
"""
Supabase API Client for Aeternum Aquae QGIS Plugin
"""

import json
import urllib.request
import urllib.error
import urllib.parse

class SupabaseClient:
    DEFAULT_URL = "https://ydmzazybsbacrafogoqc.supabase.co"
    DEFAULT_KEY = "sb_publishable_Z8nzeEFUrps0OpYnrO7-QQ_ZKtJi-79"

    def __init__(self, project_url=None, publishable_key=None):
        self.project_url = (project_url or self.DEFAULT_URL).rstrip('/')
        self.publishable_key = publishable_key or self.DEFAULT_KEY

    def _get_headers(self):
        return {
            "apikey": self.publishable_key,
            "Authorization": f"Bearer {self.publishable_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "QGIS-AeternumAquae/1.0"
        }

    def _validate_url(self, url):
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ('https', 'http'):
            raise ValueError(f"Esquema de URL no permitido: {parsed.scheme}")
        return url

    def get_states(self):
        """Returns list of unique states and station counts"""
        url = self._validate_url(f"{self.project_url}/rest/v1/rpc/get_states")
        req = urllib.request.Request(url, data=b"{}", headers=self._get_headers(), method="POST")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:  # nosec B310
                return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            raise RuntimeError(f"Error al obtener estados de Supabase: {e}")

    def get_municipios(self, state=None):
        """Returns list of municipios for a specific state or all"""
        url = self._validate_url(f"{self.project_url}/rest/v1/rpc/get_municipios")
        payload = json.dumps({"p_state": state} if state else {}).encode('utf-8')
        req = urllib.request.Request(url, data=payload, headers=self._get_headers(), method="POST")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:  # nosec B310
                return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            raise RuntimeError(f"Error al obtener municipios de Supabase: {e}")

    def query_stations_spatial(self, geojson_geometry=None, buffer_meters=0, state=None, municipio=None, station_id=None):
        """
        Executes a spatial query on Supabase PostGIS with optional polygon & buffer.
        Returns a GeoJSON FeatureCollection dictionary.
        """
        url = self._validate_url(f"{self.project_url}/rest/v1/rpc/query_estaciones_spatial")
        payload = {
            "p_geojson": geojson_geometry,
            "p_buffer_meters": float(buffer_meters or 0),
            "p_state": state if state and state != "Todos" else None,
            "p_municipio": municipio if municipio and municipio != "Todos" else None,
            "p_station_id": station_id if station_id else None
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers=self._get_headers(),
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:  # nosec B310
                return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            raise RuntimeError(f"Error en consulta espacial a Supabase: {e}")

    def query_stations_direct(self, columns=None, state=None, municipio=None, limit=None):
        """Direct PostgREST table query"""
        col_str = ",".join(columns) if columns else "*"
        params = [f"select={col_str}"]
        if state and state != "Todos":
            params.append(f"state=ilike.{urllib.parse.quote(state)}")
        if municipio and municipio != "Todos":
            params.append(f"municipio=ilike.{urllib.parse.quote(municipio)}")
        if limit:
            params.append(f"limit={limit}")

        query_str = "&".join(params)
        url = self._validate_url(f"{self.project_url}/rest/v1/estaciones?{query_str}")
        req = urllib.request.Request(url, headers=self._get_headers(), method="GET")
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:  # nosec B310
                return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            raise RuntimeError(f"Error en consulta de estaciones: {e}")
