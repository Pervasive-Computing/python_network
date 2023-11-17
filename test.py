import simpy
from street_lamp_extractor import extract_street_lamps
import matplotlib.pyplot as plt
import networkx as nx

"""
TODO:
- Radius neighbor search    (high priority)
- Neighbor interaction      (high priority) 
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
            # Simulate some activity, like checking for neighbors or status updates
            yield self.env.timeout(10)  # Adjust the timeout as needed
            self.check_neighbors()

    def check_neighbors(self):
        # Example function to simulate interaction with neighbors
        for neighbor in self.neighbors:
            print(f"{self.env.now}: {self.name} checks in with {neighbor.name}")

    def add_neighbor(self, neighbor):
        self.neighbors.append(neighbor)
                              


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
        if i > 0:
            G.add_edge(streetlights[i - 1].name, streetlight.name)

    # Run the simulation (not visualized)
    env.run(until=50)

    # Draw the network
    pos = nx.get_node_attributes(G, 'pos')
    nx.draw(G, pos, with_labels=True, node_color='lightblue', edge_color='gray')
    plt.title("Street Lamp Network (Subset)")
    plt.show()

if __name__ == "__main__":
    main()
