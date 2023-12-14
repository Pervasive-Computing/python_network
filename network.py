import argparse
import math
import os
import re
import sys
import time
import cartopy.crs as ccrs
import cbor2
import matplotlib.pyplot as plt
import networkx as nx
import simpy
import zmq
import datetime
from pathlib import Path
from datetime import time as t
from cartopy.io.img_tiles import OSM
from controller import lightController
from loguru import logger
import tomllib


from street_lamp_extractor import extract_street_lamps

sendMsgCount = 0
receiveMsgCount = 0

try:
    from rich import pretty, print
    pretty.install()
except ImportError or ModuleNotFoundError:
    pass

"""
TODO:
- Radius neighbor search    (high priority) Done
- Neighbor interaction      (high priority) Done
- Basic functionality (e.g., turn on/off, check status, receive messages, adjust brightness, etc.)
- Assume energy levels 
- Real-time delay
- Simulate a protocol (potentially)
- Plot + results 
- Dead lampposts???
"""

class Streetlight:
    def __init__(self, env, name, lat, lon):
        self.env = env
        self.name = name
        self.lat = lat
        self.lon = lon
        self.neighbors = []  # List to hold neighboring streetlights
        self.received_event = False
        self.controller = lightController()
        self.last_change = 0
        self.change_state = False
        self.level = 0.0
        

    def run(self):
        while True:
            if self.received_event:
                self.get_event()
                self.received_event = False
                self.env.timeout(1)



    def send_message(self, event):
        # global sendMsgCount
        for neighbor in self.neighbors:
            # sendMsgCount += 1
            neighbor.receive_message(event)
         

    def receive_message(self, event):
        global receiveMsgCount
        receiveMsgCount += 1
       
        self.handle_event(event)


    def get_event(self, event):
        #If there is movement, notify neighbours
        if event["sensor_input"]:
            self.send_message(event)
        
        #Handle the event
        self.handle_event(event)



    def handle_event(self, event):
        """
        event = {
                        "date": datetime.datetime(2023, 11, 3, 1, 20), 
                        "sunset_time": t(19, 30),
                        "sunrise_time": t(6, 30),
                        "lux_number": 245.5, 
                        "sensor_input": True, 
                        "season": "Summer" }
        """
        event['current_level'] = self.level
        level, time_change = self.controller.control(event, self.last_change)
        self.last_change = time_change
        self.level = level


    def get_level(self):
        return self.level
        


    def check_neighbors(self):
        # Example function to simulate interaction with neighbors
        for neighbor in self.neighbors:
            print(f"{self.env.now}: {self.name} checks in with {neighbor.name}")

    def add_neighbor(self, neighbor):
        self.neighbors.append(neighbor)
                              
                              
def plot_street_lamps_map(street_lamps):
    # Create an OpenStreetMap instance
    osm_tiles = OSM()

    # Create a new figure and set up the projection
    fig, ax = plt.subplots(subplot_kw={'projection': osm_tiles.crs}, figsize=(8, 8))

    # Set map extent to focus on Denmark
    ax.set_extent([10.1772, 10.2064, 56.1659, 56.1844])

    # Add OpenStreetMap tiles at a zoom level of 8
    ax.add_image(osm_tiles, 16)
    for lamp in street_lamps:
        lat, lon = lamp
        ax.plot(lon, lat, marker='o', color='red', markersize=5, alpha=0.7, transform=ccrs.PlateCarree())
        # Draw a circle for the communication range
        circle = plt.Circle((lon, lat), (COMMUNICATION_RANGE)*1000/111139, color='blue', alpha=0.3, transform=ccrs.PlateCarree())
        ax.add_artist(circle)
    
    
    
