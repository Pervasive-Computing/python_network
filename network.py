import argparse
import math
import os
import sys
import time

import cartopy.crs as ccrs
import cbor2
import matplotlib.pyplot as plt
import networkx as nx
import simpy
import zmq
from cartopy.io.img_tiles import OSM

from street_lamp_extractor import extract_street_lamps

msgCount = 0

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
        self.action = env.process(self.run())
        

    def run(self):
        while True:
            if self.received_event:
                self.get_event()
                print(self.name)
                self.received_event = False
                self.env.timeout(1)

    def send_message(self):
        global msgCount
        for neighbor in self.neighbors:
            msgCount += 1
            neighbor.receive_message(self.name)

    def receive_message(self, message):
        #print(f"{self.env.now}: {self.name} received message: {message}")
        self.send_event(message)


    def get_event(self):
        self.send_message()

    def send_event(self, event):
        print("There is event")

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



def main(argc: int, argv: list[str]) -> int:

    # ZeroMQ client connect
    argv_parser = argparse.ArgumentParser(prog=os.path.basename(__file__).removesuffix(".py"),
                                         description="ZeroMQ client demo")
    argv_parser.add_argument("-p", "--port", type=int, default=5555, help="Port number")

    args = argv_parser.parse_args(argv[1:])

    context = zmq.Context()

    print(f"Connecting to server on port {args.port}...")
    subscriber = context.socket(zmq.SUB)
    subscriber.connect(f"tcp://localhost:{args.port}")
    subscriber.setsockopt(zmq.SUBSCRIBE, b"streetlamps")
    print("Connected!")

    osm_file = "Maps/map.osm"
    street_lamps = extract_street_lamps(osm_file)  # Assuming this function is defined elsewhere

    # Create the SimPy environment
    env = simpy.Environment()

    # Create streetlight nodes (selecting a subset, e.g., first 50 street lamps)
    subset_size = 25  # Adjust this number as needed
    streetlights = [Streetlight(env, ids, lat, lon) for i, (ids, lat, lon) in enumerate(street_lamps)]

    # Create a network graph
    G = nx.Graph()

    # Add nodes and edges to the graph
    for i, streetlight in enumerate(streetlights):
        G.add_node(streetlight.name, pos=(streetlight.lat, streetlight.lon))

    # Find connected lamps
    find_connected_lamps(streetlights, G)

    # After creating the graph G
    pos = nx.get_node_attributes(G, 'pos')

    n_messages_received: int = 0
    try:
        while True:
            message = subscriber.recv()
            n_messages_received += 1
            data = cbor2.loads(message[len("streetlamps"):])
            #data is a list of names of streetlights
            for streetlight in streetlights:
                if streetlight.name in data:
                    streetlight.received_event = True
                env.run(until=env.now + 1)

            #print(f"Received message #{n_messages_received}: {data}")
            # time.sleep(0.1)
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


if __name__ == "__main__":
    sys.exit(main(len(sys.argv), sys.argv))
