class AccountNotFoundError(Exception):
	pass

class DuplicateAccountError(Exception):
	pass

class InsufficientFundsError(Exception):
	pass

class InvalidPlayerError(Exception):
	pass

class NoTransactionsError(Exception):
	pass

class MultipleLoansError(Exception):
	pass