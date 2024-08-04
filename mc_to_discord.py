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

logger = logging.getLogger('discord')

server_error_re = re.compile(r'\[\d{2}:\d{2}:\d{2}\] (\[.*/ERROR\]: .*)\n')
server_info_re = re.compile(r'\[\d{2}:\d{2}:\d{2}\] \[Server thread/INFO\]: (.*)\n')
chat_msg_prefix_re = re.compile(r'<\w{3,32}> ')
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
    if any(adv_str in line for adv_str in advancement_fragments):
        return MsgType.CHAT
    if any(death_str in line for death_str in death_message_fragments):
        return MsgType.CHAT
    if any(jl_str in line for jl_str in join_leave_suffixes):
        return MsgType.CHAT | MsgType.LOG
    return MsgType(0)

def filter_logs(message_queue, debug_queue):
    args = [
            "/usr/bin/journalctl",
            "--unit=minecraft.service",
            "--lines=0",
            "--output=cat",
            "--follow",
            ]
    debug_queue.put('log reader thread starting')
    try:
        with subprocess.Popen(args, stdout=subprocess.PIPE, encoding='utf-8') as proc:
            for raw_line in proc.stdout:
                match = server_error_re.fullmatch(raw_line)
                if match:
                    message_queue.put((MsgType.LOG, match.group(1)))
                    return

                match = server_info_re.fullmatch(raw_line)
                if not match:
                    continue
                line = match.group(1)

                msg_type = get_msg_type(line)
                if msg_type:
                    message_queue.put((msg_type, line))
            debug_queue.put('journalctl process reached end-of-file')
        debug_queue.put('log reader thread terminating successfully')
    except Exception as e:
        debug_queue.put('log reader thread crashed')
        debug_queue.put(str(type(e)))
        debug_queue.put(str(e.args))
        debug_queue.put(str(e))
    finally:
        debug_queue.put('log reader thread terminating')

class McToDiscord(commands.Cog):
    def __init__(self, bot, chat_channel_id, log_channel_id):
        self.bot = bot
        self.chat_channel_id = chat_channel_id
        self.log_channel_id = log_channel_id
        self.queue = queue.Queue()
        self.debug_queue = queue.Queue()
        self.start_log_reader()
        self.relay_messages.start()

    def start_log_reader(self):
        self.thread = threading.Thread(target=filter_logs, args=(self.queue, self.debug_queue))
        self.thread.daemon = True
        self.thread.start()

    @tasks.loop(seconds=5.0)
    async def relay_messages(self):
        while True:
            try:
                debug_msg = self.debug_queue.get_nowait()
            except queue.Empty:
                break
            logger.info(debug_msg)
        while True:
            try:
                (msg_type, line) = self.queue.get_nowait()
            except queue.Empty:
                break
            if MsgType.CHAT in msg_type:
                await self.chat_channel.send(line)
            if MsgType.LOG in msg_type:
                await self.log_channel.send(line)
        if not self.thread.is_alive():
            self.start_log_reader()

    @relay_messages.before_loop
    async def before_relay_messages(self):
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
