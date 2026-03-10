# Setup & Run Grafana

## Entry Points

Login: http://localhost:8000/login - default login is admin/admin.  
Remarks: on the first login you are asked to change the password.

## Configuration

- Optional (is already there): Add DataSource: http://localhost:8000/connections/datasources
    - Select: PostgreSQL
    - Name: CrateDB
    - Host: crate-db:5432
    - Database: doc
    - User: crate 
    - No password
    - TLS Mode: disaple

- Import dashboards: http://localhost:8000/dashboard/ from [grafana/out/](./grafana/out/)

- Build a Dashboard: http://localhost:8000/dashboard/new?orgId=1

- Add Gauge Visualization
    - Select DataSource: CrateDB
    - Query Code: 
    ```sql
    SELECT time_index, date_format(time_index), temperature,  FROM etindoorenvironmentobserved WHERE entity_id = 'urn:ngsi-ld:IndoorEnvironmentObserved:A5.18' ORDER BY time_index"

    SELECT time_index, date_format(time_index), temperature_avg, humidity_avg, co2_avg, pressure_avg FROM etsensor WHERE entity_id = 'urn:ngsi-ld:Sensor:A5.18' ORDER BY time_index DESC LIMIT 1
    ```
    - Visualization Type: Gauge
    - Panel Name: A5.18

- Add Timeseries Visualization for Temperature
    - Query Code: 
    ```sql
    SELECT time_index, temperature_avg FROM etsensor WHERE entity_id = 'urn:ngsi-ld:Sensor:A5.18' ORDER BY time_index
    ```
    - Panel Name: A5.18 Temperature

- Add Timeseries Visualization for Humidity
- Add Timeseries Visualization for Pressure
- Add Timeseries Visualization for CO2
