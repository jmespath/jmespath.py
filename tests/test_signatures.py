from tests import unittest

from jmespath import compat
from jmespath import exceptions
from jmespath import functions

class TestFunctionSignatures(unittest.TestCase):

	def setUp(self):
		self._functions = functions.Functions()

	def test_signature_with_monotype_argument(self):
		(function_name, signature) = self._make_test("_function_with_monotyped_arguments")
		self._functions._validate_arguments(['string'], signature, function_name)
		self.assertRaises(
			exceptions.ArityError, lambda :
			self._functions._validate_arguments([], signature, function_name)
		)

	def test_signature_with_optional_arguments(self):
		(function_name, signature) = self._make_test("_function_with_optional_arguments")
		self._functions._validate_arguments(['string'], signature, function_name)
		self._functions._validate_arguments(['string', 42], signature, function_name)
		self._functions._validate_arguments(['string', 43], signature, function_name)
		self.assertRaises(
			exceptions.ArityError, lambda :
			self._functions._validate_arguments([], signature, function_name)
		)
		self.assertRaises(
			exceptions.ArityError, lambda :
			self._functions._validate_arguments(['string', 42, 43, 44], signature, function_name)
		)

	def test_signature_with_variadic_arguments(self):
		(function_name, signature) = self._make_test("_function_with_variadic_arguments")
		self._functions._validate_arguments(['string', 'text1'], signature, function_name)
		self._functions._validate_arguments(['string', 'text1', 'text2'], signature, function_name)
		self.assertRaises(
			exceptions.VariadictArityError, lambda :
			self._functions._validate_arguments(['string'], signature, function_name)
		)

	def _make_test(self, funcName):
		for name, method in compat.get_methods(TestFunctionSignatures):
			print(name)
			if name != funcName:
				continue
			signature = getattr(method, 'signature', None)
			return (funcName, signature)
		return None

	## arg1 can only be of type 'string'
	## this signature supports testing simplified syntax
	## where 'type' is a string instead of an array of strings
	@functions.signature({'type': 'string'})
	def _function_with_monotyped_arguments(self, arg1):
		return None

	@functions.signature({'type': 'string'}, {'type': 'string', 'variadic': True})
	def _function_with_variadic_arguments(self, arg1, *arguments):
		return None

	@functions.signature({'type': 'string'}, {'type': 'number', 'optional': True}, {'type': 'number', 'optional': True})
	def _function_with_optional_arguments(self, arg1, opt1, opt2):
		return None


if __name__ == '__main__':
    unittest.main()