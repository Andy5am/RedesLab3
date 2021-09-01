"""
Instance example --> router = Router("A", "names-default.txt", "topo-default.txt")
"""

import json
import string


"""
Converts a json formatted string from a .txt file to a python dictionary.

Arguments:
    fname --> Name of the input file

Returns:
    Dictionary
"""
def json_to_dict(fname):
    with open(fname, 'r') as f:
        string = f.read()
        json_string = string.replace("'", '"')
        dict = json.loads(json_string)
    
    return dict


class Router(object):
    """
    Initialization.
    - Defines de router node (A, B, C, ...) and address of the type *@alumchat.xyz
    - Saves the node neighbors and the addresses of each node
    - Initializes the vector for saving the optimal distances

    Arguments:
        node --> Name (letter) of the node assigned
        names --> File with the names in json format
        topo --> File with the topology in json format

    Returns:
        None
    """
    def __init__(self, node, names, topo):
        self.names = names
        self.topo = topo

        self.node = node

        self.names = self.get_names()
        self.neighbors = self.get_neighbors()
        self.to_process = []

        self.addr = self.names[self.node]
        self.vector = {
            self.node: (0, node),
        }

        for nb in self.neighbors:
            self.vector[nb] = (1, nb)


    """
    Method for getting neighbors information from existen network topology.

    Arguments:
        None

    Returns:
        List with the name of the neighbor nodes
    """
    def get_neighbors(self):
        topo = json_to_dict(self.topo)

        return topo['config'][self.node]


    """
    Method for getting the names (addresses) each node has assigned.

    Arguments:
        None

    Returns:
        List with the address of each node
    """
    def get_names(self):
        names = json_to_dict(self.names)
        return names['config']
