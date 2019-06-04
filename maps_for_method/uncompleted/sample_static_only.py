from types import MappingProxyType
from typing import Callable


class AlreadyExistsKeyInMethodsMapper(RuntimeError):
    """Exception for rewriting existed value."""
    def __init__(self, key):
        self.__key = key

    def __str__(self) -> str:
        return f'\'{self.__key}\' is an already-existed key.'


class MethodsMapper(type):
    """
    Metaclass for registering keys and staticmethod.
    """
    __keys_meths = {}

    def __new__(cls, name, bases, dict_):
        self = type.__new__(cls, name, bases, dict_)
        self._metamaps = cls.__keys_meths
        return self

    @classmethod
    def register(cls, key) -> Callable:
        """
        Decorator for registering a key and a staticmethod.
        """
        def deco(method):
            if key in cls.__keys_meths:
                raise AlreadyExistsKeyInMethodsMapper(key)
            cls.__keys_meths[key] = method
            return method
        return deco


class SampleMethodsContainer(metaclass=MethodsMapper):
    """
    sample concrete class.
    """
    def __init__(self):
        self.__keys_meths = MappingProxyType(self._metamaps)

    @property
    def maps(self) -> MappingProxyType:
        """
        Returns assosiative array of keys and methods.
        """
        return self.__keys_meths

    @staticmethod
    @MethodsMapper.register('a')
    def foo(additional) -> str:
        return f'{additional}_foo'

    @staticmethod
    @MethodsMapper.register('b')
    def bar(additional) -> str:
        return f'{additional}_bar'


container = SampleMethodsContainer()
print(container.maps['a']('spam'))  # >>> 'spam_foo'
print(container.maps['b']('ham'))  # >>> 'ham_bar'


class AnotherContainer(metaclass=MethodsMapper):
    def __init__(self):
        self.__keys_meths = MappingProxyType(self._metamaps)

    @property
    def maps(self) -> MappingProxyType:
        """
        Returns assosiative array of keys and methods.
        """
        return self.__keys_meths

    @staticmethod
    @MethodsMapper.register('a')
    def baz(additional) -> str:
        return f'{additional}_baz'


# ERROR!
another = AnotherContainer()
print(another.maps['a']('spam'))  # >>> 'spam_baz'
