"""Domain logic for PointOfInterest job processing."""
import logging

import pandas as pd
logger = logging.getLogger(__name__)

# DataModel PointOfInterest: see https://github.com/smart-data-models/dataModel.PointOfInterest/blob/master/PointOfInterest/schema.json

# Common @context list (NGSI-LD core + aggregated Smart-Data-Models)
POINTOFINTEREST_CONTEXT = [
    "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld",
    "https://smartdatamodels.org/context.jsonld",
    "https://raw.githubusercontent.com/smart-data-models/dataModel.PointOfInterest/master/context.jsonld"
]


class PointOfInterestJob:
    """Job to process PointOfInterest data from POIs.csv file."""
    def __init__(self) -> None:
        self.poi_props = {}


    def prepare(self) -> bool:
        """Load Sensors.csv with the POIs properties (geocoords, address, etc.)"""
        try:
            df = pd.read_csv('Sensors.csv', delimiter=';')
            self.poi_props = df.set_index('name').T.to_dict()
            return True
        except FileNotFoundError:
            logger.warning("File 'Sensors.csv' not found!")
            return False


    def process_data(self, isfirstupdate: bool) -> list[dict] | None:
        """Process the POI data"""
        if not self.poi_props:
            logger.warning("POI properties not loaded!")
            return None

        entities = []
        for name, props in self.poi_props.items():
            # Example processing: add a new field
            lat = float(props['lat'])
            lng = float(props['lng'])
            entity = {
                "id": f"urn:ngsi-ld:PointOfInterest:{name}",
                "type": "PointOfInterest",
                "address": {
                    "type": "Property",
                    "value": {
                    "addressCountry": "AT",
                    "addressRegion": "Vienna",
                    "addressLocality": "Vienna",
                    "district": "Brigittenau",
                    "postOfficeBoxNumber": "A-1200",
                    "postalCode": "1200",
                    "streetAddress": f"{props['streetAddress']}",
                    "streetNr": f"{props['streetNr']}"
                    }
                },
                "description": {
                    "type": "Property",
                    "value": f"{props['description']}"
                },
                "location": {
                    "type": "GeoProperty",
                    "value": {
                        "type": "Point",
                        "coordinates": [ lng, lat ]
                    }
                },
                "name": {
                    "type": "Property",
                    "value": f"{name}"
                },
                "title": {
                    "type": "Property",
                    "value": f"{name} {props['description']}"
                },

                "@context": POINTOFINTEREST_CONTEXT
            }
            entities.append(entity)

        return entities


if __name__ == "__main__":
    # Test the PointOfInterestJob
    poi_job = PointOfInterestJob()
    if poi_job.prepare():
        entities = poi_job.process_data(isfirstupdate=True)
        if entities:
            for entity in entities:
                print("POI entity: %s", entity)
