Pythonで辞書の様にクラスのメソッドを呼び出す

# きっかけ
時折、依存性の注入をして、外部の設定ファイルからクラスのメソッドを呼び出したい時がある。
その際、真っ先に思いつくのは下記のような実装である。

```python
class Parrot:
    # refers to `Dead Parrot sketch`
    def __init__(self):
        self.does = {
            'pine': self.decease,
            'sleep': self.expire,
            'shag_out': self.go_to_meet_its_maker,
            'rest': self.rest_in_peace,
        }

    def decease(self):
        pass
    
    def expire(self):
        pass

    def go_to_meet_its_maker(self):
        pass

    def rest_in_peace(self):
        pass


ex_parrot = Parrot()
ex_parrot.does['sleep']()
```

だが、これだと多少の問題がある。
- どのメソッドを何の単語で登録したか`__init__`を見ないとわからなくなる
- メソッド名を変更するとき、辞書も変更しなければならない
- キーを変更するとき、当然辞書も変更しなければならない

これでは不便なため、一つのメソッドがどのキーに結びついているかが一見して理解でき、変更にも容易にしたい。

# 単純な実装
## クラス定義
メタクラスで単純な引数付きデコレータ関数を定義する。「ダブり」で登録しないために、例外も実装する。

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

「コンテナ」となるクラスの`staticmethod`にデコレータをつける。

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
だが、`metaclass=MethodsMapper`を再利用すると問題が発生する。

```python
class AnotherContainer(metaclass=MethodsMapper):
    # omit `__init__` and `maps`
    @staticmethod
    @MethodsMapper.register('a')
    def baz(additional) -> str:
        return f'{additional}_bar'

# ERROR!
another = AnotherContainer()
print(another.maps['a']('spam'))  # >>> 'spam_baz'
```

これを実行すると`AlreadyExistsKeyInMethodsMapper: 'a' is an already-existed key.`と例外が返されて止まってしまう。

これは違うクラスでも、同じメタクラス`MethodsMapper`のプライベートな内部変数の辞書`__keys_meths`に同じキーでメソッドを登録しようとしたために発生している。

また、`staticmethod`しか登録できないのは、クラスやインスタンスの他の属性を参照できなくて不便である。

# メタクラスの単純な再利用の禁止と、`staticmethod`以外も登録可能にする

```python
from types import MappingProxyType, MethodType
from typing import Callable
from inspect import signature


class MethodWrapper:
    """
    Wrapper class for methods of class attributes.

    Calls with passing `instance` to unwrap method.
    """
    # What is `types.MethodType` and descripter, access below.
    # https://docs.python.org/ja/3/howto/descriptor.html
    # https://docs.python.org/ja/3/library/types.html?highlight=types#types.MethodType
    def __init__(self, method):
        self.__method = method
        params = tuple(signature(method).parameters)
        self.__is_instmeth = bool(params and params[0] == 'self')
        self.__is_clsmeth = bool(params and params[0] in ('cls', 'klass'))
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
            pass  # methods with decorators.

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
        Returns `method` itself after registering the method to
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
        Private function.
        Returns accsociative array of keys and methods.
        """
        return MappingProxyType(
            {key: meth_wrap(instance) for key, meth_wrap in cls.__maps.items()}
        )
```
## 各クラスの解説
### `MethodWrapper`
デコレートされたメソッドをラップするためのクラス。

`__init__`の引数に`method`を受け取って、`inspect.signature`で`inspect.Signature.parameters`を見て
- 第一引数が`self`ならインスタンスメソッド
- 第一引数が`cls`または`klass`ならクラスメソッド
- 第一引数が上記以外か引数がないならスタティックメソッド

として、

`__call__`の引数にインスタンスを渡すことでアンラップして、外部から呼び出し可能な関数を返す。

### `AlreadyExistsKeyInMethodsMapper`
