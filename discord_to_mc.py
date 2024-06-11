import os
from mcrcon import MCRcon
import discord
from discord.ext import commands

host = os.environ['MCRCON_HOST']
password = os.environ['MCRCON_PASS']
port = os.environ['MCRCON_PORT']

mc_server_guild_id = 1247006457245990963
bot_playground_channel = 1247738950349492294

def say_as(username: str, msg: str):
    print(username, msg)
    with MCRcon(host, password) as mcr:
        mcr.command('/tellraw @a \"§7{0}: §r{1}\"'.format(username, msg)) 
    
if __name__ == '__main__':
    
    intents = discord.Intents.default()
    intents.message_content = True
    
    bot = commands.Bot(command_prefix="$", intents=intents)
    
    with open('.env', 'r') as env:
        token = env.read()

    @bot.command(name='chat')
    async def discord_to_chat(context: commands.Context, *args):
        message = ' '.join(args)
        say_as(context.author, message)
        
    @bot.command(name='list')
    async def list_players(context: commands.Context):
        with MCRcon(host, password) as mcr:
            resp = mcr.command('/list')
            print(resp)
        await context.reply(resp)
        
    @bot.event
    async def on_ready():
        print("Ready!")
        
    bot.run(token=token)