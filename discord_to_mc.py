import os
from mcrcon import MCRcon

host = os.environ['MCRCON_HOST']
password = os.environ['MCRCON_PASS']
port = os.environ['MCRCON_PORT']


bot_playground_channel = 1247738950349492294

def say_as(username, msg):
    with MCRcon(host, password) as mcr:
        resp = mcr.command('/tellraw @a \"§7{0}: §r{1}\"'.format(username, msg))
        print(resp)
        
say_as("jason", "beans")