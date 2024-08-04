# This example requires the 'message_content' intent.

import discord
from discord.ext import commands
import os, time

#client = discord.Client(intents=intents)

#@client.event
#async def on_ready():
#    print(f'We have logged in as {client.user}')

#@client.event
#async def on_message(message: discord.Message):
#    if message.author == client.user:
#        return

#    if message.content.startswith('$hello'):
#        await message.channel.send('Hello!')
#        print(message.channel)
    
#def log_reader():    
#    with open("/opt/minecraft/test_server/logs/" + "latest.log") as logfile:
#        logfile.seek(0, 2)
#        while True:
#            line = logfile.readline()
#            if not line:
#                time.sleep(0.1)
#                continue
#            yield line

class MainBot(commands.Bot):
    async def setup_hook(self):
        await self.load_extension('discord_to_mc')
        #await self.load_extension('mc_to_discord')
        await self.load_extension('log_reader')

def main():
    env = open(".env", 'r')
    token = env.read()

    intents = discord.Intents.default()
    intents.message_content = True
            
    bot = MainBot(command_prefix='$', intents=intents)

    bot.run(token)

if __name__ == '__main__':
    main()