# Function to calculate distance between two points
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Radius of the Earth in km
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = math.sin(dLat/2) * math.sin(dLat/2) + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon/2) * math.sin(dLon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance = R * c
    return distance

# Define communication range in kilometers
COMMUNICATION_RANGE = 0.05  # for example, 50 = 0.05 meters

# Function to find connected lamps
def find_connected_lamps(streetlights, G):
    for i, streetlight1 in enumerate(streetlights):
        for j, streetlight2 in enumerate(streetlights):
            if i != j:
                distance = calculate_distance(streetlight1.lat, streetlight1.lon, streetlight2.lat, streetlight2.lon)
                if distance <= COMMUNICATION_RANGE:
                    # Use the names of the streetlights to create edges
                    G.add_edge(streetlight1.name, streetlight2.name)
                    streetlight1.add_neighbor(streetlight2)



def main(argc: int, argv: list[str]):

    # ZeroMQ client connect
    context = zmq.Context()
    publisher  = context.socket(zmq.PUB)
    subscriber = context.socket(zmq.SUB)

    # else:
    configuration_path = Path("config.toml")
    if not configuration_path.exists():
        print(f"Cannot find `{configuration_path}`!")
        return 1
    with open(configuration_path, "rb") as file:
        try:
            configuration = tomllib.load(file)
            
        except tomllib.TOMLDecodeError as e:
            print(f"Cannot decode `{configuration_path}`: {e}", file=sys.stderr)
            return 1


    
    pub_port = configuration["publisher"]["port"]
    publisher.bind(f"tcp://*:{pub_port}")
    pub_top = "light_level"


    sub_port = configuration["subscriber"]["port"]
    
    print("Sub port = ", sub_port, " and pub port = ", pub_port)
    subscriber.connect(f"tcp://localhost:{12000}")
    subscriber.setsockopt(zmq.SUBSCRIBE, b"streetlamps")


    print("Connected!")
    

    osm_file = "Maps/map.osm"
    street_lamps = extract_street_lamps(osm_file)  # Assuming this function is defined elsewhere
    

    # Create the SimPy environment
    env = simpy.Environment()
    print(env.now)
    # print(env.datetime)
    
    
    # Create streetlight nodes (selecting a subset, e.g., first 50 street lamps)
    subset_size = 25  # Adjust this number as needed
    streetlights = [Streetlight(env, int(ids), lat, lon) for i, (ids, lat, lon) in enumerate(street_lamps)]
    # print("Streetlights = ", streetlights)
    # Create a network graph
    G = nx.Graph()
    
    
    # Add nodes and edges to the graph
    for i, streetlight in enumerate(streetlights):
        G.add_node(streetlight.name, pos=(streetlight.lat, streetlight.lon))

    
    # Find connected lamps
    find_connected_lamps(streetlights, G)

    
    # After creating the graph G
    pos = nx.get_node_attributes(G, 'pos')

    print("Starting simulation...")
    n_messages_received: int = 0
    try:
        while True:
            message = subscriber.recv() #We only recieve messages that observed movement
            # message = {'streetlamps': [11046617406, 2, 3]}
            # data = message['streetlamps']
            # print("Message = ", message)
        
            n_messages_received += 1
            data = cbor2.loads(message[len("streetlamps"):])
            # print(f"Received message #{n_messages_received}: {data}")
            logger.info(f"Received message #{n_messages_received}: {data}")
            # data is a list of names of streetlights 
            changes = dict()
            for streetlight in streetlights:
                # print("HERE:", streetlight.name)
                event = {
                        "date": datetime.datetime(2023, 11, 3, 1, 20), 
                        "sunset_time": t(19, 30),
                        "sunrise_time": t(6, 30),
                        "lux_number": 245.5, 
                        "season": "Summer" }
                if streetlight.name in data:
                    event["sensor_input"] = True
                else:
                    event["sensor_input"] = False
                
                streetlight.get_event(event)

                changes[streetlight.name] = streetlight.get_level()
            
            print('changes = ', changes)
            data = cbor2.dumps(changes)
            publisher.send(bytes(pub_top, encoding='utf-8') + data)


    except KeyboardInterrupt:
        print("Interrupted!")
    finally:
        subscriber.close()

        context.term()

    
    # Draw the network
    pos = nx.get_node_attributes(G, 'pos')
    nx.draw(G, pos, with_labels=True, node_color='lightblue', edge_color='gray')
    plt.title("Street Lamp Network (Subset)")

    plot_street_lamps_map(street_lamps[:subset_size])

    plt.show()

    global sendMsgCount
    global receiveMsgCount

    print(sendMsgCount, receiveMsgCount)

if __name__ == "__main__":
    sys.exit(main(len(sys.argv), sys.argv))
