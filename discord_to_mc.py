import os
from mcrcon import MCRcon
import discord
from discord.ext import commands
import constants

host = os.environ['MCRCON_HOST']
password = os.environ['MCRCON_PASS']
port = int(os.environ['MCRCON_PORT'])

mc_server_guild_id = 1247006457245990963
bot_playground_channel = 1247738950349492294

def try_command(command):
    try:
        with MCRcon(host, password, port=port) as mcr:
            return mcr.command(command)
    except ConnectionRefusedError:
        return 'Error: server down'

def say_as(username: str, msg: str):
    print(username, msg)
    try_command('/tellraw @a \"§7{0}: §r{1}\"'.format(username, msg))

class DiscordToMc(commands.Cog):
    @commands.Cog.listener()
    async def on_message(self, message):
        if (message.author.id != constants.bot_user_id and 
                message.channel.id == constants.chat_channel_id):
            say_as(message.author.display_name, message.content)

    #@commands.command(name='chat')
    #async def discord_to_chat(self, context: commands.Context, *args):
    #    message = ' '.join(args)
    #    say_as(context.author, message)

    @commands.command(name='list')
    async def list_players(self, context: commands.Context):
        """
        Lists the players who are online

        Runs "/list" on the Minecraft server.
        This command only works while the server is running.
        """
        resp = try_command('/list')
        print(resp)
        await context.reply(resp)

    @commands.command(name='tick')
    async def tick_query(self, context: commands.Context):
        """
        Displays information about the server's performance

        Runs "/tick query" on the Minecraft server.
        This command only works while the server is running.
        """
        resp = try_command('/tick query')
        print(resp)
        await context.reply(resp)

async def setup(bot):
    await bot.add_cog(DiscordToMc())
    
if __name__ == '__main__':
    class CommandBot(commands.Bot):
        async def setup_hook(self):
            await self.add_cog(DiscordToMc())
    
    intents = discord.Intents.default()
    intents.message_content = True
    
    bot = CommandBot(command_prefix="$", intents=intents)
    
    with open('.env', 'r') as env:
        token = env.read()
        
    @bot.event
    async def on_ready():
        print("Ready!")
        
    bot.run(token=token)
