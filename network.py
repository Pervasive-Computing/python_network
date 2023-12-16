import math
import sys
import cartopy.crs as ccrs
import cbor2
import matplotlib.pyplot as plt
import networkx as nx
import simpy
import zmq
import datetime
import csv

from pathlib import Path
from datetime import time as t
from cartopy.io.img_tiles import OSM
from controller import lightController
from calculate_cost import calc_cost
from loguru import logger
import tomllib


from street_lamp_extractor import extract_street_lamps

try:
    from rich import pretty, print
    pretty.install()
except ImportError or ModuleNotFoundError:
    pass


send_msg_count:int = 0
receive_msg_count: int = 0

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
    def __init__(self, env, name, lat, lon, timeout_time=10, recheck_time = 10):
        self.env = env
        self.name = name
        self.lat = lat
        self.lon = lon
        self.neighbors = []  # List to hold neighboring streetlights
        self.received_event = False
        self.controller = lightController(timeout_time, False)
        self.last_change = 0
        self.level = 0.0
        self.recheck_time = recheck_time


    def send_message(self, event):
        
        if(self.last_change < self.recheck_time):
            global send_msg_count
            for neighbor in self.neighbors:
                send_msg_count += 1
                neighbor.receive_message(event)
            

    def receive_message(self, event):
        global receive_msg_count
        receive_msg_count += 1
       
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



def main() -> int:

    # ZeroMQ client connect
    zmq_context = zmq.Context()
    publisher  = zmq_context.socket(zmq.PUB)
    subscriber = zmq_context.socket(zmq.SUB)

    # else:
    configuration_path = Path("config.toml")
    
    if not configuration_path.exists():
        logger.error(f"Cannot find `{configuration_path}`!")
        return 1
    with open(configuration_path, "rb") as file:
        try:
            configuration = tomllib.load(file)
            
        except tomllib.TOMLDecodeError as e:
            logger.error(f"Cannot decode `{configuration_path}`: {e}", file=sys.stderr)
            return 1



    pub_port = configuration["publisher"]["port"]
    host: str = "localhost"
    # addr: str = f"tcp://{host}:{pub_port}"
    # publisher.bind(addr)
    publisher.bind(f"tcp://*:{pub_port}")
    pub_top = "light_level"
    logger.info("ZeroMQ publisher bound to {addr = } on topic {pub_top = }")

    sub_port = configuration["subscriber"]["port"]
    addr: str = f"tcp://{host}:{sub_port}"
    subscriber.connect(addr)
    sub_top: bytes = b"streetlamps"
    subscriber.setsockopt(zmq.SUBSCRIBE, sub_top)
    logger.info("ZeroMQ subscriber connected to {addr = } on topic {sub_top = }")

    logger.info("Connected!")
    

    osm_file = "Maps/map.osm"
    logger.info(f"Extracting street lamps from {osm_file}...")
    street_lamps = extract_street_lamps(osm_file)  # Assuming this function is defined elsewhere
    logger.info(f"Found {len(street_lamps)} street lamps!")

    # Create the SimPy environment
    env = simpy.Environment()
    print(f"{env.now = }")
        
    # Create streetlight nodes (selecting a subset, e.g., first 50 street lamps)
    subset_size = 25  # Adjust this number as needed
    streetlights = [Streetlight(env, int(ids), lat, lon, configuration["setup_values"]["timeout_time"]) for i, (ids, lat, lon) in enumerate(street_lamps)]
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

    logger.info("Starting simulation...")
    n_messages_received: int = 0
    cost = []
    with open('data.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["delta_time", "count_on", "count_off"])
        try:
            while True:
                message = subscriber.recv() #We only recieve messages that observed movement
                # message = {'streetlamps': [11046617406, 2, 3]}
                # data = message['streetlamps']
                # print("Message = ", message)
            
                n_messages_received += 1
                data = cbor2.loads(message[len("streetlamps"):]) 
                # print(data)

                # logger.info(f"Received message #{n_messages_received}: {data}")
                # data is a list of names of streetlights 
                dictionary = {'timestamp' : data['timestamp'], 'changes': {}}
                for streetlight in streetlights:
                    event = {
                            "date": datetime.datetime.fromtimestamp(data['timestamp']),
                            "sunset_time": t(19, 30),
                            "sunrise_time": t(6, 30),
                            "lux_number": 245.5, 
                            "season": "Summer" }
                    if streetlight.name in data['streetlamps']:
                        event["sensor_input"] = True
                    else:
                        event["sensor_input"] = False
                    streetlight.get_event(event)

                    dictionary['changes'][streetlight.name] = streetlight.get_level()
                
                # print('changes = ', dictionary)
                data = cbor2.dumps(dictionary)
                
                publisher.send(bytes(pub_top, encoding='utf-8') + data)
                
                cost = calc_cost(dictionary['changes'], configuration["setup_values"]["delta_time"])
                writer.writerow(cost)
                # cost.append(calc_cost(dictionary['changes'], event['date']))
                if (not n_messages_received % 1000):
                    logger.info("Send changes, message number " + str(n_messages_received))


        except KeyboardInterrupt:
            print("Interrupted!")
        finally:
            subscriber.close()
            publisher.close()
            # context.term()

    
    # Draw the network
    # pos = nx.get_node_attributes(G, 'pos')
    # nx.draw(G, pos, with_labels=True, node_color='lightblue', edge_color='gray')
    # plt.title("Street Lamp Network (Subset)")

    # plot_street_lamps_map(street_lamps[:subset_size])

    # plt.show()

    global send_msg_count
    global receive_msg_count

    logger.info(f"{send_msg_count = }, {receive_msg_count = }")

if __name__ == "__main__":
    sys.exit(main())
