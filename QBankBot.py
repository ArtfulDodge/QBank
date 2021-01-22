#QBankBot.py
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from QBank import QBank
from exceptions import *

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
MANAGER_ID = os.getenv('MANAGER_ID')
bot = commands.Bot(command_prefix='q!')
qb = QBank()

#suffixes for different currency denominations
suffixes = ["nb", "ni", "ns", "db", "d"]

def build_amount_list(args):
	result = [0,0,0,0,0]
	for i in range(len(args)):
		for suffix in suffixes:
			value = args[i]
			
			if value.endswith(suffix):
				value = value.removesuffix(suffix)
				result[suffixes.index(suffix)] += int(value)
	
	return result

def get_last_nonzero_index(amount):
	return [i for i, e in enumerate(amount) if e != 0][-1]

def get_amount_as_string(amount):
	result = ""
	last_nonzero = get_last_nonzero_index(amount)

	for i in range(5):
		if amount[i] != 0:
			if i < last_nonzero:
				result += str(amount[i]) + suffixes[i] + ", "
			else:
				result += str(amount[i]) + suffixes[i]
	
	return result


@bot.event
async def on_ready():
	print(f'{bot.user} has connected to Discord!')
	await bot.change_presence(activity=discord.Game(name="q!help"))
	
@bot.command(help='Shows a message explaining how to denote currency')
async def currencyhelp(ctx):
	await ctx.send("```This bot distinguishes between different currencies by using a suffix appended to the amount you give it:\n"
			 "nb = netherite blocks\nni = netherite ingots\nns = netherite scrap\ndb = diamond blocks\nd = diamonds\n\n"
			 "Example: To pay Queueue_ a total amount of 10 netherite blocks, 5 netherite ingots, 1 netherite scrap, 5 diamond blocks, and 2 diamonds in a command you would type:\n"
			 "q!pay Queueue_ 10nb 5ni 1ns 5db 2d\n\n"
			 "You don't have to denote every currency denomination, it will be assumed that any denomination you don't specify is 0. For instance:\n"
			 "q!pay Queueue_ 10ns\n"
			 "will pay Queueue_ 10 netherite scrap, and ignore all other currency denominations\n\n"
			 "Amounts that are high enough will automatically be converted to the next highest denomination.\n"
			 "For example, 15ni will be automatically converted into 1 netherite block and 6 netherite ingots\n"
			 "This automatic conversion currently doesn't happen between diamonds and netherite, but eventually the bank will offer a set exchange rate for this.```")

@bot.command(help='Creates a new account for you\nUsage: q!createaccount {your Minecraft username}')
async def createaccount(ctx, minecraft_username):
	mc_name = minecraft_username
	dc_id = ctx.message.author.id
	try:
		qb.create_new_account(mc_name, dc_id)
		await ctx.send(f"Created a new account for user {mc_name}")
	except DuplicateAccountError as e:
		await ctx.send(e)

@bot.command(help='Checks your balance for you')
async def checkbalance(ctx):
	dc_id = ctx.message.author.id
	
	try:
		balance = get_amount_as_string(qb.check_balance_dc_id(dc_id))
		await ctx.send(f"Your balance is:\n```{balance}```")
	except Exception as e:
		await ctx.send(e)

@bot.command(help='DMs Queueue_ that you would like to make a deposit\nUsage: q!requestdeposit {amount}')
async def requestdeposit(ctx, *args):
	dc_id = ctx.message.author.id
	amount = build_amount_list(args)
	amount_string = get_amount_as_string(amount)
	
	try:
		mc_name = qb.get_player_name(dc_id)
		manager = await bot.fetch_user(int(MANAGER_ID))
		await manager.send(f"**{mc_name}** requested a **DEPOSIT** of ```{amount_string}```\n ")
		await ctx.send("Your request has been sent to the bank manager.")
	except Exception as e:
		await ctx.send(e)

@bot.command(help='DMs Queueue_ that you would like to make a withdrawal\nUsage: q!requestwithdrawal {amount}')
async def requestwithdrawal(ctx, *args):
	dc_id = ctx.message.author.id
	amount = build_amount_list(args)
	amount_string = get_amount_as_string(amount)
	
	try:
		mc_name = qb.get_player_name(dc_id)
		manager = await bot.fetch_user(int(MANAGER_ID))
		await manager.send(f"**{mc_name}** requested a **WITHDRAWAL** of: ```{amount_string}```\n ")
		await ctx.send("Your request has been sent to the bank manager.")
	except Exception as e:
		await ctx.send(e)

@bot.command(help="Pays another player\nUsage: q!pay {Recipient's Minecraft username} {amount}")
async def pay(ctx, *args):
	sender_id = ctx.message.author.id
	recipient_name = args[0]
	amount = build_amount_list(args[1:])
	amount_string = get_amount_as_string(amount)
	
	try:
		qb.client_transfer(sender_id, recipient_name, amount)
		await ctx.send(f"**{amount_string}** has been transfered from your account to {recipient_name}'s account")
		sender_name = qb.get_player_name(sender_id)
		recipient_dc_id = qb.get_dc_id_from_username(recipient_name)
		recipient = await bot.fetch_user(int(recipient_dc_id))
		await recipient.send(f"{sender_name} has paid you {amount_string}!")
	except Exception as e:
		await ctx.send(e)
	

@bot.command(help='Can only be used by Queueue_')
@commands.is_owner()
async def createaccountwithbalance(ctx, *args):
	mc_name = args[0]
	dc_id = args[1]
	
	starting_balance = build_amount_list(args[2:])
				
	try:
		qb.create_new_account(mc_name, dc_id, starting_balance)
		await ctx.send(f"Created a new account for user {mc_name}")
	except DuplicateAccountError as e:
		await ctx.send(e)

@bot.command(help='Can only be used by Queueue_')
@commands.is_owner()
async def deposit(ctx, *args):
	mc_name = args[0]
	amount = build_amount_list(args[1:])
	
	try:
		qb.deposit(mc_name, amount)
		amount_string = get_amount_as_string(amount)
		await ctx.send(f"Deposited **{amount_string}** into the account belonging to {mc_name}")
	except Exception as e:
		await ctx.send(e)

@bot.command(help='Can only be used by Queueue_')
@commands.is_owner()
async def withdraw(ctx, *args):
	mc_name = args[0]
	amount = build_amount_list(args[1:])
	
	try:
		qb.withdraw(mc_name, amount)
		amount_string = get_amount_as_string(amount)
		await ctx.send(f"Withdrew **{amount_string}** from the account belonging to {mc_name}")
	except Exception as e:
		await ctx.send(e)

@bot.command(help='Can only be used by Queueue_')
@commands.is_owner()
async def transferfunds(ctx, *args):
	sender_name = args[0]
	recipient_name = args[1]
	amount = build_amount_list(args[2:])
	amount_string = get_amount_as_string(amount)
	
	try:
		cb.manager_transfer(sender_name, recipient_name, amount)
		await ctx.send(f"**{amount_string}** has been transfered from {sender_name}'s account to {recipient_name}'s account")
	except Exception as e:
		await ctx.send(e)
	
bot.run(TOKEN)