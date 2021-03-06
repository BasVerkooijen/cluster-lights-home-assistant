# Cluster Lights component for Home Assistant
This custom component and driver for Home Assistant implements support for Cluster Lights as sold by Action and some [other stores](https://www.kabelshop.nl/PerfectLED-Clusterverlichting-met-app-7-meter-Bluetooth-576-LEDs-Binnen-Buiten-AX8718700-i7551-t101352.html). The Cluster Lights are supported by the [Lights App](https://play.google.com/store/apps/details?id=com.scinan.novolink.lightstring).

![](screenshot.jpg?raw=true)

## What is working
* Cluster Lights are represented as Light entity in home assistant
* Cluster Lights support brightness (dimming) and effects (patterns)

## Limitations
Only support for Warm White variant currently.

# Requirements for Home Assistant instance
* Bluetooth adapter supporting Bluetooth Low-Energy (BLE)
* Cluster Lights must be in range of Home Assistant instance (due to bluetooth adapter range)

# Python dependencies
* bluepy
* voluptuous

`sudo pip3 install bluepy voluptuous`

# Adding the component to Home Assistant
1. Checkout repository

   `git clone https://github.com/BasVerkooijen/cluster-lights-home-assistant.git`

2. Copy the folder `clusterlights` to your `custom_components` folder in Home Assistant installation directory

   *❓: Create the `custom_components` folder in your Home Assistant configuration directory if you don't have custom components yet:*
   
   *`mkdir <path to your config dir>/custom_components`*

   `cp -r <path to git repo>/clusterlights <path to your config dir>/custom_components`
3. Add a configuration for your cluster lights to `configuration.yaml`

   ```
   # configuration.yaml
   light:
     - platform: clusterlights
       devices:
         "AA:BB:CC:DD:EE:FF":
           name: Christmas Tree
   ```
   * **devices**
     
     (list)(Required)
     
     The list of cluster lights devices.
     
     * **mac_address**
        
        (list)(Required)
        
        The MAC address of the cluster lights.
     
       * **name**
        
          (string)(Optional)
        
          A name for the entity to create in the front-end.

4. Restart Home Assistant instance

   Example for Python virtual env installation:
   
   `sudo systemctl restart home-assistant@homeassistant`

5. The `clusterlights` integration will create a light entity with the provided name. You can add this entity to your lovelace dashboard with the _light card_.
   
   **⚠️: When no entity is created, the integration failed to initialize the cluster lights. You can inspect the Home Assistant log to see what is going wrong.** 
