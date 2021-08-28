# settings.py
import os
import logging

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

# Environment variables
JID = os.environ.get("JID")
PASSWORD = os.environ.get("PASSWORD")
DEBUG = bool(os.environ.get("DEBUG")) and os.environ.get("DEBUG").lower()=='true'
TESTING = bool(os.environ.get("TESTING")) and os.environ.get("TESTING").lower()=='true'
DEFAULT_ALG = 'flooding'

# Logging
log_lvl = logging.DEBUG #if DEBUG else logging.ERROR
logging.basicConfig(
    level=log_lvl,
    format='%(levelname)-8s %(message)s'
)

# Constants
MAIN_MENU = """
    -------------------------------
                MAIN MENU
    -------------------------------
        1. Send message
        2. Exit
"""

ALG_MENU = """
    -------------------------------
            ROUTING ALGORITHMS
    -------------------------------
        1. Flooding
        2. Distance Vector
        3. Link State
"""

ALGORITHMS = {
    "flooding": "FLOODING",
    "dv": "DISTANCE VECTOR",
    "ls": "LINK STATE"
}