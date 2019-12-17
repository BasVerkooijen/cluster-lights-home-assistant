# Action Cluster Lights component for Home Assistant
This custom component and driver for Home Assistant implements support for Cluster Lights as sold by [Action](https://www.action.com/nl-nl/p/clusterverlichting/) and some other stores.

![](screenshot.jpg?raw=true)

## What is working
* Cluster Lights are represented as Light entity in home assistant
* Cluster Lights support dimming and effects (patterns)

## Limitations
Only support for Warm White variant currently

# Requirements for Home Assistant instance
* Bluetooth adapter supporting Bluetooth Low-Energy (BLE) is required
* Cluster Lights must be in range of Home Assistant instance (Bluetooth adapter range)

# Python dependencies
* bluepy
* voluptuous

`sudo pip3 install bluepy voluptuous`

# Adding the component to Home Assistant
1. Checkout repository

   `git clone https://github.com/BasVerkooijen/cluster-lights-home-assistant.git`

2. Copy the folder 'clusterlights' to your 'custom_components' folder in Home Assistant installation directory

   *Optional: Create the 'custom_components' folder in your Home Assistant installation directory if you don't have custom components yet:*
   
   `mkdir <path to your install dir>/custom_components`

   `cp -r <path to git repo>/clusterlights <path to your install dir>/custom_components`
3. Add a configuration for your cluster lights to configuration.yaml

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
