# IDK Discord bot
# Author: Nathan Strong
# Date: Oct 29, 2021
# Description: As requested by one of my friends, this bot will (on entering the server)
# ask for a channel to bind itself to. Once it has been given one, it will track the 
# number of times the phrase "idk" has been said in the channel and will display that 
# count any time a user types the command "!idk count"

import discord, os, sys, time, signal, asyncio
from dotenv import load_dotenv

ISTEST = os.path.isfile("./is_test.txt")

# Functions for getting/saving data
def get_data(format_fn = lambda t:[int(s) for s in t]):
    filename = "channels_test.txt" if ISTEST else "channels.txt"
    file = open(filename, "r")
    data = {}
    for line in file:
        print(line)
        line_list = format_fn(line.split(":"))
        data[line_list[0]] = line_list[1]
    
    return data

def save_data(data, format_fn = lambda t:[str(i) for i in t]):
    filename = "channels_test.txt" if ISTEST else "channels.txt"
    file = open(filename, "w")
    for item in data.items():
        file.write(":".join(format_fn(item)))
        file.write("\n")

# Get the command arguments out of a string, grouping arguments in quotation marks
def get_args(arg_string):
    # Initialize some variables
    possible_arg_list = arg_string.split()
    arg_list = []
    current_arg = ""

    # Go through the list, collecting all arguments in quotation marks into single arguments
    # For instance, hello "world hello" world should become ["hello", "world hello", "world"]
    for possible_arg in possible_arg_list:
        if current_arg != "":
            current_arg = current_arg + " " + possible_arg
            if possible_arg.endswith("\""):
                arg_list.append(current_arg[:-1])
                current_arg = ""
        elif possible_arg.startswith("\""):
            current_arg = possible_arg[1:]
        else:
            arg_list.append(possible_arg)
    
    return arg_list

# Returns timestamp (hour:minute:second)
def timestamp():
    t = time.localtime()
    # time.localtime is off by 5 hours for some reason... guess I need to adjust that...
    return f"{(t.tm_hour+5)%24:02d}:{t.tm_min:02d}:{t.tm_sec:02d}"

class CommandData:
    def __init__(self, fn, desc, syntax, private):
        self.fn = fn
        self.desc = desc
        self.private = private
        self.syntax = syntax

class PermsClass:
    def __init__(self):
        self.none = "anyone"
        self.admin = "a mod"
        self.owner = "the owner of this bot"

    def verify_perms(self, user, perms, channel, owner):
        if perms == self.none or user.id == owner:
            return True
        elif user.permissions_in(channel).administrator:
            if perms == self.admin:
                return True
        return False
Perms = PermsClass()

# Create a decorator that knows which functions are commands in a given object
all_commands = {}
visible_commands = {}
def command(name, description, syntax=None, private=False, perms_needed=Perms.none):
    if syntax == None:
        syntax = "{}"+name
    def command_decorator(func):
        async def wrapper(bot, args, ctx):
            if Perms.verify_perms(ctx.author, perms_needed, ctx.channel, bot.owner):
                await func(bot, args, ctx)
            else:
                await ctx.channel.send(f"Insufficient permissions. You need to be {perms_needed} to run this command.")
        
        if name in all_commands.keys():
            raise Exception(f"The command name '{name}' was used more than once")
        all_commands[name] = CommandData(wrapper, description, syntax, private)

        return wrapper

    return command_decorator

