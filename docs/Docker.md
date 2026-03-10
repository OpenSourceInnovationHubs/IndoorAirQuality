# Setup & Run on (local) Docker

### 1. Start Docker containers:
```shell
docker compose up -d
```

### 2. Optional: To develop/debug the NGSI-Proxy:
- Stop the container "ngsi_proxy"
- Run the python script directly
    ```shell
    cd ngsi-proxy
    python ngsi-proxy/app.py
    ```

### 3. Entry points

- Grafana Frontend: [http://localhost:3000](http://localhost:3000).  
    The defaul login is *admin/admin* (You are asked to change the pwd on first login)

- CreateDB Admin UI: [http://localhost:4200](http://localhost:4200)  
    Login: crate (without password)


### 4. Optional: Setting up Grafana
- Generate Dashboards:  
    The list of sensors is based on [Sensor.csv](Sensors.csv)

    ```shell
    python grafana/generate_dashboards.py
    ```

    The dashboards will be generated based on the [grafana/template.json](grafana/template.json) and the files will be stored in [grafana/out/](grafana/out/).  

    Hint: To update the [grafana/template.json](grafana/template.json) you may just modify your A5.18 dashboard and export it from Grafana into that file.

- Copy the dashboards of interest to the [grafana/dashboards](grafana/dashboards/)
    
    Remarks: The dashboards in [grafana/dashboards](grafana/dashboards/) will then be imported automatically during grafana is running.

- if "CrateDB" does not exist  
    Add a new PostgreSQL data source:
    - Name: CrateDB
    - Host: crate-db:5432 (Important: Do not put localhost)
    - Database: doc
    - User: crate
    - Password: leave it empty
    - SSL mode: disable
