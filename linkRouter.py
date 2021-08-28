import sys
from time import time
from settings import *
import json
import numpy as np

class Router(object):

    def __init__(self, name) -> None:
        self.id = None
        self.name = name

        self.distances = {}
        self.nodes = []
        self.previos = {}
        self.visited = {}

        self.neighbor_ids = []
        self.users = {}
        self.users_list = []
        self.neighbors = []
        self.neighbors_distance = {}
        self.matrix = np.empty((len(self.users), len(self.users)))

        self.routing_table = {}
        self.package = {
            'origin': self.name,
            'seq': 0,
            'age': time(),
            'weights': {}
        }
        self.names_list = {}
        self.configure_files()
        self.MAX_WEIGHT = sys.maxsize
        self.packages = {}

    
    def configure_files(self):
        file = open("names.txt", "r")
        file_content = file.read().replace("'", '"')
        users_content = json.loads(file_content)

        self.users = users_content['config']
        for key, value in self.users.items():
            if key in self.users_list:
                pass
            else:
                self.users_list.append(key)
            if value == self.name:
                self.id = key

        file = open("topo.txt", "r")
        file_content = file.read().replace("'", '"')
        topo_content = json.loads(file_content)

        for key, value in topo_content['config'].items():
            if key == self.id:
                self.neighbor_ids = value

        for neighbor_id in self.neighbor_ids:
            self.neighbors.append(self.users[neighbor_id])

        for neighbor in self.neighbors:
            self.neighbors_distance[neighbor] = 1

        self.matrix = np.empty((len(self.users), len(self.users)))
        
    def get_routes(self, dest):
        m = self.MAX_WEIGHT
        routes = list()

        if (dest in self.routing_table):
            m, routes = self.short_route(self.routing_table[dest])

        if (dest in self.neighbors_distance):
            if (self.neighbors_distance[dest] < m):
                m = self.neighbors_distance[dest]
                routes = [dest]

            elif (self.neighbors_distance[dest] == m):
               routes.append(dest)
        return routes

    def build_graph_matrix(self):
        for i in range(len(self.users)):
            for j in range(len(self.users)):
                if i == j:
                    self.matrix[i][j]=0
                else:
                    row_name = self.users[self.users_list[i]]
                    col_name = self.users[self.users_list[j]]
                    try:
                        peso = self.packages[row_name]['weights'][col_name]
                        self.matrix[i][j]=peso
                    except:
                        self.matrix[i][j]=0

    def change_weight(self, node, weight):
        self.neighbors_distance[node] = weight

    def build_package(self):
        current_time = time()
        new_lsp = {
            'origin': self.name,
            'seq': int(self.package['seq']) + 1,
            'age': current_time,
            'weights': self.neighbors_distance,
        }
        self.package = new_lsp
        self.packages[self.name]=self.package
        return self.package

    def short_route(self, routes):
        if (len(routes) == 0):
            return self.MAX_WEIGHT, routes

        min_weight = min(routes, key = lambda x: x[1])[1]
        min_routes = list(map(lambda x: x[0], filter(lambda x: x[1] == min_weight, routes)))
        return min_weight, min_routes


    def change_neighbor_package(self, node, lsp):
        self.packages[node] = lsp

    def set_distances(self, router_matrix):

        num_nodes = len(router_matrix)

        for i in range(num_nodes):
            tempdict = {}
            for j in range(num_nodes):
                if i!=j and router_matrix[i][j]!=-1:
                    tempdict[j+1] = router_matrix[i][j]
            self.distances[i+1] = tempdict
            self.nodes.append(i+1)

    def dijkstra(self, start):

        for key, value in self.users.items():
            if value == start:
                start = key
        start = self.users_list.index(start)+1 

        unvisited = {node: None for node in self.nodes}
        self.previous = {node: None for node in self.nodes}
        interface = {node: None for node in self.nodes}
        self.visited = {node: None for node in self.nodes}

        current = int(start)
        currentDist = 0
        unvisited[current] = currentDist

        while True:
            for next, distance in self.distances[current].items():

                if next not in unvisited: continue
                
                newDist = currentDist + distance

                if not unvisited[next] or unvisited[next] > newDist:
                    unvisited[next] = newDist
                    self.previous[next] = current

                    if not interface[current]:
                        interface[next] = next
                    else:
                        interface[next] = interface[current]
                        
            self.visited[current] = currentDist
            del unvisited[current]
            
            done = 1
            for x in unvisited:
                if unvisited[x]:
                    done = 0
                    break
            if not unvisited or done:
                break

            elements = [node for node in unvisited.items() if node[1]]

            current, currentDist = sorted(elements, key = lambda x: x[1])[0]


    def shortest_path(self, start, end):

        for key, value in self.users.items():
            if value == start:
                start = key
        start = self.users_list.index(start)+1 

        for key, value in self.users.items():
            if value == end:
                end = key
        end = self.users_list.index(end)+1 

        path = []
        dest = int(end)
        src = int(start)
        path.append(dest)

        while dest != src:
            path.append(self.previous[dest])
            dest = self.previous[dest]

        path.reverse()

        for node in path:
            name = self.users[self.users_list[node-1]]
            index = path.index(node)
            path[index]=name
        return path
