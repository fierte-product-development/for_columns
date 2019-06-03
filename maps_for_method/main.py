from types import MappingProxyType, MethodType
from typing import Callable
from inspect import signature


class MethodWrapper:
    """
    Wrapper class for methods of class attributes.

    Calls with passing `instance` to unwrap method.
    """
    # see below to know what is `types.MethodType` and descripter.
    # https://docs.python.org/ja/3/howto/descriptor.html
    # https://docs.python.org/ja/3/library/types.html?highlight=types#types.MethodType
    def __init__(self, method):
        self.__method = method
        params = tuple(signature(method).parameters)
        self.__is_instmeth = bool(params) and params[0] == 'self'
        self.__is_clsmeth = bool(params) and params[0] == 'cls'
        self.__is_statmeth = not any((self.__is_clsmeth, self.__is_instmeth))

    def __call__(self, instance) -> Callable:
        """
        Unwraps method.
        """
        if self.__is_instmeth:
            unwrapped = MethodType(self.__method, instance)
        elif self.__is_clsmeth:
            unwrapped = MethodType(self.__method, type(instance))
        elif self.__is_statmeth:
            unwrapped = self.__method
        return unwrapped


class AlreadyExistsKeyInMethodsMapper(RuntimeError):
    """Exception for rewriting existed value."""
    def __init__(self, key):
        self.__key = key

    def __str__(self) -> str:
        return f'\'{self.__key}\' is an already-existed key.'


class MethodsMapper(type):
    """
    Abstract metaclass for registering keys and methods.

    MUST be one-subclassed-this for one-container-class.

    Example:
    ---
    .. code-block:: python

        class SubclassedMethodMapper(MethodsMapper)
            @classmethod
            def register_sample(cls, key) -> Callable:
                def deco(method):
                    return cls._create_decorated_func(key, method)
                return deco

        class SampleMethodContainer(metaclass=SubclassedMethodMapper):
            pass  # methods with decorators shall be implemented.

        # Below case, `TypeError` raises!
        class AnotherMethodContainer(metaclass=SubclassedMethodMapper):
            pass
    """
    @classmethod
    def __init_subclass__(cls):
        """
        Defines private attributes.
        """
        cls.__usage = set()
        cls.__maps = {}

    def __new__(cls, name, bases, dict_) -> type:
        self = type.__new__(cls, name, bases, dict_)
        cls.__usage.add(self)
        if len(cls.__usage) > 1:
            raise TypeError(
                f'\'{cls.__name__}\' has already used in another class.'
            )
        self._get_metamaps = cls.__get_modified_maps
        return self

    @classmethod
    def _create_decorated_func(cls, key, method) -> Callable:
        """
        Internal function.
        Returns `method` itself after registering `key` and `method` to
        inner assosiative array.

        Example:
        ---
        .. code-block:: python

            class SubclassedMethodMapper(MethodsMapper)
                @classmethod
                def register_sample(cls, key) -> Callable:
                    def deco(method):
                        return cls._create_decorated_func(key, method)
                    return deco

            class SampleMethodContainer(metaclass=SubclassedMethodMapper):
                @register_sample('foo')
                def egg(self):
                    pass
        """
        try:
            is_existed_key = key in cls.__maps
        except AttributeError:
            raise TypeError(f'{cls.__name__} cannot instantiate.')
        if is_existed_key:
            raise AlreadyExistsKeyInMethodsMapper(key)
        cls.__maps[key] = MethodWrapper(method)
        return method

    @classmethod
    def __get_modified_maps(cls, instance) -> MappingProxyType:
        """
        Returns accsociative array of keys and methods.
        """
        return MappingProxyType(
            {key: meth_wrap(instance) for key, meth_wrap in cls.__maps.items()}
        )
