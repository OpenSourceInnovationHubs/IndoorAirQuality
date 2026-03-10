""" Orion Client Module
This module provides a client to interact with the Orion-LD Context Broker."""
import logging
import os
from typing import Any, Mapping

import requests

logger = logging.getLogger(__name__)


class OrionClient:
    """Simple wrapper around the Orion-LD REST API."""

    def __init__(self) -> None:
        self.base_url = os.getenv("ORION_BASE_URL", "http://localhost:1026")
        self.timeout: int = 5
        self.headers = {
            "Content-Type": "application/ld+json",
            "Accept": "application/ld+json",
        }
        logger.info("Orion-LD Context Broker URL: %s", self.base_url)


    def check_connection(self) -> bool:
        """Return ``True`` when the broker answers ``/version`` within the timeout."""
        try:
            response = requests.get(f"{self.base_url}/version", timeout=self.timeout)
            return response.status_code == 200
        except requests.RequestException as e:
            logger.warning("Orion connection error: %s", e)
            return False


    def create_entity(self, entity_id: str, entity: Mapping[str, Any]) -> dict | None:
        """Create an entity and return the freshly stored representation on success."""

        url = f"{self.base_url}/ngsi-ld/v1/entities/"

        response = requests.post(url, json=entity, headers=self.headers, timeout=self.timeout)
        if response.status_code != 201:
            logger.error("Failed to create entity %s: %s - %s",
                         entity_id, response.status_code, response.text)
            return None
        return self.get_entity(entity_id)


    def get_entity(self, entity_id: str) -> dict | None:
        """Return the JSON representation of an entity or ``None`` when missing."""
        url = f"{self.base_url}/ngsi-ld/v1/entities/{entity_id}"
        response = requests.get(url, timeout=self.timeout, headers=self.headers)
        if response.status_code == 200:
            return response.json()

        return None


    def delete_entity(self, entity_id: str) -> bool:
        """Delete the entity and return ``True`` if Orion confirms the removal."""
        url = f"{self.base_url}/ngsi-ld/v1/entities/{entity_id}"
        response = requests.delete(url, timeout=self.timeout, headers=self.headers)
        if response.status_code == 204:
            return True
        return False


    def update_entity(self, entity_id: str, entity: Mapping[str, Any]) -> bool:
        """Patch mutable attributes of an existing entity, ignoring read-only fields."""

        url = f"{self.base_url}/ngsi-ld/v1/entities/{entity_id}/attrs"

        payload = entity.copy()
        # remove the readonly fields when existing
        if 'id' in payload:
            del payload['id']
        if 'type' in payload:
            del payload['type']

        response = requests.post(url, json=payload, headers=self.headers, timeout=self.timeout)
        if response.status_code != 204:
            logger.error("Failed to update entity %s: %s - %s",
                         entity_id, response.status_code, response.text)
            return False
        return True
