
import asyncio
import settings
import sys
import argparse

import slixmpp
from slixmpp.exceptions import IqError, IqTimeout, XMPPError
from aioconsole import ainput


def clean_jid(jid, domain="@alumchat.xyz"):
    if jid[-13:] != domain:
        jid += domain
    
    return jid


class Client(slixmpp.ClientXMPP):

    def __init__(self, jid, password, algorithm):
        super().__init__(jid, password)

        self.nick = None

        self.algorithm = algorithm

        # PLUGINS
        self.register_plugin('xep_0030') # Service Discovery
        self.register_plugin('xep_0199') # XMPP Ping

        # EVENT HANDLERS
        self.add_event_handler("session_start", self.session_start)
        self.add_event_handler("session_start", self.app)
        self.add_event_handler("message", self.recv_message)


    async def session_start(self, event):
        """ Session start. Must send presence to server and get JID's roster. """

        try:
            await self.get_roster()
        except IqError as err:
            print('Error: %s' % err.iq['error']['condition'])
        except IqTimeout:
            print('Error: Request timed out')
        self.send_presence()


    def recv_message(self, msg):
        """ Handles incoming messages. 

        """

        # TODO: routing algorithms

        if msg['type'] in ('chat', 'normal'):
            print(f"{msg['from'].username}: {msg['body']}")
            # msg.reply("Thanks for sending\n%(body)s" % msg).send() #msg['body']
            
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
                    if msg != 'exit':
                        self.message(recipient, msg)
                    else:
                        IN_CHAT = False
 

            elif option==10: # Exit
                print("Exit")
                print("Goodbye!")
                sys.exit()

            else:
                print("Not a valid option.")



if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--alg", dest='alg', help="Routing algorithm to use.")

    args = parser.parse_args()

    if args.alg:
        print(f"Router ON with {args.alg} routing algorithm.")
        print(f"Running node: {settings.JID}")
        xmpp = Client(settings.JID, settings.PASSWORD, args.alg)
    else:
        xmpp = Client(settings.JID, settings.PASSWORD, settings.DEFAULT_ALG)

    xmpp.connect()
    xmpp.process(forever=False)