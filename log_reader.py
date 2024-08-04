#!/usr/bin/python

import discord
from discord.ext import tasks, commands
import logging
import threading
import queue
import subprocess
import asyncio
import re
import enum
import constants
import sys
import os

logger = logging.getLogger('discord')

server_error_re = re.compile(r'\[\d{2}:\d{2}:\d{2}\] (\[.*/ERROR\]: .*)\n')
server_info_re = re.compile(r'\[\d{2}:\d{2}:\d{2}\] \[Server thread/INFO\]: (.*)\n')
chat_msg_prefix_re = re.compile(r'<\w{3,32}> ')
villager_prefix_re = re.compile(r'Villager \w+\[\'.+\'/\d+, l=\'.+\', x=.+, y=.+, z=.+\]')
join_leave_suffixes = [
    ' joined the game',
    ' left the game',
]
server_stop_msg = '[Rcon: Stopping the server]'
rcon_prefix = '[Rcon: '
server_start_prefix = 'Starting minecraft server version '
advancement_fragments = [
    ' has made the advancement ',
    ' has reached the goal ',
    ' has completed the challenge ',
]
death_message_fragments = [
    ' was pricked to death',
    ' walked into a cactus while trying to escape ',
    ' drowned',
    ' died from dehydration',
    ' experienced kinetic energy',
    ' blew up',
    ' was blown up by ',
    ' hit the ground too hard',
    ' fell from a high place',
    ' fell off a ladder',
    ' fell off some ',
    ' fell off scaffolding',
    ' fell while climbing',
    ' was doomed to fall',
    ' was impaled on a stalagmite',
    ' was skewered by a falling stalactite',
    ' went up in flames',
    ' walked into fire while fighting ',
    ' burned to death',
    ' was burned to a crisp while fighting ',
    ' went off with a bang',
    ' tried to swim in lava',
    ' was struck by lightning',
    ' discovered the floor was lava',
    ' walked into the danger zone due to ',
    ' was killed by magic',
    ' froze to death',
    ' was frozen to death by ',
    ' was slain by ',
    ' was stung to death',
    ' was obliterated by a sonically-charged shriek',
    ' was shot by ',
    ' was pummeled by ',
    ' was fireballed by ',
    ' was shot by a skull from ',
    ' starved to death',
    ' suffocated in a wall',
    ' was squished too much',
    ' was squashed by ',
    ' left the confines of this world',
    ' was poked to death by a sweet berry bush',
    ' while trying to hurt ',
    ' was impaled by ',
    ' fell out of the world',
    ' didn\'t want to live in the same world as ',
    ' withered away',
    ' died',
    ' was killed',
    ' was roasted in dragon\'s breath',
    ' died from dehydration',
]

class MsgType(enum.Flag):
    CHAT = enum.auto()
    LOG = enum.auto()

def get_msg_type(line):
    if line == server_stop_msg:
        return MsgType.LOG
    if line.startswith(rcon_prefix):
        return MsgType(0)
    if line.startswith(server_start_prefix):
        return MsgType.LOG
    if chat_msg_prefix_re.match(line):
        return MsgType.CHAT
    if villager_prefix_re.match(line):
        return MsgType.LOG
    if any(adv_str in line for adv_str in advancement_fragments):
        return MsgType.CHAT
    if any(death_str in line for death_str in death_message_fragments):
        return MsgType.CHAT
    if any(jl_str in line for jl_str in join_leave_suffixes):
        return MsgType.CHAT
    return MsgType(0)

class McToDiscord(commands.Cog):
    def __init__(self, bot, chat_channel_id, log_channel_id):
        self.bot = bot
        self.chat_channel_id = chat_channel_id
        self.log_channel_id = log_channel_id
        self.relay_messages.start()
        self.relay_hourly_errors.start()
        self.relay_daily_errors.start()

    @tasks.loop()
    async def relay_messages(self):
        logger.info('log reader task starting')
        proc = await asyncio.create_subprocess_exec(
            #"/usr/bin/journalctl",
            #"--unit=minecraft.service",
            #"--lines=0",
            #"--output=cat",
            #"--follow",
            "/usr/bin/tail",
            "--lines=0",
            "--follow=name",
            "--retry",
            os.path.join(os.getenv('MINECRAFT_DIR'), 'logs', 'latest.log'),
            stdout=asyncio.subprocess.PIPE,
        )
        logger.info('log reader started')
        async for raw_line_bytes in proc.stdout:
            raw_line = raw_line_bytes.decode()
            match = server_error_re.fullmatch(raw_line)
            if match:
                await self.log_channel.send(match.group(1))
                continue

            match = server_info_re.fullmatch(raw_line)
            if not match:
                continue
            line = match.group(1)

            msg_type = get_msg_type(line)
            if MsgType.CHAT in msg_type:
                await self.chat_channel.send(line)
            if MsgType.LOG in msg_type:
                await self.log_channel.send(line)
        logger.info('log reader reached end-of-file')
        await proc.wait()
        logger.info('log reader terminated')

    @tasks.loop()
    async def relay_hourly_errors(self):
        logger.info('hourly log monitor task starting')
        proc = await asyncio.create_subprocess_exec(
            "/usr/bin/journalctl",
            "--unit=minecraft_backup_hourly.service",
            "--lines=0",
            "--output=cat",
            "--follow",
            stdout=asyncio.subprocess.PIPE,
        )
        logger.info('hourly log monitor started')
        async for line_bytes in proc.stdout:
            line = line_bytes.decode()
            if line.startswith('tar: '):
                await self.log_channel.send('hourly backup process: ' + line)
        logger.info('hourly log monitor reached end-of-file')
        await proc.wait()
        logger.info('hourly log monitor terminated')

    @tasks.loop()
    async def relay_daily_errors(self):
        logger.info('daily log monitor task starting')
        proc = await asyncio.create_subprocess_exec(
            "/usr/bin/journalctl",
            "--unit=minecraft_backup_daily.service",
            "--lines=0",
            "--output=cat",
            "--follow",
            stdout=asyncio.subprocess.PIPE,
        )
        logger.info('daily log monitor started')
        async for line_bytes in proc.stdout:
            line = line_bytes.decode()
            if line.startswith('tar: '):
                await self.log_channel.send('daily backup process: ' + line)
        logger.info('daily log monitor reached end-of-file')
        await proc.wait()
        logger.info('daily log monitor terminated')

    @relay_messages.before_loop
    @relay_hourly_errors.before_loop
    @relay_daily_errors.before_loop
    async def before_task(self):
        await self.bot.wait_until_ready()
        self.chat_channel = self.bot.get_channel(self.chat_channel_id)
        self.log_channel = self.bot.get_channel(self.log_channel_id)

async def setup(bot):
    await bot.add_cog(McToDiscord(bot,
                                  chat_channel_id=constants.chat_channel_id,
                                  log_channel_id=constants.log_channel_id))

if __name__ == '__main__':
    class RelayBot(commands.Bot):
        async def setup_hook(self):
            await self.add_cog(McToDiscord(self,
                                           chat_channel_id=constants.bot_playground_channel_id, 
                                           log_channel_id=constants.bot_playground_channel_id))

    with open(".env", 'r') as env:
        token = env.read()
    intents = discord.Intents.default()
    bot = RelayBot(command_prefix='$', intents=intents)
    bot.run(token)
