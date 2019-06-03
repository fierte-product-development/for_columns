from main import MethodsMapper
from types import MappingProxyType
from typing import Callable


class SampleMapper(MethodsMapper):
    @classmethod
    def register(cls, key) -> Callable:
        """
        Decorator for registering a key and a method.
        """
        def deco(method):
            return cls._create_decorated_func(key, method)
        return deco


class SampleMethodsContainer(metaclass=SampleMapper):
    """
    sample concrete class.
    """
    sample_cls_attr = 'cls sample'

    def __init__(self):
        self.__frozen_maps = MappingProxyType(self._get_metamaps(self))
        self.sample_inst_attrs = 'inst sample'

    @property
    def maps(self) -> MappingProxyType:
        """
        Returns assosiative array of keys and methods.
        """
        return self.__frozen_maps

    @staticmethod
    @SampleMapper.register('a')
    def foo(additional) -> str:
        return f'{additional}_foo'

    @staticmethod
    @SampleMapper.register('b')
    def bar(additional) -> str:
        return f'{additional}_bar'

    @SampleMapper.register('c')
    def jugem(self) -> str:
        return f'{self.sample_inst_attrs}, {self.sample_cls_attr}'

    @SampleMapper.register('d')
    def gokoo(self) -> str:
        return 'gokoo'

    @classmethod
    @SampleMapper.register('e')
    def suri(cls) -> str:
        return cls.sample_cls_attr


# tests
container = SampleMethodsContainer()
assert container.maps['a'] == container.foo
assert container.maps['a']('spam') \
    == container.foo('spam') \
    == 'spam_foo'  # noqa
assert container.maps['b'] == container.bar
assert container.maps['b']('ham') \
    == container.bar('ham') \
    == 'ham_bar'  # noqa
assert container.maps['c'] == container.jugem
assert container.maps['c']() \
    == container.jugem() \
    == 'inst sample, cls sample'  # noqa
assert container.maps['d'] == container.gokoo
assert container.maps['d']() \
    == container.gokoo() \
    == 'gokoo'  # noqa
assert container.maps['e'] == container.suri
assert container.maps['e']() \
    == container.suri() \
    == 'cls sample'  # noqa


class AnotherMapper(MethodsMapper):
    __case_a = []
    __case_b = []

    def __init__(self, *args):
        self._case_a = tuple(self.__case_a)
        self._case_b = tuple(self.__case_b)

    @classmethod
    def register_a(cls, key) -> Callable:
        def deco(method):
            cls.__case_a.append(key)
            return cls._create_decorated_func(key, method)
        return deco

    @classmethod
    def register_b(cls, key) -> Callable:
        def deco(method):
            cls.__case_b.append(key)
            return cls._create_decorated_func(key, method)
        return deco


class AnotherSample(metaclass=AnotherMapper):
    def __init__(self):
        metamap = self._get_metamaps(self)
        self.__a_maps = MappingProxyType(
            {k: v for k, v in metamap.items() if k in self._case_a}
        )
        self.__b_maps = MappingProxyType(
            {k: v for k, v in metamap.items() if k in self._case_b}
        )

    @AnotherMapper.register_a('x')
    def hoge(self):
        return 'hoge'

    @AnotherMapper.register_b('y')
    def fuga(self):
        return 'fuga'

    @property
    def a_maps(self):
        return self.__a_maps

    @property
    def b_maps(self):
        return self.__b_maps


another = AnotherSample()
assert another.a_maps['x'] == another.hoge
assert another.a_maps['x']() \
    == another.hoge() \
    == 'hoge'  # noqa
assert another.b_maps['y'] == another.fuga
assert another.b_maps['y']() \
    == another.fuga() \
    == 'fuga'  # noqa
