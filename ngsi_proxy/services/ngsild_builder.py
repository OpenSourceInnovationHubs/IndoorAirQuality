"""Utilities for turning OTT Hydromet readings into NGSI-LD payloads."""

from datetime import datetime, timezone
import json
import logging
import re
from typing import Any, Mapping, Sequence


logger = logging.getLogger(__name__)


class NgsiLdBuilder:
    """Helper for assembling NGSI-LD compatible entities from sensor values."""

    @staticmethod
    def _slug(text: str) -> str:
        """Return a safe fragment to append to the URN (letters & digits only)."""
        return re.sub(r"[^\w]", "", text)

    @staticmethod
    def build_entity(
        MAP: Mapping[str, tuple[str, str]],
        CONTEXT: Sequence[str],
        name: str,
        value: Any,
        station_id: str,
        observed_at: str | None = None,
    ) -> dict[str, Any]:
        """Return a single NGSI-LD entity representing one sensor reading."""
        if name not in MAP:
            raise ValueError(f"Sensor name '{name}' is unknown to the mapping table")

        entity_type, attr = MAP[name]
        observed_at = observed_at or datetime.now(timezone.utc).isoformat()

        return {
            "id": f"urn:ngsi-ld:{entity_type}:{station_id}",
            "type": entity_type,
            "dateObserved": observed_at,
            attr: {
                "type": "Property",
                "value": value,
                "observedAt": observed_at
            },
            "@context": CONTEXT
        }

    @staticmethod
    def build_entities(
        MAP: Mapping[str, tuple[str, str]],
        CONTEXT: Sequence[str],
        sensor_list: Sequence[Mapping[str, Any]],
        station_id: str,
    ) -> list[dict[str, Any]]:
        """Convert many sensor values into their grouped NGSI-LD representations."""
        entities: dict[str, list[dict[str, Any]]] = {}
        entity_types: dict[str, str] = {}
        for item in sensor_list:
            name = item["name"]

            # Convert one reading into an NGSI-LD entity
            if name in MAP:
                entity_type, attr = MAP[name]
                entity_id = f"urn:ngsi-ld:{entity_type}:{station_id}"
                if entity_id not in entities:
                    entities[entity_id] = []
                    entity_types[entity_id] = entity_type

                # NGSI-LD expects ISO 8601 with timezone; assume UTC if date provided
                ts = item.get("timestamp")
                observed_at = DateTimeConverter(ts).isoformat()

                entities[entity_id].append(
                    {
                        attr: {
                            "type": "Property",
                            "value": item["value"],
                            "observedAt": observed_at,
                        },
                    }
                )
                continue

            #print(f"DEBUG: '{name}' is unknown to the mapping table - skipping.")

        # Convert the dict of entities into a list of NGSI-LD entities
        payload: list[dict[str, Any]] = []
        for entity_id, attributes in entities.items():
            # Merge all attributes into a single entity
            entity = {
                "id": entity_id,
                "type": entity_types[entity_id],
                "dateObserved": observed_at
            }
            for attr in attributes:
                entity.update(attr)
            entity.update({"@context": CONTEXT})
            payload.append(entity)

        return payload




class DateTimeConverter:
    """Utility class for converting date-time strings."""

    def __init__(self, ts):
        self.datetime = datetime.now(tz=timezone.utc)

        if ts:
            if isinstance(ts, str):
                self.datetime = self.from_iso8601(ts)
            elif isinstance(ts, datetime):
                self.datetime = ts
            elif isinstance(ts, int):
                self.datetime = self.from_unix_epoch_ms(ts)


    def isoformat(self) -> str:
        """Return the datetime as an ISO 8601 string with timezone.

        Returns:
            str: The date-time string in ISO 8601 format with timezone.
        """
        return self.datetime.isoformat()


    @staticmethod
    def from_iso8601(dt_string: str) -> datetime:
        """Convert various date-time string formats to ISO 8601 with timezone.

        Args:
            dt_string (str): The date-time string to convert.

        Returns:
            str: The converted date-time string in ISO 8601 format with timezone.
        """

        # Try Python's ISO parser first (handles microseconds + timezone offsets)
        try:
            parsed = datetime.fromisoformat(dt_string)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            pass

        # if dt_string uses YYYY-MM-DDThh:mm:ss, append timezone
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", dt_string):
            return (datetime.strptime(dt_string, "%Y-%m-%dT%H:%M:%S")
                    .replace(tzinfo=timezone.utc))
        # if dt_string uses YYYYMMDDThh:mm:ss, convert briefly
        if re.fullmatch(r"\d{8}T\d{2}:\d{2}:\d{2}", dt_string):
            return (datetime.strptime(dt_string, "%Y%m%dT%H:%M:%S")
                    .replace(tzinfo=timezone.utc))

        raise ValueError(f"Unsupported date-time format: {dt_string}")


    @staticmethod
    def from_unix_epoch_ms(epoch_ms: int) -> datetime:
        """Convert epoch milliseconds to a datetime object with timezone.

        Args:
            epoch_ms (int): The epoch time in milliseconds.

        Returns:
            datetime: The corresponding datetime object with timezone.
        """
        return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc)


    @staticmethod
    def iso_to_epoch_ms(ts_str: str) -> int | None:
        """Convert either “YYYYMMDDTHH:MM:SS” or “YYYY‑MM‑DDTHH:MM:SS” → epoch‑ms UTC."""
        for fmt in ("%Y%m%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
            try:
                return int(
                    datetime.strptime(ts_str, fmt)
                    .replace(tzinfo=timezone.utc)
                    .timestamp()
                    * 1000
                )
            except ValueError:
                continue
        return None


    @staticmethod
    def ms_to_iso(ms: int) -> str:
        """Convert epoch‑ms → ISO‑8601 “YYYY‑MM‑DDTHH:MM:SSZ”."""
        return datetime.utcfromtimestamp(ms / 1000).strftime("%Y-%m-%dT%H:%M:%SZ")


# ------------ HOW TO USE ------------------------------------------------------
if __name__ == "__main__":
    MAP = {
        # WeatherObserved: see https://raw.githubusercontent.com/smart-data-models/dataModel.Weather/master/WeatherObserved/schema.json
        "Air Density": ("WeatherObserved", "airDensity"),
        "Air Temperature": ("WeatherObserved", "temperature"),
        "Rel. Humidity (act.)": ("WeatherObserved", "relativeHumidity"),
    }

    CONTEXT = [
        "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld",
        "https://smartdatamodels.org/context.jsonld"
    ]


    # Example #1: single sensor reading
    e = NgsiLdBuilder.build_entity(MAP, CONTEXT, "Air Temperature", 23.98, "farmWeatherStation001")
    logger.info(json.dumps(e, indent=2))

    # Example #2: JSON file as input (like SensorsWithValues.json)
    import pathlib
    main_data = json.loads(pathlib.Path("docs/DataModel/SensorsWithValues.json")
                           .read_text(encoding="utf-8"))
    main_entities = NgsiLdBuilder.build_entities(MAP, CONTEXT, main_data, station_id="WeatherStation")
    logger.info(json.dumps(main_entities, indent=2))
    # write to file
    pathlib.Path("docs/DataModel/SensorsWithValues.ngsi-ld.json").write_text(
        json.dumps(main_entities, indent=2),
        encoding="utf-8"
    )
