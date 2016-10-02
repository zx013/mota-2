import types
import importlib


def inst_to_dict(instance):
	dictionary = {}
	module_name = instance.__module__
	dictionary['__module__'] = module_name
	module = importlib.import_module(module_name)

	for class_name, class_type in vars(module).items():
		if isinstance(instance, class_type):
			break
	dictionary['__name__'] = class_name

	for key in dir(instance):
		if key[:2] == '__' and key[-2:] == '__':
			continue
		val = getattr(instance, key)
		if hasattr(val, '__call__'):
			continue
		dictionary[key] = val

	return dictionary

def dict_to_inst(dictionary):
	module_name = dictionary['__module__']

	module = importlib.import_module(module_name)
	for class_name, class_type in vars(module).items():
		if dictionary['__name__'] == class_name:
			break

	instance = class_type()
	for key, val in dictionary.items():
		if key[:2] == '__' and key[-2:] == '__':
			continue
		setattr(instance, key, val)

	return instance


def adjust_iter(iteration):
	dictionary = {}
	dictionary['__type__'] = type(iteration)
	if isinstance(iteration, list):
		dictionary['__value__'] = list(iteration)
	elif isinstance(iteration, tuple):
		dictionary['__value__'] = tuple(iteration)
	elif isinstance(iteration, dict):
		dictionary.update(iteration)
	elif type(iteration) == types.InstanceType:
		dictionary.update(inst_to_dict(iteration))
	else:
		dictionary['__value__'] = iteration
	return dictionary

class Save:
	@staticmethod
	def save():
		pass

	@staticmethod
	def load():
		pass


class A:
	a = 1
	def __init__(self):
		self.b = 2

	def c(self):
		self.a = 3
		self.b = 4


if __name__ == '__main__':
	a = A()
	a.c()
	d = inst_to_dict(a)
	i = dict_to_inst(d)
	print d, dir(i), i.a, i.b
	print adjust_iter(range(10))
	print adjust_iter(tuple(range(10)))
	print adjust_iter(a)
	print adjust_iter(d)
	print adjust_iter(1)