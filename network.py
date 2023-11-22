import simpy
from street_lamp_extractor import extract_street_lamps
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
from cartopy.io.img_tiles import OSM
import math
import networkx as nx
import time

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
        self.action = env.process(self.run())

    def run(self):
        while True:
            # Simulate some activity, like sending messages to neighbors
            yield self.env.timeout(10)  # Adjust the timeout as needed
            current_time = time.strftime("%H:%M:%S", time.gmtime(self.env.now))
            self.send_message(f"Hello from {self.name} at {current_time}")

    def send_message(self, message):
        print(f"{self.env.now}: {self.name} sends message: {message}")
        for neighbor in self.neighbors:
            neighbor.receive_message(message)

    def receive_message(self, message):
        print(f"{self.env.now}: {self.name} received message: {message}")
        self.send_event(message)


    def get_event(self, event):
        self.send_message(self, event)

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


def main():
    osm_file = "Maps/map.osm"
    street_lamps = extract_street_lamps(osm_file)  # Assuming this function is defined elsewhere

    # Create the SimPy environment
    env = simpy.Environment()

    # Create streetlight nodes (selecting a subset, e.g., first 50 street lamps)
    subset_size = 25  # Adjust this number as needed
    streetlights = [Streetlight(env, f"Streetlight_{i}", lat, lon) for i, (lat, lon) in enumerate(street_lamps[:subset_size])]

    # Create a network graph
    G = nx.Graph()

    # Add nodes and edges to the graph
    for i, streetlight in enumerate(streetlights):
        G.add_node(streetlight.name, pos=(streetlight.lat, streetlight.lon))

    # Find connected lamps
    find_connected_lamps(streetlights, G)

    # After creating the graph G
    pos = nx.get_node_attributes(G, 'pos')

    # Run the simulation (not visualized)
    env.run(until=50)
    
    # Draw the network
    pos = nx.get_node_attributes(G, 'pos')
    nx.draw(G, pos, with_labels=True, node_color='lightblue', edge_color='gray')
    plt.title("Street Lamp Network (Subset)")

    plot_street_lamps_map(street_lamps[:subset_size])

    plt.show()


if __name__ == "__main__":
    main()
