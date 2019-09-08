import re
import discord
from discord.ext import commands


def is_hex_color_code(s: str):
    return bool(re.match('[a-fA-F0-9]{6}$', s))


class Colors(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['hex', 'colorme'])
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    async def color(self, ctx, hex_code):

        if not is_hex_color_code(hex_code):
            await ctx.send("Invalid hex code. Usage: `/color 44ff00`.")

        # Make sure we have guild space
        guild = ctx.message.guild
        if not (len(guild.roles) < 250):
            await ctx.send('No custom role slots left!')
            return

        prefix = self.bot.cfg['color-role-prefix']

        color = discord.Colour(int(hex_code, 16))
        new_role = await guild.create_role(name=f'{prefix} #{hex_code}', color=color)
        user = ctx.message.author

        # Unequip old colors
        for role in user.roles:
            if role.name.startswith(prefix):
                await user.remove_roles(role)

                # Delete if we're the last owner
                if len(role.members) < 2:
                    await role.delete()

        # Give new color
        try:
            await user.add_roles(new_role)
        except Exception as e:
            await ctx.send(f'Failed to assign new color: {e}')
        else:
            await ctx.message.add_reaction("✅")


def setup(bot):
    bot.add_cog(Colors(bot))
