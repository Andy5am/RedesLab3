import json
import string
import numpy as np

def read_file(t):
    with open(t, 'r') as f:
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

    Returns:
        None
    """
    def __init__(self, node, nfile, tfile):
        self.nfile = nfile
        self.tfile = tfile

        self.node = node

        self.names = self.get_names()
        self.neighbors = self.get_neighbors()

        self.addr = self.names[self.node]
        self.vector = {
            self.node: 0,
        }

        for node in self.neighbors:
            self.vector[node] = 1


    """
    Method for getting neighbors information from existen network topology.

    Arguments:
        None

    Returns:
        List with the name of the neighbor nodes
    """
    def get_neighbors(self):
        topo = read_file(self.tfile)

        return topo['config'][self.node]


    """
    Method for getting the names (addresses) each node has assigned.

    Arguments:
        None

    Returns:
        List with the address of each node
    """
    def get_names(self):
        return read_file(self.nfile)['config']



if __name__ == "__main__":
    node = Router("A", 'names-default.txt', 'topo-default.txt')
