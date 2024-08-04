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
import sys
import os

#logger = logging.getLogger('discord')

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

async def filter_logs():
    print('log reader task starting')
    proc = await asyncio.create_subprocess_exec(
        #"/usr/bin/journalctl",
        #"--unit=minecraft.service",
        #"--lines=0",
        #"--output=cat",
        #"--follow",
        "/usr/bin/tail",
        "--lines=100",
        "--follow=name",
        "--retry",
        os.path.join(os.getenv('MINECRAFT_DIR'), 'logs', 'latest.log'),
        stdout=asyncio.subprocess.PIPE,
    )
    print('log reader started')
    async for raw_line_bytes in proc.stdout:
        raw_line = raw_line_bytes.decode()
        match = server_error_re.fullmatch(raw_line)
        if match:
            print('log ' + match.group(1))
            continue

        match = server_info_re.fullmatch(raw_line)
        if not match:
            continue
        line = match.group(1)

        msg_type = get_msg_type(line)
        if MsgType.CHAT in msg_type:
            print('chat ' + line)
        if MsgType.LOG in msg_type:
            print('log ' + line)
    print('log reader reached end-of-file')
    await proc.wait()
    print('log reader terminated')

async def backup_log():
    proc = await asyncio.create_subprocess_exec(
        "/usr/bin/journalctl",
        "--unit=minecraft_backup_daily.service",
        "--lines=10000",
        "--output=cat",
        #"--follow",
        stdout=asyncio.subprocess.PIPE,
    )
    async for line_bytes in proc.stdout:
        line = line_bytes.decode()
        if line.startswith('tar: '):
            print(line, end='')
        if line.startswith('cp: '):
            print(line, end='')
    await proc.wait()

asyncio.run(backup_log())
