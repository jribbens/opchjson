Handle JSON objects more simply, like you do in JavaScript.
===========================================================

This Python module provides an interface to JSON data structures that
is more reminiscent of the compact and forgiving syntax that you use
in JavaScript than the verbose and picky Python 'dict' interface.

For example, instead of:
```python
from pathlib import Path
import json

with Path('data.json').open(encoding='utf-8') as fh:
    data = json.load(fh)
version = (data.get('summary') or {}).get('version')
```
you can write:
```python
from pathlib import Path
from opchjson import JSON

data = JSON.parse(Path('data.json'))
version = data.summary.version
```
i.e. you can access object properties using the `.` operator, just
like in JavaScript. If you access a non-existent property, it will
return `JSON.undefined`. Note that one difference from JavaScript
behaviour is that if you try and retrieve properties from `undefined`
it will return `undefined` rather than throwing an exception.

Note that you cannot access object properties that start with an
underscore character via the `.` operator, as this is reserved for
accessing Python dictionary methods - e.g. `data._items()`. If you
want to access a property that begins with `_`, simply use the
standard Python `[]` operator- e.g. `data['_foo']`. This will
similarly return `JSON.undefined` if the property does not exist.


Usage
-----

To use the module, do `from opchjson import JSON`. If you wish,
you can also import `undefined`, to save a bit of typing on
`JSON.undefined`.

### JSON()

If you already have a data structure in memory that is suitable
for JSON representation, e.g. a Python dict, you can pass it to
`JSON()` to convert it into `opchjson` representation.

### JSON.parse()

`JSON.parse` takes a single positional argument, which can be
a string, bytes, a bytearray, a pathlib Path, or any file-like
object. If it is a Path, the file will be assumed to be UTF-8
encoded unless you provide an `encoding` keyword argument
specifying a different encoding. You can also pass any keyword
argument that the Python standard library `json.load` function
would accept.

The returned value will be None, a bool, an int, a float, a
string, or an instance of JSON.Array or JSON.Object.

### JSON.stringify()

This function is similar to the JavaScript one of the same name.
The first argument is the value to encode as JSON. The remaining
arguments are either positional arguments as per JavaScript, or
keyword arguments as per Python's `json.dumps`, or a mixture of
both.

### JSON.Array

Instances of this class are essentially identical to Python lists,
except that they will return `JSON.undefined` rather than throwing
exceptions when you try to retrieve list elements that don't exist.
Note that empty Arrays count as falsey, like Python and unlike
JavaScript.

### JSON.Object

Instances of this class are essentially identical to Python dicts,
except that they will return `JSON.undefined` rather than throwing
exceptions when you try to retrieve keys that don't exist. Note that
empty Objects count as falsey, like Python and unlike JavaScript.

### JSON.undefined

This is a singleton instance that behaves like an empty, immutable
`JSON.Object`. Test for it using `foo is JSON.undefined`.


History
-------

### 0.1.0 (2026-06-02)

  * Initial version.
