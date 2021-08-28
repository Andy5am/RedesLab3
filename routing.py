import sys
import json
import asyncio
import argparse

from aioconsole import ainput

import slixmpp
from slixmpp.exceptions import IqError, IqTimeout, XMPPError

import settings
from vectorDistance import json_to_dict, Router


def clean_jid(jid, domain="@alumchat.xyz"):
    if jid[-13:] != domain:
        jid += domain
    
    return jid


class Client(slixmpp.ClientXMPP):

    def __init__(self, jid, password, algorithm:str, topo:dict, names:dict):
        slixmpp.ClientXMPP.__init__(self, jid, password)

        self.nick = None

        self.algorithm = algorithm
        self.topo = topo
        self.names = names

        self.node = self.recv_names(self.jid, self.names)

        self.router = Router(self.node, 'names-demo.txt', 'topo-demo.txt')

        if self.algorithm.lower()=='flooding':
            self.counter = 0
            self.nodes = {}

        # PLUGINS
        self.register_plugin('xep_0030') # Service Discovery
        self.register_plugin('xep_0199') # XMPP Ping

        # EVENT HANDLERS
        self.add_event_handler("session_start", self.session_start)
        self.add_event_handler("session_start", self.app)
        self.add_event_handler("session_start", self.bellman_ford)
        self.add_event_handler("message", self.recv_message)


    """
    Calculation of the optimal route for each node "discovered" and saved in vector.

    Processes incoming 'update' packages from neighbor nodes to find a better route (if there is one)
    for each saved node, or add one if there is not one previous existing route.

    Arguments:
        None

    Returns:
        None
    """
    async def bellman_ford(self, event):
        while True:
            await asyncio.sleep(0.5)
            
            work = self.router.to_process.copy()

            for pair in work:
                for key, value in pair[1].items():
                    try:
                        # incoming value (route) lower than the one stored
                        if self.router.vector[key][0] > value[0] + 1:
                            self.router.vector[key] = (value[0] + 1, pair[0])
                            print(self.router.vector[key])
                    except KeyError:
                        print("\nNEW NODE!\n")
                        self.router.vector[key] = (value[0] + 1, pair[0])
                        print(self.router.vector[key])

            # build dict to send to neighbor nodes
            payload = {
                "type": "update",
                "sender": self.router.node,
                "vector": self.router.vector
            }
            # send to all neighbors
            for node in self.router.neighbors:
                self.message(self.router.names[node], json.dumps(payload))


    async def session_start(self, event):
        """ Session start. Must send presence to server and get JID's roster. """
        self.send_presence()

        try:
            await self.get_roster()
        except IqError as err:
            print('Error: %s' % err.iq['error']['condition'])
        except IqTimeout:
            print('Error: Request timed out')


    def recv_message(self, msg):
        """ Handles incoming messages. """

        if msg['type'] in ('chat', 'normal'):
            payload = json.loads(msg['body']) # get payload
            
            if self.algorithm.lower()=='flooding':
                # Validate source node list
                if payload['source'] in self.nodes.keys():
                    # Check if msg has been flooded
                    if payload['counter'] <= len(self.nodes[payload['source']]):
                        print("Message in node list. Discarding message.")
                        return

                else:
                    self.nodes[payload['source']] = []
                    self.nodes['source'].append(payload['counter'])

                if payload['destination']==self.jid:
                    print(f"{payload['source']} says: {payload['message']}")
                else:
                    for node in self.topo[self.node]: # node neighbors
                        neighbor = self.names[node]
                        if msg['from'] != neighbor:
                            self.message(neighbor, json.dumps(payload))

            if self.algorithm.lower() == 'dv':
                # if the message is about vector state, append to list for bellman-ford to process
                if payload['type'] == "update":
                    self.router.to_process.append((payload['sender'], payload['vector']))
                # if the message is a normal communication, print if self is recipient, forward if not
                elif payload['type'] == "comm":
                    try:
                        if self.router.node != payload['recipient_node']:
                            payload['node_count'] += 1 # increment the node counter
                            payload['node_list'].append(self.node) # append self node to node list

                            dest = self.router.vector[payload['recipient_node']][1]
                            self.message(self.router.names[dest], json.dumps(payload)) # forward message

                            print(f""" FORWARDED MESSAGE RECEIVED
                            --> FROM: [{payload['sender_node']}] {payload['sender']}
                            --> TO: [{payload['recipient_node']}] {payload['recipient']}
                            --> FORWARDED TO: [{dest}] {self.router.names[dest]}
                            """)
                        else:
                            # print received message if intended recipient
                            print(f""" MESSAGE RECEIVED
                            --> FROM: [{payload['sender_node']}] {payload['sender']}
                            --> TO: [{payload['recipient_node']}] {payload['recipient']}
                            --> JUMPS: {payload['node_count']}
                            --> NODES: {payload['node_list']}
                            --> SAYS: {payload['message']}
                            """)
                    except KeyError:
                        print("\nNODE NO LONGER EXISTS!\n")


            
        elif msg['type'] in ('error'):
            print('An error has ocurred.')


    def message(self, recipient, message=None, mtype='chat'):
        """ Sends message to another user in server. """

        recipient = clean_jid(recipient) # Check for domain
        msg = self.Message()

        msg['to'] = recipient
        msg['body'] = message
        msg['type'] = mtype

        msg.send()

    def recv_topo(self, topo:dict):
        self.topo = topo

    def recv_names(self, addr:str, names:dict):
        """ Identify node name based on names dict. """
        for key, value in names.items():
            if value == addr:
                return key

    
    async def app(self, event):
        IN_APP_LOOP = True

        while IN_APP_LOOP:

            print(settings.MAIN_MENU)
            option = int(await ainput("\nSelect an option: "))

            if option==1: # Send direct message
                recipient = str(await ainput("JID: "))
                recipient = clean_jid(recipient)


                print(f"\nChatting with {recipient}")
                print("Type 'exit' to exit chat.")

                IN_CHAT = True

                while IN_CHAT:
                    msg = str(await ainput(">> "))
                    
                    payload = {}

                    if self.algorithm.lower()=='flooding':
                        self.counter += 1
                        payload = {
                            "counter": self.counter,
                            "source": self.node,
                            "destination": recipient,
                            "message": msg
                        }
                    
                    elif self.algorithm.lower() == 'dv':
                        recipient_node = self.recv_names(recipient, self.names)
                        payload = {
                            "type": "comm",
                            "sender": self.jid,
                            "sender_node": self.router.node,
                            "recipient": recipient,
                            "recipient_node": recipient_node,
                            "node_count": 1,
                            "node_list": [self.node],
                            "message": msg
                        }

                    if msg != 'exit':
                        if self.algorithm.lower()=='flooding':
                            for node in self.topo[self.node]: # node neighbors
                                neighbor = self.names[node]
                                self.message(neighbor, json.dumps(payload))
                        
                        if self.algorithm.lower()=='dv':
                            intermediary = self.router.vector[recipient_node][1]

                            self.message(self.names[intermediary], json.dumps(payload))
                    
                            print(f"""SENT MESSAGE
                            --> TO: [{recipient_node}] {recipient}
                            --> THROUGH: [{intermediary}] {self.names[intermediary]}
                            """)
                    else:
                        IN_CHAT = False
 

            elif option==10: # Exit
                print("Exit")
                print("Goodbye!")
                IN_APP_LOOP = False

            else:
                print("Not a valid option.")



if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--alg", dest='alg', help="Routing algorithm to use.")

    args = parser.parse_args()

    # TODO: parametrize topo and names files?
    topo = json_to_dict('topo-demo.txt')
    names = json_to_dict('names-demo.txt')

    if args.alg:
        print(f"Router ON with {settings.ALGORITHMS[args.alg]} routing algorithm.")
        # print(f"Running node: {settings.JID}")
        # xmpp = Client(settings.JID, settings.PASSWORD, args.alg, topo=topo, names=names)
        print(f"Running node: {jid}")
        xmpp = Client(jid, pwd, args.alg, topo=topo['config'], names=names['config'])
    else:
        xmpp = Client(settings.JID, settings.PASSWORD, settings.DEFAULT_ALG, topo=topo, names=names)

    xmpp.connect()
    xmpp.process(forever=False)