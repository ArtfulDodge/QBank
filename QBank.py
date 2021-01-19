#QBank.py
import os
import discord
import mysql.connector as mysql
from mysql.connector import Error
from dotenv import load_dotenv
from mcuuid.api import GetPlayerData
from exceptions import *

class QBank:

	def __init__(self):
		load_dotenv()
		try:
			self.db = mysql.connect(
				host = os.getenv('MYSQL_HOST'),
				user = os.getenv('MYSQL_USER'),
				passwd = os.getenv('MYSQL_PASSWORD'),
				auth_plugin = "mysql_native_password",
				database = "qbank"
			)
			print(self.db)
		except Error as e:
			print(f"The error '{e}' occurred")
	
		self.cursor = self.db.cursor()
		
		self.cursor.execute("SHOW TABLES")
		tables = self.cursor.fetchall()
		
		if not any("accounts" in s for s in tables):
			self.cursor.execute("CREATE TABLE accounts (account_id INT(11) NOT NULL AUTO_INCREMENT PRIMARY KEY, mc_uuid CHAR(36), mc_name VARCHAR(16), dc_name VARCHAR(32), dc_id VARCHAR(255), netherite_blocks INT UNSIGNED, netherite_ingots INT UNSIGNED, netherite_scrap INT UNSIGNED, diamond_blocks INT UNSIGNED, diamonds INT UNSIGNED)")
		
		if not any("transactions" in s for s in tables):
			self.cursor.execute("CREATE TABLE transactions (transaction_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY, transaction_type VARCHAR(10) NOT NULL, sender_account_id INT(11), recipient_account_id INT(11), netherite_blocks INT UNSIGNED, netherite_ingots INT UNSIGNED, netherite_scrap INT UNSIGNED, diamond_blocks INT UNSIGNED, diamonds INT UNSIGNED)")
		
	def account_exists(self, uuid):
		query = "SELECT account_id FROM accounts WHERE mc_uuid = %s"
		data = [uuid]
		self.cursor.execute(query, data)
		record = self.cursor.fetchone()
		if not record:
			return False
		return True
		
	def create_new_account(self, mc_name, dc_name, dc_id, n_blocks=0, n_ingots=0, n_scrap=0, d_blocks=0, d=0):
		
		mc_uuid = self.get_player_uuid(mc_name)
		if not self.account_exists(mc_uuid):
			query = "INSERT INTO accounts (mc_uuid, mc_name, dc_name, dc_id, netherite_blocks, netherite_ingots, netherite_scrap, diamond_blocks, diamonds) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
			values = (mc_uuid, mc_name, dc_name, dc_id, n_blocks, n_ingots, n_scrap, d_blocks, d)
			self.cursor.execute(query, values)
			self.db.commit()
			return True
		else:
			raise DuplicateAccountError(f"User {mc_name} already has an account")
		return False
		
	def deposit(self, mc_name, n_blocks=0, n_ingots=0, n_scrap=0, d_blocks=0, d=0):
		transaction_type = "deposit"
		uuid = self.get_player_uuid(mc_name)
		if self.account_exists(uuid):
			query = "SELECT account_id, netherite_blocks, netherite_ingots, netherite_scrap, diamond_blocks, diamonds FROM accounts WHERE mc_uuid = %s"
			data = [uuid]
			self.cursor.execute(query, data)
			record = self.cursor.fetchone()
			id = record[0]
			pre_n_blocks = record[1]
			pre_n_ingots = record[2]
			pre_n_scrap = record[3]
			pre_d_blocks = record[4]
			pre_d = record[5]
			
			self.create_transaction(transaction_type, recipient_id = id, net_blocks = n_blocks, net_ingots = n_ingots, net_scrap = n_scrap, dia_blocks = d_blocks, dia = d)
			
			d += pre_d
			while (d >= 9):
				d_blocks += 1
				d -= 9
			d_blocks += pre_d_blocks
			n_scrap += pre_n_scrap
			
			while (n_scrap >= 4):
				n_ingots += 1
				n_scrap -= 4
			
			n_ingots += pre_n_ingots
			
			while (n_ingots >= 9):
				n_blocks += 1
				n_ingots -= 9
			
			n_blocks += pre_n_blocks
			
			query = "UPDATE accounts SET netherite_blocks = %s, netherite_ingots = %s, netherite_scrap = %s, diamond_blocks = %s, diamonds = %s WHERE account_id = %s"
			data = (n_blocks, n_ingots, n_scrap, d_blocks, d, id)
			self.cursor.execute(query, data)
			self.db.commit()
		else:
			raise AccountNotFoundError(f"Found no account belonging to user {mc_name}")
	
	def withdraw(self, mc_name, n_blocks=0, n_ingots=0, n_scrap=0, d_blocks=0, d=0):
		transaction_type = "withdrawal"
		uuid = self.get_player_uuid(mc_name)
		if (self.account_exists(uuid)):
			query = "SELECT account_id, netherite_blocks, netherite_ingots, netherite_scrap, diamond_blocks, diamonds FROM accounts WHERE mc_uuid = %s"
			data = [uuid]
			self.cursor.execute(query, data)
			record = self.cursor.fetchone()
			id = record[0]
			pre_n_blocks = record[1]
			pre_n_ingots = record[2]
			pre_n_scrap = record[3]
			pre_d_blocks = record[4]
			pre_d = record[5]
			
			post_n_blocks = pre_n_blocks - n_blocks
			post_n_ingots = pre_n_ingots - n_ingots
			while post_n_ingots < 0:
				post_n_blocks -= 1
				post_n_ingots += 9
			post_n_scrap = pre_n_scrap - n_scrap
			while post_n_scrap < 0:
				post_n_ingots -= 1
				post_n_scrap += 4
			post_d_blocks = pre_d_blocks - d_blocks
			post_d = pre_d - d
			while post_d < 0:
				post_d_blocks -= 1
				post_d += 9
			
			if post_n_blocks < 0 or post_n_ingots < 0 or post_d_blocks < 0:
				raise InsufficientFundsError(f"{mc_name} has insufficient funds for the transaction")
			else:
				self.create_transaction(transaction_type, sender_id = id, net_blocks = n_blocks, net_ingots = n_ingots, net_scrap = n_scrap, dia_blocks = d_blocks, dia = d)
				query = "UPDATE accounts SET netherite_blocks = %s, netherite_ingots = %s, netherite_scrap = %s, diamond_blocks = %s, diamonds = %s WHERE account_id = %s"
				data = (post_n_blocks, post_n_ingots, post_n_scrap, post_d_blocks, post_d, id)
				self.cursor.execute(query, data)
				self.db.commit()
		else:
			raise AccountNotFoundError(f"Found no account belonging to user {mc_name}")
	
	def get_player_uuid(self, mc_name):
		player = GetPlayerData(mc_name)
		
		if player.valid:
			return player.uuid
		else:
			raise InvalidPlayerError(f"No UUID for player with name {mc_name}")
	
	def create_transaction(self, transaction_type, sender_id=None, recipient_id=None, net_blocks=0, net_ingots=0, net_scrap=0, dia_blocks=0, dia=0):
		query = "INSERT INTO transactions (transaction_type, sender_account_id, recipient_account_id, netherite_blocks, netherite_ingots, netherite_scrap, diamond_blocks, diamonds) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
		data = (transaction_type, sender_id, recipient_id, net_blocks, net_ingots, net_scrap, dia_blocks, dia)
		self.cursor.execute(query, data)
		self.db.commit()
			
	#end QBank
		
qb = QBank()
try:
	if qb.create_new_account(mc_name="Queueue_", dc_name="Queueue_#6969", dc_id="111301566463516672"):#, n_scrap=1, d_blocks=39, d=3):
		print("Success!")
	else:
		print("Failure!")
except DuplicateAccountError as e:
	print(e)

qb.deposit("Queueue_", n_blocks = 6, n_ingots = 6, n_scrap = 3, d_blocks = 5, d = 6)
qb.withdraw("Queueue_", n_blocks = 6, n_ingots = 6, n_scrap = 3, d_blocks = 5, d = 7)