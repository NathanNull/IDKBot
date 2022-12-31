import discord, time, dotenv, os, json, sys
from discord.ext import commands

dotenv.load_dotenv()
TOKEN = os.environ['token']
OWNER = int(os.environ['owner'])

def get_data():
    with open('bound_channels.json') as file:
        data = json.load(file)
    return data

def save_data(data):
    with open('bound_channels.json', 'w') as file:
        json.dump(data, file)

class IDKBot(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot

        # m is [100,1000,10000...], mx gives m with each item multiplied by n, and
        # milestones_2d has [[100,1000,10000...],[200,2000,20000...]...[900,9000...]]
        m = [10**n for n in range(2,7)]
        mx = lambda n:[n*i for i in m]
        milestones_2d = [mx(i) for i in range(1,10)]

        # For each sublist in milestones_2d, append it to self.milestones. Then sort it, because why not.
        self.milestones = []
        for sub_list in milestones_2d:
            self.milestones += sub_list
        
        self.milestones.sort()

        # Get dict of stored channels
        self.channels = {
            int(key):int(val) for (key,val) in get_data().items()
        }
    
    async def count_idks(self, channel: discord.TextChannel):
        async with channel.typing():
            messages = await channel.history(limit = None).flatten()

            idkcount = 0
            for msg in messages:
                if msg.content.lower() == "idk":
                    idkcount += 1
        
        return idkcount

    @discord.slash_command()
    @discord.default_permissions(manage_channels=True)
    async def bind(self, ctx: discord.ApplicationContext):
        self.channels[ctx.guild_id] = ctx.channel_id
        self.idk_counts[ctx.channel_id] = await self.count_idks(ctx.channel)
        await ctx.respond(f"Done binding to channel, found {self.idk_counts[ctx.channel.id]} previous IDKs! Happy IDKing!")

    @discord.slash_command()
    async def count(self, ctx: discord.ApplicationContext):
        if ctx.channel_id not in self.channels.values():
            await ctx.respond("Either this is the wrong channel for IDKs, or the channel for IDKs has not been set (This can be done with '!idk bind' if you are an admin).")
        else:
            await ctx.respond(f"IDK has been said {self.idk_counts[ctx.channel_id]} times in this channel.")

    @discord.slash_command()
    async def refresh(self, ctx: discord.ApplicationContext):
        self.idk_counts[ctx.channel_id] = await self.count_idks(ctx.channel)
        await ctx.respond(f"Refreshed, the new IDK count is {self.idk_counts[ctx.channel_id]}")

    @discord.slash_command()
    async def spam_idks(self, ctx: discord.ApplicationContext, *, num: int):
        await ctx.respond("idk")
        for _ in range(59):
            await ctx.channel.send("idk")
            time.sleep(1)
    
    @discord.slash_command(checks=[lambda ctx: ctx.author.id==OWNER])
    async def stop(self, ctx: discord.ApplicationContext):
        self.save()

        # Go offline, end program
        await ctx.author.send("Stop command ran. Exiting.")
        await ctx.respond("Going offline.")
        await self.bot.change_presence(status=discord.Status.offline)
        sys.exit(f"> > > > Stop command run by {ctx.author}, bot offline. This is NOT an error.")

    def save(self):
        # Save channel data to file
        save_data(self.channels)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Print the message
        if message.channel.type == discord.ChannelType.private:
            print(message.channel.recipient)
            chstr = f"(dming {message.channel.recipient if message.author.id==self.bot.user.id else self.bot.user})"
        else:
            chstr = f"(in {message.guild.name}#{message.channel.name})"
        print(f"{message.author} {chstr}: {message.content}")

        # If the user sent IDK in the bound IDK channel, increment the respective counter. Then announce any milestones.
        if message.content.lower() == "idk" and message.channel.id == self.channels[message.guild.id]:
            self.idk_counts[message.channel.id] += 1
            if self.idk_counts[message.channel.id] in self.milestones:
                await message.channel.send(f"Milestone reached: {self.idk_counts[message.channel.id]} IDKs!")

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{self.bot.user} connected to discord.")

        if len(self.bot.guilds) == 0:
            return
        
        self.idk_counts = {}
        for (server, channel) in self.channels.items():
            self.idk_counts[channel] = await self.count_idks(self.bot.get_channel(channel))
        
        await self.bot.get_user(OWNER).send("I'm online now!")
    
    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        print(f"Joined guild {guild.name}")
        await guild.system_channel.send("""Everyone welcome IDKBot, the bot that does something, idk.
Run !idk help to get the commands allowed by this bot.
Also, please give me a channel to run in by typing !idk bind in that channel (You need to be an admin to do this).""")

def main():
    intents = discord.Intents.all()
    bot = commands.Bot(intents=intents)
    bot.add_cog(IDKBot(bot))
    try:
        bot.run(TOKEN)
    except KeyboardInterrupt:
        bot.get_cog('IDKBot').save()

if __name__ == '__main__':
    main()