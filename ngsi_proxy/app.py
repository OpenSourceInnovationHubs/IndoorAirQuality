#!/usr/bin/env python3
"""Scheduler for periodic data fetching and pushing to IoT-Hub and FIWARE infrastructure."""
import logging
import os
import threading
import time
import datetime as dt

from flask import Flask, jsonify

from bl.indoor_air_quality import IndoorAirQualityJob
from bl.pointofinterest import PointOfInterestJob

from services.orion_service import OrionClient
from services.quantumleap_service import QuantumLeapClient
from logging_config import configure_logging

logger = logging.getLogger(__name__)


class SchedulerState:
    """Thread-safe Shared state for the scheduler thread."""
    lock = threading.Lock()
    running : bool = False
    last_update : str | None = None
    update_count : int = 0


class Scheduler:
    """
    Scheduler thread for periodic data fetching and 
    pushing to IoT-Hub and FIWARE infrastructure.
    """
    def __init__(self):
        self.interval_seconds = int(os.getenv("INTERVAL_SECONDS", "60"))
        self.thread = threading.Thread(target=self._run_loop, daemon=True)

        self.jobPOI = PointOfInterestJob()
        self.jobAir = IndoorAirQualityJob()
        self.orion = OrionClient()
        self.quantumleap = QuantumLeapClient()

        logger.info("Scheduler initialized with interval %s seconds", self.interval_seconds)


    def start(self) -> None:
        """Start the scheduler in a background thread."""
        logger.info("Scheduler running every %s seconds", self.interval_seconds)
        self.thread.start()


    def run_forever(self) -> None:
        """Run the scheduler loop in the current thread (blocking)."""
        logger.info("Scheduler running every %s seconds", self.interval_seconds)
        self._run_loop()


    def _run_loop(self) -> None:
        """Main loop for the scheduler, fetching data and pushing it to IoT-Hub and Orion-LD."""
        logger.info("Scheduler loop started")
        with SchedulerState.lock:
            SchedulerState.running = True
            SchedulerState.last_update = None
            SchedulerState.update_count = 0
        try:
            self.jobPOI.prepare()
            pois = self.jobPOI.process_data(isfirstupdate=True)
            if pois:
                self._send_to_orion(pois)
                self.jobAir.setPOIs(pois)

            while True:
                time.sleep(self.interval_seconds)
                try:
                    logger.debug("Scheduler triggered")
                    with SchedulerState.lock:
                        isfirstupdate = (SchedulerState.update_count % self.interval_seconds) == 0

                    # Execute jobs
                    if not self.jobAir.prepare():
                        continue

                    entities = self.jobAir.process_data(isfirstupdate)
                    if not entities:
                        continue

                    self._send_to_orion(entities)

                    # Update the last update timestamp in a thread-safe way
                    current_ts = dt.datetime.now(dt.timezone.utc)
                    with SchedulerState.lock:
                        SchedulerState.update_count += 1
                        SchedulerState.last_update = current_ts.isoformat()
                        logger.info("Last update timestamp: %s", SchedulerState.last_update)

                except RuntimeError:
                    logger.exception("Runtime error in scheduler")
                except ValueError as exc:
                    logger.error("Value error in scheduler: %s", exc)
        finally:
            with SchedulerState.lock:
                SchedulerState.running = False
            logger.warning("Scheduler finished")



    def _send_to_orion(self, entities: list[dict]) -> bool:
        """Send the entities to Orion-LD"""
        try:
            for entity in entities:
                entity_id = entity.get("id")
                if not entity_id:
                    logger.warning("Entity ID is missing in the entity, skipping")
                    continue

                # Ensure that there is a subscription for QuantumLeap
                ql_client = self.quantumleap
                subscription_id = ql_client.get_subscription_id_from_entity_id(entity_id)
                if not ql_client.get_subscription(subscription_id):
                    ql_client.create_subscription(subscription_id, entity)

                # Create or update the entity in Orion-LD
                orion_client = self.orion
                if not orion_client.get_entity(entity_id):
                    orion_client.create_entity(entity_id, entity)
                    logger.info("Created entity %s", entity_id)
                else:
                    orion_client.update_entity(entity_id, entity)
                    logger.info("Updated entity %s", entity_id)

            logger.info("Successfully pushed %s NGSI-LD entities to Orion-LD", len(entities))
            return True
        except Exception as exc:
            logger.exception("Failed to push entities to Orion-LD: %s", exc)
            return False


# ---------- Flask app for health check ---------
app = Flask(__name__)
app_port = os.getenv('NGSI_PROXY_APP_PORT', '3001')

@app.route('/health', methods=['GET'])
def health_check():
    """ Health check endpoint. """
    return jsonify(status="healthy"), 200



if __name__ == "__main__":
    configure_logging()

    Scheduler().start() # Start scheduler in background thread

    # Start the Flask web server (Attention: This is blocking)
    app.run(host='0.0.0.0', port=int(app_port))
