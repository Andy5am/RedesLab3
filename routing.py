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

        self.node = self.recv_names(self.names)

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


    async def bellman_ford(self, event):
        while True:
            work = self.router.to_process.copy()

            await asyncio.sleep(5)

            print(work, self.router.to_process)


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
                print(payload)
                self.router.to_process.append(payload['sender'])

            
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

    def recv_names(self, names:dict):
        """ Identify node name based on names dict. """
        for key, value in names.items():
            if value == self.jid:
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
                    self.counter += 1
                    
                    payload = {}

                    if self.algorithm.lower()=='flooding':
                        payload = {
                            "counter": self.counter,
                            "source": self.node,
                            "destination": recipient,
                            "message": msg
                        }
                    
                    elif self.algorithm.lower() == 'dv':
                        payload = {
                            "type": "check",
                            "sender": self.router.node,
                            "message": msg
                        }

                    if msg != 'exit':
                        if self.algorithm.lower()=='flooding':
                            for node in self.topo[self.node]: # node neighbors
                                neighbor = self.names[node]
                                self.message(neighbor, json.dumps(payload))
                        
                        if self.algorithm.lower()=='dv':
                            for node in self.router.neighbors:
                                self.message(self.router.names[node], json.dumps(payload))
                    
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
        print(f"Running node: {settings.JID}")
        xmpp = Client(settings.JID, settings.PASSWORD, args.alg, topo=topo, names=names)
    else:
        xmpp = Client(settings.JID, settings.PASSWORD, settings.DEFAULT_ALG, topo=topo, names=names)

    xmpp.connect()
    xmpp.process(forever=False)