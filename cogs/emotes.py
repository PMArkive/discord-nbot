import re

import discord
from aiohttp import ClientSession
from discord import HTTPException
from discord.ext import commands
from pymongo.errors import DuplicateKeyError

INVISIBLE_CHAR = '\u17B5'
EMOTE_PATTERN = re.compile(r'\$([^\s$]+)')


class Emotes(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.emotedb = bot.db.emotes
        self.session = ClientSession()

    @commands.Cog.listener()
    async def on_message(self, message):

        if message.author.bot:
            return

        prefixed = EMOTE_PATTERN.findall(message.content)
        to_delete = []

        pipe = [
            {'$match': {'name': {'$in': prefixed}}},
            {'$project': {'name': 1, 'url': 1, 'length': {'$strLenCP': '$name'}}},
            {'$sort': {'length': -1}}
        ]

        async for doc in self.emotedb.aggregate(pipeline=pipe):
            name = doc['name']
            emote = await self.create_emote_from_url(message.channel.guild, name, doc['url'])
            if emote:
                to_delete.append(emote)
                message.content = message.content.replace(f"${name}", str(emote))

        if to_delete:
            to_delete.append(message)

            sent = await self.impersonate(message.author, message.content, message.channel)
            if sent:
                for trash in to_delete:
                    await trash.delete()

    async def create_emote_from_url(self, guild, name: str, url: str):
        async with self.session.get(url) as response:
            image_bytes = await response.read()
            try:
                emote = await guild.create_custom_emoji(name=name, image=image_bytes)
            except HTTPException as e:
                pass
            else:
                return emote

    @commands.command()
    async def add(self, ctx, name, url):
        try:
            emote = await self.create_emote_from_url(ctx.guild, name, url)
        except discord.HTTPException as e:
            await ctx.send(e)
        else:
            try:
                await self.bot.db.emotes.insert_one({
                    'owner': ctx.author.id,
                    'name': name,
                    'url': str(emote.url)
                })
            except DuplicateKeyError:
                await ctx.send(f'Emote with that name already exists')
            else:
                await ctx.send(f'Added emote `${name}`')
            finally:
                await emote.delete()

    @commands.command()
    async def remove(self, ctx, name):
        doc = await self.bot.db.emotes.find_one_and_delete({'name': name, ctx.author: ctx.author.id})
        await ctx.send(doc)

    async def impersonate(self, member: discord.Member, message: str, channel: discord.TextChannel):
        """Post a webhook that looks like a message sent by the user."""

        # Webhook usernames require at least 2 characters
        username = member.display_name.ljust(2, INVISIBLE_CHAR)

        # webhook = discord.utils.find(lambda m: m.user == self.bot.user, channel.guild.webooks())

        our_webhook = None
        webhooks = await channel.webhooks()
        for webhook in webhooks:
            if webhook.user == self.bot.user:
                our_webhook = webhook

        if not our_webhook:
            our_webhook = await channel.create_webhook(name='NBot')

        message = await our_webhook.send(
            username=username,
            content=message,
            avatar_url=member.avatar_url,
            wait=True
        )

        return message


def setup(bot):
    bot.add_cog(Emotes(bot))





