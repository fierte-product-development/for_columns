Pythonのメソッドにエイリアスを設定する
===

# きっかけ
時折、依存性の注入をして、外部の設定ファイルからクラスのメソッドをエイリアスで呼び出したい時がありました。
その際、真っ先に思いついたのは下記のような実装でした。

```python
class Parrot:
    # refers to `Dead Parrot sketch`
    def __init__(self):
        self.does = {
            'pine': self.decease,
            'sleep': self.expire,
        }

    def decease(self):
        return 'go_to_meet_its_maker'
    
    def expire(self):
        return 'rest_in_peace'


ex_parrot = Parrot()
print(ex_parrot.does['sleep']())  # >>> 'rest_in_peace'
```

ですが、これだと多少の問題があります。
- どのメソッドを何の単語で登録したか`__init__`を見ないとわからなくなる
- メソッド名を変更するとき、辞書も変更しなければならない
- キーを変更するとき、当然辞書も変更しなければならない

これでは不便なため、一つのメソッドがどのキーに結びついているかが一見して理解できて、また変更も容易にしたいところです。

# 単純な実装
## クラス定義
メタクラスで単純な引数付きデコレータ関数を定義します。「ダブり」で登録しないために、例外も実装します。

```python
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
```

「コンテナ」となるクラスの`staticmethod`にデコレータをつけます。

```python
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
```

## 問題点
これでエイリアスの登録はできましたが、この実装は`metaclass=MethodsMapper`を再利用した際に問題が生じます。

```python
class AnotherContainer(metaclass=MethodsMapper):
    # omit `__init__` and `maps`
    @staticmethod
    @MethodsMapper.register('a')
    def baz(additional) -> str:
        return f'{additional}_baz'

# ERROR!
another = AnotherContainer()
print(another.maps['a']('spam'))  # >>> 'spam_baz'
```

上記コードを実行すると、`AlreadyExistsKeyInMethodsMapper: 'a' is an already-existed key.`と例外が返されてしまいます。

これは違うクラスでも、同じメタクラス`MethodsMapper`のプライベート変数である辞書`__keys_meths`に同じキーでメソッドを登録しようとしたためです。

また、`staticmethod`しか登録できないのは、クラスやインスタンスの他の属性を参照できず不便です。

# メタクラスの単純な再利用を禁止し、`staticmethod`以外も登録可能にする

```python
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

```
## 各クラスの解説
用例はdocstringを参照のこと。

### `MethodWrapper`
デコレートされたメソッドをラップするためのクラス。

`__init__`の引数に`method`を受け取り、`inspect.signature(method).parameters`を見て
- 第一引数が`self`ならインスタンスメソッド
- 第一引数が`cls`ならクラスメソッド
- 第一引数が上記以外か、引数がないならスタティックメソッド

として、

`__call__`の引数にインスタンスを渡すことでアンラップして、外部から呼び出し可能な関数を返します。

### `AlreadyExistsKeyInMethodsMapper`
「ダブり」で登録しようとした際の例外。

### `MethodsMapper`
プライベートな抽象属性`__usage`と`__maps`の定義が必要な抽象クラス。

サブクラスが`MethodsMapper`を継承すれば`__init_subclass__`が発火して、`__usage`と`__maps`を定義するため、サブクラス上でこれらの変数を定義する必要はありません。

サブクラス化しないと、`__maps`を定義していないことで`AttributeError`が発生して、それをキャッチしてインスタンス化できない旨の`TypeError`を発生させます。

このクラスのサブクラスをメタクラスとして使うと、`__new__`の発火時に`__usage`にクラスの型が登録されます。

違うクラスで同じメタクラスを使おうとすると、`__usage`に2つ以上のクラスが登録されることになり、`TypeError`を返します。

# 用例とテスト
下記のサンプル用のクラスを作って`assert`で検証します。

```python
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
```

また、この様なデコレータも作ることができます。

```python
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
```

`AnotherMapper`の`__init__`が発火した際に、クラスの属性にメタクラスの属性を引き渡して、インスタンス側で使えるようにしてあります。

# 終わりに
プロダクト開発では、外部から様々な経理上のドキュメントをパースするようなプログラムを実装する必要があり、その条件分岐を外部の設定ファイルに委ねているため、依存性の注入をした際に分かりやすい書き方が必要で、このコラムのもとになるプログラムを書きました。

このライブラリが、同じようなお悩みを抱えていた方の一助となれば幸いです。