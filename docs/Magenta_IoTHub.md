# Magenta IoT-Hub Business

A (proprietary) IoT-plattform hosted by Magenta.

Magenta Business IoT Hub [Produktinfo](https://www.magenta.at/business/iot/plattformen/iot-hub)

## Entry Points

- Magenta Business IoT Hub Dashboard: https://iothub.magenta.at/home 

-  Authentication [IoTHub_Authenticate.http](../IoTHub_Authenticate.http), save the JWT token as IOTHUB_TOKEN parameter in the [.env](../.env) file

- Retrieve values via the REST-API [IoTHub_IndoorAirQuality_A5.18.http](../IoTHub_IndoorAirQuality_A5.18.http)

## HOWTO Magenta IoT Hub REST-API

- Magenta IoT Hub API & API-docs (Swagger): https://iothub.magenta.at/swagger-ui/  
    Attention: The API may have a rate limit,  
    for the API-statistics see IoT Dashboard / API Statistics: https://iothub.magenta.at/usage


- How to use the REST-API:

    1. Create an [.env](../.env) file and provide IOTHUB_USERNAME and IOTHUB_PASSWORD
    2. Authenticate to geht the JWT token [IoTHub_Authenticate.http](../IoTHub_Authenticate.http)
    3. Execute further requests using the token as Bearer Authorization header


## Tutorials
- Getting Started with IoT Hub: https://docs.iothub.magenta.at/docs/getting-started-guides/helloworld-pe/?connectdevice=mqtt-linux#step-2-connect-device
- Guide to Connect a IoT Device: https://docs.iothub.magenta.at/docs/getting-started-guides/helloworld-pe/?connectdevice=mqtt-windows#step-2-connect-device
- Documentation how to retrieve device/entity values: https://docs.iothub.magenta.at/docs/pe/user-guide/telemetry/


## Further Resources

- Online Epoch UNIX Timestamp converter: https://www.unixtimestamp.com/