class IDKBot(discord.Client):
    def __init__(self, prefix="!idk ", owner=None, **base_args):
        # Run base class __init__ function using any arguments passed in
        super().__init__(**base_args)

        # Set prefix, commands, owner
        self.prefix = prefix
        self.commands = all_commands
        self.owner = owner

        # Generate milestones. Should be [100,200,300...900,1000,2000...9000000]. The bot will alert the channel whenever a milestone is hit.

        # m is [100,1000,10000...], mx gives m with each item multiplied by n, and milestones_2d has [[100,1000,10000...],[200,2000,20000...]...[900,9000...]]
        m = [10**n for n in range(2,7)]
        mx = lambda n:[n*i for i in m]
        milestones_2d = [mx(i+1) for i in range(9)]

        # For each sublist in milestones_2d, append it to self.milestones. Then sort it, because why not.
        self.milestones = []
        for sub_list in milestones_2d:
            self.milestones += sub_list
        
        self.milestones.sort()

        # Done generating milestones

        # Get dict of stored channels
        self.channels = {
            int(key):int(val) for (key,val) in get_data().items()
        }
    
    async def get_initial_idks(self, channel):
        print(channel)
        async with channel.typing():
            messages = await channel.history(limit = None).flatten()

            idkcount = 0
            for msg in messages:
                if msg.content.lower() == "idk":
                    idkcount += 1
        
        return idkcount

    async def on_ready(self):
        # State that the bot has logged on
        
        print(f"{self.user} connected to discord at {timestamp()}")
        
        if len(self.guilds) == 0:
            return

        # For each server we have a channel for, get the idks in that channel and store them
        self.idk_counts = {}
        for (server, channel) in self.channels.items():
            print(server)
            self.idk_counts[channel] = await self.get_initial_idks(self.get_channel(channel))

        await self.get_user(self.owner).send("I'm online now!")

    async def on_guild_join(self, guild):
        # Alert both the console and the joined server that the bot has joined.
        print(f"Joined guild {guild.name}")
        await guild.system_channel.send("""Everyone welcome IDKBot, the bot that does something, idk.
Run !idk help to get the commands allowed by this bot.
Also, please give me a channel to run in by typing !idk bind in that channel (You need to be an admin to do this).""")
    
    async def on_message(self, message):
        # Log the message in the console
        if message.channel.type == discord.ChannelType.private:
            print(f"{message.author} ({timestamp()} dming {message.channel.recipient if message.author.id==self.user.id else self.user}): {message.content}")
        else:
            print(f"{message.author} ({timestamp()} in {message.guild.name}#{message.channel.name}): {message.content}")
        
        # If the user sent IDK in the bound IDK channel, increment the respective counter. Then announce any milestones.
        if message.content.lower() == "idk" and message.channel.id == self.channels[message.guild.id]:
            self.idk_counts[message.channel.id] += 1
            if self.idk_counts[message.channel.id] in self.milestones:
               await message.channel.send(f"Milestone reached: {self.idk_counts[message.channel.id]} IDKs!")
        
        # If the message was sent by the bot itself or if it doesn't have the required prefix, return (since the message is not a command)
        if message.author == self.user:
            return

        if not message.content.startswith(self.prefix):
            return
        
        # Get the necessary command details, then execute the requested command if it is found.
        command = get_args(message.content[len(self.prefix):])
        command_name = command[0]
        command_args = command[1:]

        if command_name in self.commands.keys():
            await self.commands[command_name].fn(self, command_args, message)
        else:
            await message.channel.send(f"Unknown command '{command_name}'. Try '{self.prefix}help' for a list of available commands.")

    @command("bind", "Sets the channel this bot will listen to. Any previous channels will now no longer work. Requires admin permissions on this server.", perms_needed=Perms.admin)
    async def bind(self, args, ctx):
        self.channels[ctx.guild.id] = ctx.channel.id
        self.idk_counts[ctx.channel.id] = await self.get_initial_idks(ctx.channel)
        await ctx.channel.send(f"Done binding to channel, found {self.idk_counts[ctx.channel.id]} previous IDKs! Happy IDKing!")
    
    @command("count", "Gives the number of times IDK has been said in the given channel")
    async def count(self, args, ctx):
        if ctx.channel.id not in self.channels.values():
            await ctx.channel.send("Either this is the wrong channel for IDKs, or the channel for IDKs has not been set (This can be done with '!idk bind' if you are an admin).")
        else:
            await ctx.channel.send(f"IDK has been said {self.idk_counts[ctx.channel.id]} times in this channel.")
    
    @command("refresh","Refreshes the IDK count (run this command if some IDKs have been deleted)")
    async def refresh_count(self, args, ctx):
        await self.get_initial_idks(ctx.channel)
        await ctx.channel.send(f"Refreshed, the new IDK count is {self.idk_counts[ctx.channel.id]}")
    
    @command("spam_idks","Has the bot send messages containing 'idk', one per second for a minute")
    async def spam(self, args, ctx):
        for i in range(60):
            await ctx.channel.send("idk")
            time.sleep(1)
    
    @command("help", "Sends this message")
    async def list_commands(self, args, ctx):
        msg = "List of available commands:\n\n"
        for name, cmd in all_commands.items():
            if not cmd.private:
                msg = msg + f"""{" ".join(name.capitalize().split("_"))}:
  -Description: {cmd.desc}.
  -Syntax: {cmd.syntax.format(self.prefix)}
                
"""
        await ctx.channel.send(msg)
    
    @command("stop", "Takes the bot offline. Only usable by the creator of this bot", private=True, perms_needed=Perms.owner)
    async def end(self, args, ctx):
        # Save channel data to file
        save_data(self.channels)

        # Go offline, end program
        await self.get_user(self.owner).send("Stop command ran. Exiting.")
        await ctx.channel.send("Going offline.")
        await self.change_presence(status=discord.Status.offline)
        sys.exit(f"Stop command run by {ctx.author}, bot offline. This is NOT an error.")

    # What to do when the program is supposed to stop. Similar to stop command.
    async def term(self, signum, stack):
        print("stop signal recieved")
        await self.get_user(self.owner).send(f"Recived signal {signal.Signals(signum).name}. Saving data and exiting.")
        print("sent message")
        save_data(self.channels)
        print("saved data, going offline")
        await self.change_presence(status=discord.Status.offline)
        self.loop.stop()

# Main function
def main():
    # Get environment vars
    if 'token' not in os.environ.keys():
        load_dotenv()
    TOKEN = os.environ['token']
    ADMIN = int(os.environ['owner'])

    # Set intents
    intents = discord.Intents.default()
    intents.members = True


    # Create and run client
    client = IDKBot(
        intents = intents, owner = ADMIN, prefix = ("!t " if ISTEST else "!idk ")
    )

    # Setup SIGTERM to send shutdown message
    signal.signal(signal.SIGTERM, lambda *args: asyncio.create_task(client.term(*args)))

    if ISTEST and os.name=='nt':
        print("SIGINT accepted")
        signal.signal(signal.SIGINT, lambda *args: asyncio.create_task(client.term(*args)))

    client.run(TOKEN)

if __name__ == "__main__":
    main()
