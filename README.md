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
from jsjson import JSON

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


History
-------

### 0.1.0 (2026-06-02)

  * Initial version.
