import xml.etree.ElementTree as ET


def extract_street_lamps(osm_file):
    """
    Parses an OSM file and extracts the coordinates of street lamps.

    Args:
    osm_file (str): The path to the OSM file.

    Returns:
    list of tuple: A list of tuples, each containing the latitude and longitude of a street lamp.
    """
    tree = ET.parse(osm_file)
    root = tree.getroot()
    street_lamps = []

    for node in root.findall('node'):
        for tag in node.findall('tag'):
            if tag.get('k') == 'highway' and tag.get('v') == 'street_lamp':
                id = node.get('id')
                lat = float(node.get('lat'))
                lon = float(node.get('lon'))
                street_lamps.append((id, lat, lon))

    return street_lamps



def calculate_center(street_lamps):
    """
    Function to calculate the center of the street lamps
    """
    if not street_lamps:
        return None, None

    sum_lat = sum(lamp[0] for lamp in street_lamps)
    sum_lon = sum(lamp[1] for lamp in street_lamps)
    num_lamps = len(street_lamps)

    return sum_lat / num_lamps, sum_lon / num_lamps