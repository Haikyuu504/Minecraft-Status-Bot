import discord
from discord.ext import tasks, commands
from mcstatus.server import JavaServer
import os
import requests
import json
import base64

TOKEN = os.getenv('DISCORD_BOT_TOKEN')
MINECRAFT_SERVER_ADDRESS = ''
CHANNEL_NAME = ''

intents = discord.Intents.default()
intents.message_content = True  
client = commands.Bot(command_prefix='!', intents=intents)

previous_status = None
previous_players = set()

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    channel = discord.utils.get(client.get_all_channels(), name=CHANNEL_NAME)
    if channel is None:
        print(f"Channel '{CHANNEL_NAME}' not found.")
    else:
        server_status_check.start(channel)
        print(f"Monitoring server status for '{MINECRAFT_SERVER_ADDRESS}'.")

@tasks.loop(seconds=1)
async def server_status_check(channel):
    global previous_status, previous_players
    server = JavaServer.lookup(MINECRAFT_SERVER_ADDRESS)
    try:
        status = server.status()
        current_status = 'online'
        current_players = {player.name for player in status.players.sample} if status.players.sample else set()
        
        if previous_status != current_status:
            previous_status = current_status
            embed = discord.Embed(
                title="Minecraft Server Status",
                description=f"Server is now online with {status.players.online} players.",
                color=discord.Color.green()
            )
            await channel.send(embed=embed)
            print(f"Server is online with {status.players.online} players.")
        
        new_players = current_players - previous_players
        for player in new_players:
            skin_url = get_player_skin(player)
            embed = discord.Embed(
                title="Player Logged In",
                description=f"Player `{player}` has logged in.",
                color=discord.Color.blue()
            )
            if skin_url:
                embed.set_thumbnail(url=skin_url)
            await channel.send(embed=embed)
            print(f"Player `{player}` has logged in.")

        
        left_players = previous_players - current_players
        for player in left_players:
            embed = discord.Embed(
                title="Player Logged Out",
                description=f"Player `{player}` has logged out.",
                color=discord.Color.orange()
            )
            await channel.send(embed=embed)
            print(f"Player `{player}` has logged out.")

        
        previous_players = current_players

    except Exception as e:
        current_status = 'offline'
        if previous_status != current_status:
            previous_status = current_status
            embed = discord.Embed(
                title="Minecraft Server Status",
                description="Server is now offline.",
                color=discord.Color.red()
            )
            await channel.send(embed=embed)
            print(f"Server is offline. Exception: {e}")

@client.command(name='players')
async def players(ctx):
    server = JavaServer.lookup(MINECRAFT_SERVER_ADDRESS)
    try:
        status = server.status()
        players_list = [player.name for player in status.players.sample] if status.players.sample else []
        if players_list:
            embed = discord.Embed(
                title="Players Online",
                description='\n'.join(players_list),
                color=discord.Color.blue()
            )
        else:
            embed = discord.Embed(
                title="Players Online",
                description="No players online.",
                color=discord.Color.blue()
            )
        await ctx.send(embed=embed)
    except Exception as e:
        embed = discord.Embed(
            title="Error",
            description="Unable to fetch player list.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        print(f"Error fetching player list: {e}")

def get_player_skin(player_name):
    try:
        
        response = requests.get(f'https://api.mojang.com/users/profiles/minecraft/{player_name}')
        if response.status_code == 200:
            player_data = response.json()
            uuid = player_data['id']
            
            
            response = requests.get(f'https://sessionserver.mojang.com/session/minecraft/profile/{uuid}')
            if response.status_code == 200:
                profile_data = response.json()
                for property in profile_data['properties']:
                    if property['name'] == 'textures':
                        textures = json.loads(base64.b64decode(property['value']))
                        return textures['textures']['SKIN']['url']
    except Exception as e:
        print(f"Error retrieving skin for player {player_name}: {e}")
    return None

client.run(TOKEN)
