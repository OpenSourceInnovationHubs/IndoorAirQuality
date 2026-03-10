"""Thin synchronous client for Magenta IoT-Hub (HTTP API)."""
from __future__ import annotations

import logging
import os
import threading
from typing import List, Dict, Optional, Any
from urllib.parse import urlencode

import requests


TIMEOUT = 10  # seconds

class MagentaIoTClient:
    """Handles login / token storage for the IoT-Hub HTTP API."""

    _LOCK = threading.RLock()

    def __init__(self) -> None:
        """Initialize the client from environment variables."""
        base_url = os.getenv("IOTHUB_BASE_URL")
        if base_url in (None, ""):
            raise RuntimeError("Environment variable IOTHUB_BASE_URL missing")
        self.base_url: str = base_url

        user = os.getenv("IOTHUB_USERNAME")
        if user in (None, ""):
            raise RuntimeError("Environment variable IOTHUB_USERNAME missing")
        self._user = user

        password = os.getenv("IOTHUB_PASSWORD")
        if password in (None, ""):
            raise RuntimeError("Environment variable IOTHUB_PASSWORD missing")
        self._password = password

        self._token: Optional[str] = os.getenv("IOTHUB_TOKEN")
        self._refresh_token: Optional[str] = None

        self.devices: dict = {} # cached device list, self.devices[<type>][<label>] = <id>


    # ---------------------------- public helpers -------------------------- #
    @property
    def token(self) -> Optional[str]:
        """ Return the current access token, or *None* if not authenticated. """
        return self._token


    @property
    def is_authenticated(self) -> bool:
        """ Check if the client is authenticated."""
        return bool(self._token)


    def check_connection(self) -> bool:
        """
        Verify that the IoT-Hub HTTP API host is reachable **without
        requiring a token**.

        We request the public Swagger UI document located at
          <BASE_URL>/swagger-ui.html

        A 200 (or any < 400) means TCP reachability and a running server.
        """

        url = f"{self.base_url.replace('/api','/').rstrip('/')}/swagger-ui.html"
        try:
            resp = requests.head(url, timeout=5)          # lightweight probe
            # some servers may not support HEAD; fall back to GET once
            if resp.status_code >= 400:
                resp = requests.get(url, timeout=5, allow_redirects=True)
            return resp.status_code < 400
        except requests.RequestException:
            return False


    # ---------------------------- Authentication -------------------------- #
    def login(self) -> bool:
        """POST /auth/login and cache access/refresh tokens."""

        url = f"{self.base_url.rstrip('/')}/auth/login"
        try:
            resp = requests.post(
                url,
                json={"username": self._user, "password": self._password},
                headers={"Accept": "application/json"},
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
        except requests.RequestException:
            return False

        try:
            data = resp.json()
            token = data["token"]
            refresh = data.get("refreshToken")
        except (ValueError, KeyError):
            return False

        with self._LOCK:
            self._token = token
            self._refresh_token = refresh
            os.environ["IOTHUB_TOKEN"] = token
        return True


    def logout(self) -> bool:
        """
        Invalidate the current token on the server (best-effort)
        and wipe local cache.
        """

        with self._LOCK:
            if not self._token:
                return True  # nothing to do

            # IoT-Hub HTTP API supports POST /auth/logout  ➜ 204 No Content
            url = f"{self.base_url.rstrip('/')}/auth/logout"
            try:
                requests.post(
                    url,
                    headers={"X-Authorization": f"Bearer {self._token}"},
                    timeout=TIMEOUT,
                ).raise_for_status()
            except requests.RequestException:
                # token might already be expired; continue clearing anyway
                pass

            self._token = None
            self._refresh_token = None
            os.environ.pop("IOTHUB_TOKEN", None)
            return True


    # --------------------------- re-create token --------------------------- #
    def recreate_token(self) -> bool:
        """Force a brand-new access token."""
        self.logout()
        return self.login()


    # ─────────────────────────── Device info ────────────────────────────
    def get_devices(self, text_search : str = "") -> dict:
        """ Retrieve a list of devices from the Magenta IoT Hub Business API. """

        if text_search not in ("", None):
            url = f"{self.base_url}/deviceInfos/all?page=0&pageSize=100&textSearch={text_search}"
        else:
            url = f"{self.base_url}/deviceInfos/all?page=0&pageSize=100"

        try:
            headers = {"X-Authorization": f"Bearer {self._token}"}
            response = requests.get(url, headers=headers, timeout=TIMEOUT)

            if response.status_code == 401:  # token expired?
                logging.warning("Token expired, attempting re-login.")
                if self.login():
                    headers["X-Authorization"] = f"Bearer {self._token}"
                    response = requests.get(url, headers=headers, timeout=TIMEOUT)
                else:
                    logging.error("Re-login failed.")
                    return {}

            if response.status_code == 200:
                self.devices = {}
                for item in response.json()["data"]:
                    if item["name"] != item["label"]:
                        if item["type"] not in self.devices:
                            self.devices[item["type"]] = {}
                        name = item["label"].split(" ")[0] if item["label"] != "" else item["name"]
                        self.devices[item["type"]][name] = item["id"]["id"]

                return self.devices
        except requests.RequestException as e:
            logging.error("Request failed: %s", e)
            return {}
        except ValueError as e:
            logging.error("Failed to parse JSON response: %s", e)
            return {}

        return {}


    def get_device_info(self, id: str | None = None, name: str | None = None) -> Optional[dict]:
        """
        Return complete device JSON for *device_id*.

        • Authentication required  → header ``X-Authorization: Bearer <token>``
        • If token is missing or expired, we auto-login once.
        • Returns *None* on error.
        """
        if name not in (None, ""):
            if not self.devices:
                self.get_devices()
            for dev_type in self.devices:
                if name in self.devices[dev_type]:
                    id = self.devices[dev_type][name]
                    break
        if id in (None, ""):
            id = os.getenv("IOTHUB_DEVICE_ID")
        if not id:
            return {}

        if not self._token and not self.login():
            logging.error("Failed to login and retrieve token.")
            return None

        url = f"{self.base_url.rstrip('/')}/device/{id}"
        headers = {"X-Authorization": f"Bearer {self._token}"}

        try:
            response = requests.get(url, headers=headers, timeout=TIMEOUT)
            if response.status_code == 401:  # token expired?
                logging.warning("Token expired, attempting re-login.")
                if self.login():
                    headers["X-Authorization"] = f"Bearer {self._token}"
                    response = requests.get(url, headers=headers, timeout=TIMEOUT)
                else:
                    logging.error("Re-login failed.")
                    return None
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logging.error("Request failed: %s", e)
            return None
        except ValueError as e:
            logging.error("Failed to parse JSON response: %s", e)
            return None


    # ──────────────────────── latest time-series values ───────────────────
    def get_latest_values(
        self,
        *,
        id: str | None = None,
        name: str | None = None,
        keys: list[str] | None = None,
    ) -> Optional[dict]:
        """
        Return the latest value(s) for this device.

        Parameters
        ----------
        id : str | None
            Device ID.  If *None* → use environment variable ``IOTHUB_DEVICE_ID``.
        name : str | None
        keys : list[str] | None
            If given → restrict to these time-series keys.  Otherwise IoT-Hub
            returns the latest sample for *all* keys.

        Returns
        -------
        dict | None
            Whatever JSON IoT-Hub returns, or ``None`` on error.
        """
        if name not in (None, ""):
            if not self.devices:
                self.get_devices()
            for dev_type in self.devices:
                if name in self.devices[dev_type]:
                    id = self.devices[dev_type][name]
                    break
        if id in (None, ""):
            id = os.getenv("IOTHUB_DEVICE_ID")
        if not id:
            return None

        if not self._token and not self.login():
            return None

        base = self.base_url.rstrip("/")
        path = f"/plugins/telemetry/DEVICE/{id}/values/timeseries"
        url = f"{base}{path}"

        if keys:
            url = f"{url}?{urlencode({'keys': ','.join(keys)})}"

        headers = {"X-Authorization": f"Bearer {self._token}"}

        try:
            resp = requests.get(url, headers=headers, timeout=TIMEOUT)
            if resp.status_code == 401 and self.login():      # token expired
                headers["X-Authorization"] = f"Bearer {self._token}"
                resp = requests.get(url, headers=headers, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError):
            return None


    # ──────────────────────── latest changed time-series values ───────────────────
    def get_changed_values(self, readings) -> list[Any]:
        """ Filter *readings* to only those that have changed since the last push."""
        latest_raw: dict[str, Any] = self.get_latest_values() or {}

        def _latest_for(sensor_key: str) -> Any | None:
            """Return the previously stored value for *sensor_key*, if any."""
            raw = latest_raw.get(sensor_key)
            if raw is None:
                return None
                # SDKs vary: might be list[dict] or a single dict
            if isinstance(raw, list):
                return raw[0].get("value") if raw else None
            if isinstance(raw, dict):
                return raw.get("value")
            return None

        filtered: list[Any] = []
        for entry in readings:
                # Attempt to find the sensor name and its value.
            sensor_name: str | None = None
            value: Any | None = None

            if isinstance(entry, dict):
                    # Common structure → { "name": "Air Temperature", "value": 27.7 }
                if "value" in entry:
                    sensor_name = (
                            entry.get("name")
                            or entry.get("sensor")
                            or entry.get("key")
                            or entry.get("id")
                        )
                    value = entry["value"]
                else:
                        # Fallback: { "Air Temperature": 27.7 } – first key is name.
                    if entry:
                        sensor_name = next(iter(entry))
                        value = entry[sensor_name]
            elif isinstance(entry, (list, tuple)) and len(entry) == 2:
                    # E.g. ("Air Temperature", 27.7)
                sensor_name, value = entry  # type: ignore[misc]
            else:
                    # Unknown structure → keep it to be safe
                filtered.append(entry)
                continue

                # If we couldn’t determine the field names, keep the reading.
            if sensor_name is None:
                filtered.append(entry)
                continue

                # Compare against the last stored value; include only if different.
            if str(_latest_for(sensor_name)) != str(value):
                filtered.append(entry)

        readings = filtered
        return readings


    # ─────────────────────────── Telemetry push ────────────────────────────
    def send_telemetry(
        self,
        readings: List[Dict[str, str | float]],
        *,
        timestamp: Optional[int] = None,
    ) -> bool:
        """
        Push *readings* to IoT-Hub via the **device-token** endpoint.

        Parameters
        ----------
        readings : list of dicts
            Expected shape::
                {
                  "name":        <sensor name>,
                  "value":       <numeric or string>,
                  ...            (other keys are ignored)
                }
        timestamp : int | None
            Milliseconds since epoch.  If *None* → server uses “now”.

        Returns ``True`` on HTTP 200, else ``False``.
        """
        device_token = os.getenv("IOTHUB_DEVICE_TOKEN")
        if not device_token:
            raise RuntimeError("IOTHUB_DEVICE_TOKEN missing")

        base = self.base_url.rstrip("/")  # e.g. https://…/api
        url = f"{base}/v1/{device_token}/telemetry"

        # build payload
        values = {item["name"]: item["value"] for item in readings}
        payload = (
            values
            if timestamp is None
            else [{"ts": int(timestamp), "values": values}]
        )

        try:
            resp = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=TIMEOUT,
            )
            return resp.status_code == 200
        except requests.RequestException:
            return False


    def readings_json_to_list(self, readings: dict) -> list[dict]:
        """
        Convert IoT-Hub readings JSON to a flattened list.

        Parameters
        ----------
        readings : dict
            JSON mapping as returned by ``get_latest_values()``.

        Returns
        -------
        list of lists
            Flattened list of values.
        """
        result = []
        for key, values in readings.items():
            value = values[0]["value"]
            # if value is a number string, convert to float
            try:
                value = float(value)
            except (ValueError, TypeError):
                pass
            result.append({"name": key, "value": value, "timestamp": values[0]["ts"]})
        return result
