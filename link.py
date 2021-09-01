
import asyncio
import re
import settings
import sys
import argparse
import json
import random
from time import time

import slixmpp
from slixmpp.exceptions import IqError, IqTimeout, XMPPError
from aioconsole import ainput

from linkRouter import Router

from vectorDistance import read_file


def clean_jid(jid, domain="@alumchat.xyz"):
    if jid[-13:] != domain:
        jid += domain
    
    return jid


class Client(slixmpp.ClientXMPP):

    def __init__(self, jid, password, algorithm:str, topo:dict, names:dict):
        super().__init__(jid, password)

        self.nick = None

        self.algorithm = algorithm

        self.router = Router(jid)

        if self.algorithm.lower()=='flooding':
            self.counter = 0
            self.nodes = {}

        # PLUGINS
        self.register_plugin('xep_0030') # Service Discovery
        self.register_plugin('xep_0199') # XMPP Ping

        # EVENT HANDLERS
        self.add_event_handler("session_start", self.session_start)
        self.add_event_handler("session_start", self.app)
        self.add_event_handler("message", self.receive_message)


    async def session_start(self, event):
        """ Session start. Must send presence to server and get JID's roster. """

        try:
            await self.get_roster()
        except IqError as err:
            print('Error: %s' % err.iq['error']['condition'])
        except IqTimeout:
            print('Error: Request timed out')
        self.send_presence()


    def message(self, recipient, message=None, mtype='chat'):
        """ Sends message to another user in server. """

        recipient = clean_jid(recipient) # Check for domain
        msg = self.Message()

        msg['to'] = recipient
        msg['body'] = message
        msg['type'] = mtype

        msg.send()
    
    async def app(self, event):

        self.setup_router()
        IN_APP_LOOP = True

        while IN_APP_LOOP:

            print(settings.MAIN_MENU)
            option = int(await ainput("\nSelect an option: "))

            if option==1: # Send direct message
                recipient = str(await ainput("JID: "))
                recipient = clean_jid(recipient)


                print(f"\nChatting with {recipient}")
                print("Type 'exit' to exit chat.")

                
                msg = str(await ainput(">> "))
                self.router.set_distances(self.router.matrix)
                self.router.dijkstra(self.router.name)
                path = self.router.shortest_path(self.router.name, recipient)
                msg_payload = {'type': 'direct', 'message': msg, 'path': path}
                message = self.create_direct_message(recipient, msg_payload)
                self.direct_message(path[1],message)

            elif option==10: # Exit
                print("Exit")
                print("Goodbye!")
                IN_APP_LOOP = False

            else:
                print("Not a valid option.")

    def setup_router(self):
        self.loop.create_task(self.refresh_topology_packages())
        print("Setting up router...")

    async def refresh_topology_packages(self):
        while True:
            for neighbor in self.router.neighbors:
                self.send_echo_message(neighbor)

            await asyncio.sleep(5)

            self.flooding()


    def flooding(self):
        own_lsp = self.router.build_package()
        flood_msg = {
            'type': "lsp",
            'lsp': own_lsp,
        }

        for neighbor in self.router.neighbors:
            msg = self.create_message(neighbor, flood_msg)
            self.send_direct_message(neighbor, msg)

    def send_echo_message(self, neighbor):
        echo_msg = {
            'type': "echo" ,
            'timestamp': time()
        }
        msg = self.create_message(neighbor, echo_msg)
        self.send_direct_message(neighbor, msg)
    
    def receive_message(self, message):
        message_type = str(message['type'])
        if message_type == 'chat':
            body_json = str(message['body'])
            body = json.loads(body_json)
            
            sender = body["from_node"]
            recipient = body["to_node"]
            nodes_traveled = body["nodes"]
            payload = body["payload"]
            msg_type = payload["type"]
            if "echo"  == msg_type:
                received_time = payload['timestamp']
                ack_msg = {
                    'type': "ack",
                    'start_timestamp': received_time
                }
                ack_msg_json = self.create_message(sender, ack_msg)
                message.reply(ack_msg_json).send()

            elif "ack" == msg_type:
                start_time = payload['start_timestamp']
                if sender is not None:
                    end_time = time()
                    time_diff = (end_time - start_time) / 2 
                    self.router.change_weight(sender, time_diff)

            elif "lsp" == msg_type:
                received_lsp = payload['lsp']

                self.router.change_neighbor_package(sender, received_lsp)
                self.router.build_graph_matrix()

                
                for neighbor in self.router.neighbors:
                    if neighbor != sender:
                        resend_msg = self.resend_message(neighbor, payload, nodes_traveled)
                        self.send_direct_message(neighbor, resend_msg)
            
            elif "direct" == msg_type:
                if recipient == self.router.name:
                    print("Mensaje: ", payload['message'])
                    print(f"Recorrido: {nodes_traveled}")
                else:
                    print('reenviando')
                    path = payload['path']
                    print(path)
                    index = path.index(self.router.name)
                    print(index)
                    msg = self.create_direct_message(path[index+1],payload, path[0], nodes_traveled)
                    self.direct_message(path[index+1],msg)

    def create_direct_message(self, recipient, payload, sender = None, nodes = ''):
        if sender == None:
            sender = self.router.name
        new_message = {
            "from_node": sender,
            "to_node": recipient,
            "jumps": 0,
            "distance": 0,
            "nodes": nodes,
            "payload": payload
        }

        new_message["nodes"] += f"{self.router.name}"
        new_message = json.dumps(new_message)
        return new_message


    def direct_message(self, send_to, message):
        self.send_message(
            mto = send_to,
            mbody = message,
            mtype = 'chat',
            mfrom = self.jid
        )

    def send_direct_message(self, send_to, message):
        message = json.loads(message)
        routes = self.router.get_routes(message["to_node"])
        if len(routes) == 0:
            print(f"Unknown route to {message['to_node']}")
        else:
            send_to = random.choice(routes)
            message["jumps"] += 1
            message["distance"] += 1

        self.direct_message(send_to, json.dumps(message))
    
    def create_message(self, recipient, payload, nodes = ""):
        new_message = {
            "from_node": self.router.name,
            "to_node": recipient,
            "jumps": 0,
            "distance": 0,
            "nodes": nodes,
            "payload": payload
        }

        new_message["nodes"] += f"{self.router.name}"
        new_message = json.dumps(new_message)
        return new_message

    def resend_message(self, recipient, payload, nodes = ""):
        lsp = payload['lsp']
        new_message = {
            "from_node": lsp['origin'],
            "to_node": recipient,
            "jumps": 0,
            "distance": 0,
            "nodes": nodes,
            "payload": payload
        }

        new_message["nodes"] += f"{self.router.name}"
        new_message = json.dumps(new_message)
        return new_message
            


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--alg", dest='alg', help="Routing algorithm to use.")

    args = parser.parse_args()

    # TODO: parametrize topo and names files?
    names = read_file('names-default.txt')
    topo = read_file('topo-default.txt')
    jid = input('JID: ')
    password = input('Password: ')
    if args.alg:
        print(f"Router ON with {args.alg} routing algorithm.")
        print(f"Running node: {settings.JID}")
        xmpp = Client(jid, password, args.alg, topo=topo, names=names)
    else:
        xmpp = Client(settings.JID, settings.PASSWORD, settings.DEFAULT_ALG, topo=topo, names=names)

    xmpp.connect()
    xmpp.process(forever=False)