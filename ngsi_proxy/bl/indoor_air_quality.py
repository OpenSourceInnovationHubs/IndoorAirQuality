"""Domain logic for IndoorAirQuality job processing."""
import logging

from services.ngsild_builder import NgsiLdBuilder
from services.iothub_service import MagentaIoTClient


logger = logging.getLogger(__name__)


# Mapping:  sensor name  →  (Entity type, attribute name)
INDOORAIRQUALITY_MAP = {
    # IndoorEnvironmentObserved: see https://raw.githubusercontent.com/smart-data-models/dataModel.Environment/refs/heads/master/IndoorEnvironmentObserved/schema.json
    "Temperature_avg": ("IndoorEnvironmentObserved", "temperature"),
    "Humidity_avg": ("IndoorEnvironmentObserved", "relativeHumidity"),
    "CO2_avg": ("IndoorEnvironmentObserved", "co2"),
    "Pressure_avg": ("IndoorEnvironmentObserved", "atmosphericPressure"),
}

# Common @context list (NGSI-LD core + aggregated Smart-Data-Models)
INDOORAIRQUALITY_CONTEXT = [
    "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld",
    "https://smartdatamodels.org/context.jsonld"
]


class IndoorAirQualityJob:
    """Job to process IndoorAirQuality sensor data from Magenta IoT-Hub."""
    def __init__(self) -> None:
        self.iot_client = MagentaIoTClient()

        self.last_observed_at = None
        self.pois = dict()


    def setPOIs(self, pois: list[dict]) -> None:
        """Set PointOfInterest entities for reference linking."""
        if not pois:
            return
        self.pois = {poi["id"]: poi for poi in pois}


    def prepare(self) -> bool:
        """Ensure sensor list available – recreate session once if necessary"""
        if not self.iot_client.devices:
            self.iot_client.get_devices()
        if not self.iot_client.devices:
            logger.warning("IndoorAirQuality sensor list unavailable")
            return False
        return True


    def process_data(self, isfirstupdate: bool) -> list[dict] | None:
        """Fetch current/next readings from Magenta IoT-Hub"""
        if not self.iot_client.devices:
            return None

        all_entities = []
        for name, id in self.iot_client.devices["IndoorAirQuality"].items():
            # Fetch latest readings for this device out of Magenta IoT-Hub
            readings = self.iot_client.get_latest_values(name=name)
            if readings:
                readings_list = self.iot_client.readings_json_to_list(readings)

            if not readings_list or not isinstance(readings_list, list) or len(readings_list) < 1:
                logger.warning(
                    "No IndoorAirQuality readings for device %s (last observed at %s)",
                    name,
                    self.last_observed_at,
                )
                continue

            # Convert readings to NGSI-LD entities
            entities = NgsiLdBuilder.build_entities(INDOORAIRQUALITY_MAP, INDOORAIRQUALITY_CONTEXT, readings_list, name)

            # Add NGSI-LD references to the Room/PointOfInterest
            if entities and len(entities) > 0:
                poi_id = f"urn:ngsi-ld:PointOfInterest:{name}"
                entities[0].update({
                    "refPointOfInterest": {
                        "type": "Relationship",
                        "object": poi_id
                    },
                })
                pois_entity = self.pois.get(poi_id) if self.pois else None
                if pois_entity:
                    entities[0].update({
                        "location": pois_entity.get("location"),
                    })

            all_entities.extend(entities)

        return all_entities
