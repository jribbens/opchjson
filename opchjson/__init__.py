"""Handle JSON objects more simply, like you do in JavaScript."""

# Copyright 2026 Jon Ribbens

from collections.abc import (
    Callable,
    Hashable,
    ItemsView,
    Iterable,
    Iterator,
    KeysView,
    Mapping,
    ValuesView,
)
import datetime
from functools import total_ordering
import json
from pathlib import Path
import re
import sys
from typing import (
    Any,
    Never,
    Protocol,
    Self,
    SupportsIndex,
    TypeVar,
    Union,
    overload,
)
from urllib.parse import urlparse

_returns_co = TypeVar('_returns_co', covariant=True)
_T = TypeVar('_T')


class SupportsRead(Protocol[_returns_co]):
    """A Protocol for file-like objects with a read() method."""

    def read(self, size: int = -1) -> _returns_co:
        """
        Read at most size characters from stream.

        Read from underlying buffer until we have size characters or we hit
        EOF.

        Args:
            size: maximum number of bytes or characters to read,
                  or -1 to continue until EOF.

        Returns:
            The bytes or string read from the file.
        """


ObjectKeyType = str | int


class Unsupplied:
    """A sentinel value and type for an argument that is unsupplied."""


unsupplied = Unsupplied()


class JSON:
    """JSON utilities."""

    Types = Union[
        None, bool, float, int, str,
        'JSON.Array', 'JSON.Object', 'JSON.String', 'JSON.Undefined',
    ]
    InputTypes = Types | list | tuple | dict

    def __new__(  # type: ignore[misc]
        cls: type['JSON'],
        value: 'JSON.InputTypes',
    ) -> 'JSON.Types':
        """
        Return the JSON form of an object.

        Args:
            value: The object to convert.

        Returns:
            The value, possibly wrapped in a JSON object.

        Raises:
            TypeError: if the object cannot be represented in JSON.
        """
        if not isinstance(value, JSON.InputTypes):
            raise TypeError(
                f'JSON() cannot accept objects of type {type(value)}'
            )
        return (
            cls.Object(cls, value) if isinstance(value, dict)
            else cls.Array(cls, value) if isinstance(value, (list, tuple))
            else cls.String(cls, value) if isinstance(value, str)
            else value
        )

    @classmethod
    def parse(
        cls: type['JSON'],
        value: str | bytes | bytearray | SupportsRead[str | bytes] | Path,
        **kwargs: Any
    ) -> 'JSON.Types':
        """
        Parse the value as JSON and return it as JSON objects.

        Args:
            value: a string, bytes, a bytearray, a file-like object,
              or a pathlib.Path
            kwargs: any other keyword arguments to pass to json.load(s)

        Returns:
            One of the JSON.Types objects.

        If you pass a Path object, it is assumed to be in utf-8 encoding
        unless you pass an 'encoding' keyword argument specifying another
        encoding.
        """
        if isinstance(value, (str, bytes, bytearray)):
            return cls(
                json.loads(value, **kwargs)
            )  # type: ignore[return-value]
        if isinstance(value, Path):
            with value.open(
                encoding=kwargs.pop('encoding', None) or 'utf-8',
            ) as fh:
                return cls(
                    json.load(fh, **kwargs)
                )  # type: ignore[return-value]
        return cls(json.load(value, **kwargs))  # type: ignore[return-value]

    @classmethod
    def stringify(
        cls: type['JSON'],
        value: 'JSON.InputTypes',
        *args: tuple[()] | tuple[None] | tuple[None, int | str | None],
        **kwargs: Any
    ) -> str:
        """
        Convert an object into a JSON string.

        Takes either the JavaScript-style (value, replacer, space)
        positional arguments, or the Python-style json.dump keyword
        arguments, or a mixture of the two.

        Args:
            value: one of the JSON.Types objects
            args: () or (None, int/str/None)
            kwargs: as per json.dumps

        Returns:
            JSON string

        Raises:
            TypeError: if the arguments are incorrect
            ValueError: if 'replacer' is specified
        """
        if len(args) > 2:
            raise TypeError(
                f'stringify takes at most 2 arguments ({len(args)} given)'
            )
        if len(args) > 0 and args[0]:
            raise ValueError('stringify(replacer) not supported')
        if len(args) > 1:
            if isinstance(args[1], int):
                kwargs['indent'] = args[1] if args[1] > 0 else None
            else:
                kwargs['indent'] = args[1] or None
            if kwargs['indent'] is None:
                kwargs.setdefault('separators', (',', ':'))
        elif 'indent' not in kwargs:
            kwargs.setdefault('separators', (',', ':'))
        kwargs.setdefault('default', cls.encode)
        return json.dumps(value, **kwargs)

    @staticmethod
    def encode(obj: object) -> object:
        """
        'default' method for json.dump.

        Args:
            obj: the object to provide an encoding for.

        Returns:
            An object that json.dump knows how to encode itself.

        Raises:
            TypeError: if obj is not something we know how to encode.
        """
        # ruff: disable[SLF001]
        if isinstance(obj, JSON.Object):
            if JSON.undefined in obj._values():
                return {
                    key: value
                    for key, value in obj._items()
                    if value is not JSON.undefined
                }
            return obj._dict
        if isinstance(obj, JSON.Array):
            if JSON.undefined in obj:
                return [
                    None if value is JSON.undefined else value
                    for value in obj
                ]
            return obj._list
        raise TypeError
        # ruff: enable[SLF001]

    class Undefined:
        """A singleton class representing the JSON 'undefined' value."""

        __slots__ = ()

        _instance: Union['JSON.Undefined', None] = None

        def __new__(cls) -> 'JSON.Undefined':
            """Return the singleton instance of the Undefined class."""
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance

        # our custom methods

        def _json(self, **kwargs: Any) -> Never:  # noqa: ARG002
            """
            Encode the object as a JSON string.

            Raises:
                ValueError: because 'undefined' cannot be encoded in JSON
            """
            raise ValueError('"undefined" cannot be represented in JSON')

        # standard dict methods

        def _clear(self) -> Never:
            """
            Raise ValueError, as undefined cannot be modified.

            Raises:
                ValueError: always
            """
            raise ValueError("Cannot modify 'undefined'")

        @overload
        def _get(
            self,
            key: ObjectKeyType,
            /
        ) -> 'JSON.Undefined': ...
        @overload
        def _get(
            self,
            key: ObjectKeyType,
            default: _T,
            /
        ) -> _T: ...
        def _get(  # type: ignore[no-untyped-def]
            self,
            key,  # noqa: ARG002
            default=unsupplied,
            /
        ):
            """
            Return the given default, or undefined.

            Args:
                key: ignored
                default: the default value to use.

            Returns:
                The provided default value, or undefined.
            """
            return JSON.undefined if default is unsupplied else default

        def _items(self) -> ItemsView[ObjectKeyType, 'JSON.Types']:
            """
            Return an empty iterator.

            Returns:
                An iterator that returns nothing.
            """
            return {}.items()

        def _keys(self) -> KeysView[ObjectKeyType]:
            """
            Return an empty iterator.

            Returns:
                An iterator that returns nothing.
            """
            return {}.keys()

        @overload
        def _pop(self, key: ObjectKeyType) -> Never: ...
        @overload
        def _pop(self, key: ObjectKeyType, default: _T) -> _T: ...
        def _pop(  # type: ignore[no-untyped-def]
            self,
            key,  # noqa: ARG002
            default=unsupplied,
        ):
            """
            Return the default if provided, otherwise undefined.

            Args:
                key: ignored
                default: the default value to use.

            Returns:
                The provided default value.
            """
            return JSON.undefined if default is unsupplied else default

        def _popitem(self) -> Never:
            """
            Raise KeyError, as undefined never contains any values.

            Raises:
                KeyError: always
            """
            raise KeyError('popitem(): undefined contains no values')

        def _setdefault(
            self,
            key: ObjectKeyType,  # noqa: ARG002
            default: 'JSON.InputTypes' = None  # noqa: ARG002
        ) -> Never:
            """
            Raise ValuError, as undefined cannot be modified.

            Raises:
                ValueError: always
            """
            raise ValueError("Cannot modify 'undefined'")

        def _update(self, *args: Any, **kwargs: Any) -> Never:  # noqa: ARG002
            """
            Raise ValuError, as undefined cannot be modified.

            Raises:
                ValueError: always
            """
            raise ValueError("Cannot modify 'undefined'")

        def _values(self) -> ValuesView['JSON.Types']:
            """
            Return an empty iterator.

            Returns:
                An iterator that returns nothing.
            """
            return {}.values()

        # python 'magic' methods

        def __repr__(self) -> str:
            """
            Return 'undefined'.

            Returns:
                The string 'undefined'
            """
            return 'undefined'

        def __str__(self) -> str:
            """
            Return 'undefined'.

            Returns:
                The string 'undefined'
            """
            return 'undefined'

        def __lt__(self, other: object) -> bool:
            """
            Refuse greater/lesser comparisons between undefined and anything.

            Returns:
                NotImplemented
            """
            return NotImplemented

        def __eq__(self, other: object) -> bool:
            """
            Return True if the object we are comparing with is also undefined.

            Args:
                other: the other object to compare with

            Returns:
                True if 'other' is undefined, otherwise False
            """
            return self is other

        def __hash__(self) -> int:
            """
            Return a hash value for the undefined object.

            Returns:
                an integer hash value
            """
            return hash('undefined')

        def __getattribute__(self, name: str) -> Any:
            """
            Look up name as an object attribute or a dictionary key.

            Args:
                name: the attribute to look up. If it begins '_' then it
                      is looked for as an attribute name, otherwise
                      JSON.undefined is returned.

            Returns:
                the attribute value, or undefined.
            """
            if name[:1] == '_':
                return super().__getattribute__(name)
            return JSON.undefined

        def __setattr__(self, name: str, value: 'JSON.InputTypes') -> None:
            """
            Raise ValueError, as 'undefined 'is not modifiable.

            Args:
                name: ignored
                value: ignored

            Raises:
                ValueError: always
            """
            raise ValueError("Cannot modify 'undefined'")

        def __delattr__(self, name: str) -> None:
            """
            Raise ValueError, as 'undefined 'is not modifiable.

            Args:
                name: ignored

            Raises:
                ValueError: always
            """
            raise ValueError("Cannot modify 'undefined'")

        def __len__(self) -> int:
            """
            Return the length of undefined, which is always 0.

            Returns:
                0
            """
            return 0

        def __getitem__(self, key: ObjectKeyType) -> 'JSON.Undefined':
            """
            Retrieve a value from undefined, which always returns undefined.

            Args:
                key: ignored

            Returns:
                undefined
            """
            return JSON.undefined

        def __setitem__(
            self,
            key: ObjectKeyType,
            value: 'JSON.InputTypes'
        ) -> Never:
            """
            Raise ValueError, as you cannot modify undefined.

            Args:
                key: ignored
                value: ignored

            Raises:
                ValueError: always
            """
            raise ValueError("Cannot modify 'undefined'")

        def __delitem__(self, key: ObjectKeyType) -> Never:
            """
            Raise ValueError, as you cannot modify undefined.

            Args:
                key: ignored

            Raises:
                ValueError: always
            """
            raise ValueError("Cannot modify 'undefined'")

        def __iter__(self) -> Iterator[ObjectKeyType]:
            """
            Return an empty iterator.

            Returns:
                an empty iterator
            """
            return iter({})

        def __reversed__(self) -> Iterator[ObjectKeyType]:
            """
            Return an empty iterator.

            Returns:
                an empty iterator
            """
            return iter({})

        def __contains__(self, key: object) -> bool:
            """
            Return False, since undefined does not contain anything.

            Returns:
                False
            """
            return False

    undefined = Undefined()

    class String(str):
        """A JSON string."""

        __slots__ = ('_JSON',)
        _JSON: type['JSON']

        def __new__(
            cls: type['JSON.String'],
            base: type['JSON'],
            *args: Any
        ) -> 'JSON.String':
            """Create a new JSON String object."""
            obj = super().__new__(cls, *args)
            obj._JSON = base
            return obj

        # our custom methods

        def _json(self, **kwargs: Any) -> str:
            """
            Return this string as a JSON string.

            Returns:
                This string as a JSON string.
            """
            return self._JSON.stringify(self, **kwargs)

        @property
        def url(self) -> Any:
            """
            Return the string parsed into a URL object.

            Returns:
                A urlparse() result.
            """
            try:
                return urlparse(self)
            except ValueError:
                return urlparse('')

        @property
        def datetime(self) -> datetime.datetime:
            """
            Return the string parsed into a datetime object.

            Returns:
                a datetime object

            Raises:
                ValueError: if the string cannot be parsed as a datetime
            """
            s = re.sub(r'Z$', '+0000', self)
            for date_format in (
                '%Y-%m-%dT%H:%M:%S.%f%z',
                '%Y-%m-%dT%H:%M:%S%z',
            ):
                try:
                    return datetime.datetime.strptime(  # noqa: DTZ007
                        s,
                        date_format
                    )
                except ValueError:
                    pass
            raise ValueError(
                f'String {self!r} could not be parsed as a datetime'
            )

    @total_ordering
    class Array:  # noqa: PLW1641
        """A JSON array."""

        _JSON: type['JSON']
        _list: list['JSON.Types']

        def __init__(
            self,
            base: type['JSON'],
            init: Iterable['JSON.InputTypes'] = ()
        ) -> None:
            """
            Initialise the array as per the list() constructor.

            Args:
                base: the base JSON class
                init: an optional iterator to initialise the list
            """
            # ruff: disable[SLF001]
            self._JSON = base
            self._list = (
                init._list.copy()
                    if type(init) is type(self)
                    and init._JSON is self._JSON
                else [base(value) for value in init]  # type: ignore[misc]
            )
            # ruff: enable[SLF001]

        # our custom methods

        def _json(self, **kwargs: Any) -> str:
            """
            Return this array as a JSON string.

            Returns:
                this array as a JSON string
            """
            return self._JSON.stringify(self, **kwargs)

        # standard list methods

        def index(
            self,
            value: Any,
            start: SupportsIndex = 0,
            stop: SupportsIndex = sys.maxsize
        ) -> int:
            """
            Return first index where value is found in the array.

            Args:
                value: the object to look for in the array
                start: the first index to look at
                stop: the last index not to look at

            Returns:
                the first index the object was found at

            Raises:
                ValueError: if the value is not found
            """
            return self._list.index(value, start, stop)

        def count(self, value: Any) -> int:
            """
            Return number of occurrences of value in the array.

            Args:
                value: the object to look for in the array

            Returns:
                the number of times the object was found
            """
            return self._list.count(value)

        def append(self, value: 'JSON.InputTypes') -> None:
            """
            Append value to the end of the array, converted if necessary.

            Args:
                value: the value to convert and append
            """
            self._list.append(self._JSON(value))  # type: ignore[arg-type]

        def clear(self) -> None:
            """Remove all items from the array."""
            self._list.clear()

        def copy(self) -> Self:
            """
            Return a shallow copy of the array.

            Returns:
                a shallow copy of the array
            """
            return self.__class__(self._JSON, self)

        def extend(self, iterable: Iterable['JSON.InputTypes']) -> None:
            """Extend the array by appending elements from the iterable."""
            if iterable is self or iterable is self._list:
                self._list *= 2
            else:
                self._list.extend(
                    self._JSON(value)  # type: ignore[misc]
                    for value in iterable
                )

        def insert(
            self,
            index: SupportsIndex,
            value: 'JSON.InputTypes'
        ) -> None:
            """Insert value before index."""
            self._list.insert(
                index,
                self._JSON(value)  # type: ignore[arg-type]
            )

        def pop(self, index: SupportsIndex = -1) -> 'JSON.Types':
            """
            Remove and return item at index (default last).

            Args:
                index: the index of the item to return (default last)

            Returns:
                the item requested, or undefined if the list is empty or
                the index is out of range
            """
            try:
                return self._list.pop(index)
            except IndexError:
                return JSON.undefined

        def remove(self, value: Any) -> None:
            """
            Remove first occurrence of value.

            Args:
                value: the value to remove, if found
            """
            try:
                self._list.remove(value)
            except ValueError:
                pass

        def reverse(self) -> None:
            """Reverse *IN PLACE*."""
            self._list.reverse()

        def sort(
            self,
            *,
            key: Callable | None = None,
            reverse: bool = False,
        ) -> None:
            """Sort the list in ascending order and return None."""
            self._list.sort(
                key=key, reverse=reverse
            )  # ty: ignore[no-matching-overload]

        # list operators

        def __add__(self, other: Iterable['JSON.InputTypes']) -> Self:
            """
            Add the contents of the other iterable to a copy of this array.

            Returns:
                the new array
            """
            result = self.copy()
            result += other
            return result

        def __mul__(self, other: int) -> Self:
            """
            Return a copy of this array appended to itself 'other' times.

            Returns:
                the new array
            """
            result = self.copy()
            result *= other
            return result

        def __rmul__(self, other: int) -> Self:
            """
            Return a copy of this array appended to itself 'other' times.

            Returns:
                the new array
            """
            result = self.copy()
            result *= other
            return result

        def __iadd__(self, other: Iterable['JSON.InputTypes']) -> Self:
            """
            Append items from the given iterable to this array.

            Returns:
                this array
            """
            self.extend(other)
            return self

        def __imul__(self, other: int) -> Self:
            """
            Append this array to itself 'other' times.

            Returns:
                this array
            """
            self._list *= other
            return self

        # python 'magic' methods

        def __repr__(self) -> str:
            """
            Return a Python list representation of this array.

            Returns:
                a Python list literal representing this array
            """
            return repr(self._list)

        def __str__(self) -> str:
            """
            Return a JSON representation of this array.

            Returns:
                a string containing JSON representing this array
            """
            return self._json(indent=2)

        def __lt__(self, other: Any) -> bool:
            """
            Return True if this array is 'less than' the other object.

            Returns:
                True if this array is 'less than' the other object
            """
            return bool(other > self._list)

        def __eq__(self, other: object) -> bool:
            """
            Return True if this array is 'equal to' the other object.

            Returns:
                True if this array is 'equal to' the other object
            """
            return other == self._list

        def __len__(self) -> int:
            """
            Return the number of items in this array.

            Returns:
                the number of items in this array
            """
            return len(self._list)

        @overload
        def __getitem__(self, key: SupportsIndex) -> 'JSON.Types': ...
        @overload
        def __getitem__(self, key: slice) -> 'JSON.Array': ...
        def __getitem__(self, key):  # type: ignore[no-untyped-def]
            """
            Return the item at the given index in the array.

            Args:
                key: either the index, or a slice object

            Returns:
                if 'key' was a slice, a new array
                otherwise the item at index 'key' of the array
                otherwise undefined
            """
            if isinstance(key, slice):
                result = self.__class__(self._JSON)
                result._list = self._list[key]  # noqa: SLF001
                return result
            try:
                return self._list[key]
            except IndexError:
                return JSON.undefined

        @overload
        def __setitem__(
            self,
            key: SupportsIndex,
            value: 'JSON.InputTypes'
        ) -> None: ...
        @overload
        def __setitem__(
            self,
            key: slice,
            value: Iterable['JSON.InputTypes']
        ) -> None: ...
        def __setitem__(self, key, value):  # type: ignore[no-untyped-def]
            """
            Set the item at the given index, or items at the slice.

            Args:
                key: the index to set, or a slice object
                value: the value or values to set
            """
            if isinstance(key, slice):
                self._list[key] = (
                    self._JSON(item)  # type: ignore[misc]
                    for item in value
                )
            else:
                self._list[key] = self._JSON(  # type: ignore[call-overload]
                    value
                )

        def __delitem__(self, key: SupportsIndex | slice) -> None:
            """
            Delete the given item (or range of items) from the array.

            Args:
                key: the index of the item, or a slice object
            """
            del self._list[key]

        def __iter__(self) -> Iterator['JSON.Types']:
            """
            Iterate over the contents of the array.

            Returns:
                an iterator over the contents of the array
            """
            return iter(self._list)

        def __reversed__(self) -> Iterator['JSON.Types']:
            """
            Return an iterator of the contents of the array, in reverse.

            Returns:
                an iterator of the contents of the array, in reverse
            """
            return reversed(self._list)

        def __contains__(self, value: object) -> bool:
            """
            Return True if the array contains 'value'.

            Returns:
                True if the array contains 'value'
            """
            return value in self._list

    @total_ordering
    class Object:  # noqa: PLW1641
        """A JSON Object."""

        _JSON: type['JSON']
        _dict: dict[int | str, 'JSON.Types']

        def __init__(
            self,
            base: type['JSON'],
            *args: Any,
            **kwargs: Any
        ) -> None:
            """
            Create a JSON Object.

            Args:
                base: the base JSON class
                args: initialisation positional arguments as per dict()
                kwargs: initialisation keyword arguments as per dict()
            """
            self._JSON = base
            self._dict = {}
            self._update(*args, **kwargs)

        # our custom methods

        def _json(self, **kwargs: Any) -> str:
            """
            Return the object as a JSON string.

            Returns:
                the object as a JSON string
            """
            return self._JSON.stringify(self, **kwargs)

        # standard dict methods

        def _clear(self) -> None:
            """Remove all items from the object."""
            self._dict.clear()

        def _copy(self) -> Self:
            """
            Return a shallow copy of this object.

            Returns:
                a shallow copy of this object
            """
            return self.__class__(self._JSON, self)

        # fromkeys() is not implemented as it has no way of getting _JSON

        @overload
        def _get(
            self,
            key: ObjectKeyType,
            /
        ) -> 'JSON.Types': ...
        @overload
        def _get(
            self,
            key: ObjectKeyType,
            default: _T,
            /
        ) -> Union[_T, 'JSON.Types']: ...
        def _get(  # type: ignore[no-untyped-def]
            self,
            key,
            default=unsupplied,
            /
        ):
            """
            Return the value for key if key is in the object, else default.

            Args:
                key: the property name
                default: the default value to return

            Returns:
                the property value, or the default, or undefined.
            """
            return self._dict.get(
                key,
                JSON.undefined if default is unsupplied else default
            )

        def _items(self) -> ItemsView[ObjectKeyType, 'JSON.Types']:
            """
            Return an iterator over tuples (property, value) from the object.

            Returns:
                an iterator over tuples (property, value)
            """
            return self._dict.items()

        def _keys(self) -> KeysView[ObjectKeyType]:
            """
            Return an iterator over the object property names.

            Returns:
                an iterator over the object property names
            """
            return self._dict.keys()

        @overload
        def _pop(
            self,
            key: ObjectKeyType,
            default: Unsupplied = unsupplied,
            /
        ) -> 'JSON.Types': ...
        @overload
        def _pop(
            self,
            key: ObjectKeyType,
            default: _T,
            /
        ) -> Union[_T, 'JSON.Types']: ...
        def _pop(  # type: ignore[no-untyped-def]
            self,
            key,
            default=unsupplied,
            /
        ):
            """
            Return the named property's value, and remove it from the object.

            Args:
                key: the property name
                default: the value to return if the property does not exist

            Returns:
                the property value, or default, or undefined
            """
            return self._dict.pop(
                key,
                JSON.undefined if default is unsupplied else default
            )

        def _popitem(self) -> tuple[ObjectKeyType, 'JSON.Types']:
            """
            Remove and return a (property-name, value) pair as a 2-tuple.

            Returns:
                (property-name, value)

            Raises:
                KeyError: if the object has no properties
            """
            return self._dict.popitem()

        def _setdefault(
            self,
            key: ObjectKeyType,
            default: 'JSON.Types' = None,
            /
        ) -> 'JSON.Types':
            """
            Set a property but only if it is currently undefined.

            Args:
                key: the property name
                default: the value to insert (defaults to None)

            Returns:
                the property value (default if it wasn't previously defined)
            """
            value = self._get(key)
            if value is undefined:
                default = self._JSON(default)  # type: ignore[assignment]
                self[key] = default
                return default
            return value

        def _update(
            self,
            *args: Any,
            **kwargs: dict[ObjectKeyType, 'JSON.InputTypes']
        ) -> None:
            """
            Update the object with new properties.

            Args:
                args: if supplied, a single Mapping object to be copied from
                kwargs: keyword args to be used as property names and values

            Raises:
                TypeError: if too many positional arguments are supplied
            """
            if args:
                if len(args) != 1:
                    raise TypeError(
                        f'update expected at most 1 argument, got {len(args)}'
                    )
                if isinstance(args[0], JSON.Object):
                    self._dict.update(args[0]._dict)  # noqa: SLF001
                elif isinstance(args[0], dict):
                    self._dict.update({
                        key: self._JSON(value)
                        for key, value in args[0].items()
                    })
                elif hasattr(args[0], 'keys'):
                    self._dict.update({
                        key: self._JSON(args[0][key])
                        for key in args[0]
                    })
                else:
                    self._dict.update({
                        key: self._JSON(value)
                        for key, value in args[0]
                    })
            if kwargs:
                self._dict.update({
                    key: self._JSON(value)  # type: ignore[misc]
                    for key, value in kwargs.items()
                })

        def _values(self) -> ValuesView['JSON.Types']:
            """
            Return an iterator over the object property values.

            Returns:
                an iterator over the object property values
            """
            return self._dict.values()

        # dict operators

        def __or__(self, other: Union[Mapping, 'JSON.Object']) -> Self:
            """
            Create a new object with properties from this one and another.

            Args:
                other: another JSON Object or dictionary

            Returns:
                a new object with the properties of this one and other
            """
            result = self._copy()
            result._update(other)
            return result

        def __ior__(self, other: Union[Mapping, 'JSON.Object']) -> Self:
            """
            Update this object with the properties from another.

            Args:
                other: another JSON Object or dictionary

            Returns:
                this object
            """
            self._update(other)
            return self

        # python 'magic' methods

        def __repr__(self) -> str:
            """
            Return a Python dictionary literal representation of this object.

            Returns:
                a Python dictionary literal representing this object
            """
            return repr(self._dict)

        def __str__(self) -> str:
            """
            Return a JSON representation of this object.

            Returns:
                a string containing JSON representing this object
            """
            return self._json(indent=2)

        def __lt__(self, other: Any) -> bool:
            """
            Return True if this object is 'less than' the other object.

            Returns:
                True if this object is 'less than' the other object
            """
            return bool(other > self._dict)

        def __eq__(self, other: object) -> bool:
            """
            Return True if this object is 'equal to' the other object.

            Returns:
                True if this array is 'equal to' the other object
            """
            return other == self._dict

        def __getattribute__(self, name: str) -> Any:
            """
            Look up name as an object attribute or a dictionary key.

            Args:
                name: the attribute to look up. If it begins '_' then it
                      is looked for as an attribute name, otherwise it is
                      looked for as an object property name.

            Returns:
                the attribute or property value, or undefined if not found.
            """
            if name[:1] == '_':
                return super().__getattribute__(name)
            return self._get(name)

        def __setattr__(self, name: str, value: Any) -> None:
            """
            Set name as an attribute or property value.

            Args:
                name: the attribute to look up. If it begins '_' then it
                      is looked for as an attribute name, otherwise it is
                      used as an object property name.
                value: the value to set
            """
            if name[:1] == '_':
                super().__setattr__(name, value)
            else:
                self._dict[name] = self._JSON(
                    value
                )  # type: ignore[assignment]

        def __delattr__(self, name: str) -> None:
            """
            Delete name as an attribute or property.

            Args:
                name: the attribute to look up. If it begins '_' then it is
                      looked for as an attribute, otherwise it is used as an
                      object property name.
            """
            try:
                if name[:1] == '_':
                    super().__delattr__(name)
                else:
                    del self._dict[name]
            except (AttributeError, KeyError):
                pass

        def __dir__(self) -> list[str]:
            """
            Return an iterator over the object property names.

            Returns:
                an iterator over the object property names
            """
            return [str(key) for key in self._dict]

        def __len__(self) -> int:
            """
            Return the number of object properties.

            Returns:
                the number of object properties
            """
            return len(self._dict)

        def __getitem__(self, key: ObjectKeyType) -> 'JSON.Types':
            """
            Return the object property with the given name, or undefined.

            Args:
                key: the object property name

            Returns:
                the value of the named property, or undefined
            """
            return self._get(key)

        def __setitem__(
            self,
            key: ObjectKeyType,
            value: 'JSON.InputTypes'
        ) -> None:
            """
            Set the object property with the given name to the given value.

            Args:
                key: the property name
                value: the value to set

            Raises:
                TypeError: if the key is not a valid property name
            """
            if not isinstance(key, (int, str)):
                raise TypeError(
                    f'Cannot use {type(key)} as an object property name'
                )
            self._dict[key] = self._JSON(
                value
            )  # type: ignore[assignment]

        def __delitem__(self, key: ObjectKeyType) -> None:
            """
            Delete the named object property.

            Args:
                key: the property name
            """
            try:
                del self._dict[key]
            except KeyError:
                pass

        def __iter__(self) -> Iterator[int | str]:
            """
            Return an iterator over the object property names.

            Returns:
                an iterator over the object property names
            """
            return iter(self._dict)

        def __reversed__(self) -> Iterator[int | str]:
            """
            Return an iterator over the object property names, in reverse.

            Returns:
                an iterator over the object property names, in reverse.
            """
            return reversed(self._dict)

        def __contains__(self, key: Hashable) -> bool:
            """
            Return True if the object has a property with the given name.

            Returns:
                True if the object has a property with the given name
            """
            return key in self._dict


undefined = JSON.undefined

# have to patch JSON.Types after loading, as issubclass(foo, union)
# cannot cope with union containing ForwardRefs

JSON.Types = (  # ty: ignore[invalid-assignment]
    None | bool | float | int | str |  # type: ignore[assignment]
    JSON.Array | JSON.Object | JSON.String | JSON.Undefined
)
JSON.InputTypes = JSON.Types | list | tuple | dict  # type: ignore[assignment]
