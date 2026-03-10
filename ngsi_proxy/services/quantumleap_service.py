"""Client helper for working with QuantumLeap subscriptions."""

import logging
import os
from typing import Any, Iterable, Mapping

import requests


logger = logging.getLogger(__name__)

class QuantumLeapClient:
    """Service Agent that hides the HTTP plumbing of the QuantumLeap API."""

    def __init__(self) -> None:
        self.orion_base_url = os.getenv("ORION_BASE_URL", "http://localhost:1026")
        self.ql_base_url = os.getenv("QUANTUMLEAP_BASE_URL", "http://localhost:8668")
        self.timeout: int = 5
        self.headers = {
            "Content-Type": "application/ld+json",
            "Accept": "application/ld+json",
        }
        logger.info("QuantumLeap URL: %s", self.ql_base_url)

        self.subscriptions_count: int = 0


    def check_connection(self) -> bool:
        """Return ``True`` when ``/version`` responds with HTTP 200."""
        try:
            response = requests.get(f"{self.ql_base_url}/version", timeout=self.timeout)
            return response.status_code == 200
        except requests.RequestException as e:
            logger.warning("QuantumLeap connection error: %s", e)
            return False


    def get_subscription_id_from_entity_id(self, entity_id: str) -> str:
        """Convert an NGSI-LD entity URN to the matching subscription URN."""
        if not entity_id.startswith("urn:ngsi-ld:"):
            raise ValueError(f"Invalid entity ID format: {entity_id}")
        return entity_id.replace("urn:ngsi-ld:", "urn:ngsi-ld:Subscription:")


    def create_subscription(self, subscription_id: str, entity: Mapping[str, Any]) -> str:
        """Create a subscription in Orion that forwards notifications to QuantumLeap."""
        url = f"{self.orion_base_url}/ngsi-ld/v1/subscriptions/"
        attributes = []
        for key in entity.keys():
            if key in ["id", "type", "@context"]:
                continue
            if key.startswith("https://"):
                key = key.split("/")[-1]
            attributes.append(key)
        entity_id = entity.get("id")
        entity_type = entity.get("type")
        payload = {
            "id": subscription_id,
            "type": "Subscription",
            "description": "Notify QuantumLeap of count changes of any Sensor",
            "entities": [
                {
                    "type": entity_type,
                    "id": entity_id
                }
            ],
            "watchedAttributes": attributes,
            "notification": {
                "attributes": attributes,
                "format": "normalized",
                "endpoint": {
                    "uri": "http://quantumleap:8668/v2/notify",    #TODO: make QL-URL for subscription configurable
                    "accept": "application/ld+json"
                }
            },
            "throttling": 1,
            "@context": [
                "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld",
                "https://smartdatamodels.org/context.jsonld"
            ]
        }
        try:
            response = requests.post(url, json=payload, headers=self.headers, timeout=self.timeout)
            if response.status_code != 201:
                logger.warning(
                    "Failed to create subscription %s: %s - %s",
                    subscription_id,
                    response.status_code,
                    response.text,
                )
                return ""
            self.subscriptions_count += 1
            result = response.headers["Location"].split("/")[-1]
            logger.info(
                "Subscription %s for entity %s created: %s",
                subscription_id,
                entity_id,
                result,
            )
        except requests.RequestException as e:
            logger.warning("Failed to create subscription %s: %s", subscription_id, e)
            return ""
        return result


    def get_subscription(self, subscription_id: str) -> dict[str, Any] | None:
        """Return the subscription JSON or ``None`` if it does not exist."""
        url = f"{self.orion_base_url}/ngsi-ld/v1/subscriptions/{subscription_id}"
        try:
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            if response.status_code == 200:
                return response.json()
            if response.status_code == 404:
                logger.info("Subscription not found: %s", subscription_id)
                return None
            logger.error(
                "Failed to retrieve subscription %s: %s - %s",
                subscription_id,
                response.status_code,
                response.text,
            )
            return None
        except requests.RequestException as e:
            logger.warning("Failed to retrieve subscription %s: %s", subscription_id, e)
            return None


    def delete_subscription(self, subscription_id: str) -> bool:
        """Delete the subscription and return ``True`` if Orion reports success."""
        url = f"{self.orion_base_url}/ngsi-ld/v1/subscriptions/{subscription_id}"
        try:
            response = requests.delete(url, headers=self.headers, timeout=self.timeout)
            if response.status_code == 204:
                logger.info("Subscription deleted: %s", subscription_id)
                return True
        except requests.RequestException as e:
            logger.warning("Failed to delete subscription %s: %s", subscription_id, e)
        return False


    def create_subscriptions(self, entities: Iterable[Mapping[str, Any]]) -> None:
        """Ensure every provided entity has a corresponding QuantumLeap subscription."""
        for entity in entities:
            entity_id = entity.get("id")
            if not entity_id:
                logger.warning("Entity ID is missing in the payload")
                continue
            subscription_id = self.get_subscription_id_from_entity_id(entity_id)
            if not self.get_subscription(subscription_id):
                self.create_subscription(subscription_id, entity)
            else:
                logger.info("Subscription for entity %s already exists", entity_id)


    def get_subscriptions(self) -> list[dict[str, Any]]:
        """Retrieve every subscription currently stored in Orion."""
        url = f"{self.orion_base_url}/ngsi-ld/v1/subscriptions?limit=100"
        try:
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            if response.status_code == 200:
                subscriptions = response.json()
                self.subscriptions_count = len(subscriptions)
                return subscriptions
            else:
                logger.error(
                    "Failed to retrieve subscriptions: %s - %s",
                    response.status_code,
                    response.text,
                )
                return []
        except requests.RequestException as e:
            logger.warning("Failed to retrieve subscriptions: %s", e)
            return []


    def delete_subscriptions(self) -> None:
        """Remove all known subscriptions (best-effort)."""
        subscriptions = self.get_subscriptions()
        for subscription in subscriptions:
            subscription_id = subscription.get("id")
            if subscription_id:
                self.delete_subscription(subscription_id)
            else:
                logger.warning("Subscription ID is missing in the payload")
        self.subscriptions_count = 0


    def get_subscriptions_count(self) -> int:
        """Return how many subscriptions have been detected/created this session."""
        return self.subscriptions_count
