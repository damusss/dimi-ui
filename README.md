# dimi(-ui)

> [!WARNING]
> dimi-ui is still early in development. It supports a limited amount of features and documentation isn't currently
> available.

dimi is an immediate-mode user interface library designed for Python and pygame-ce using a deferred two-pass layout
system.
More specifically, the layout engine uses four passes to complete a UI cycle:

- declaration pass
- measure/arrange two-pass layout (size & position resolution)
- render/interaction resolution pass

Element interaction is provided immediately during the declaration pass, allowing immediate application logic, but it
is actually deferred from the previous frame, which is negligeable at sensible framerates.

The library supports both software rendering and the experimental `pygame(-ce)._render` API out of the box. It can be
used to build UI-only applications or be integrated in existing applications and games.

The only supported environment is the latest version of the [pygame-ce (Pygame Community Edition)](https://pyga.me)
library. Neither upstream pygame nor the outdated `pygame._sdl2.video` API are supported.

dimi is intended to be a polished and more immediate-oriented successor of [mili](https://github.com/damusss/mili-ui) (
limited only by a couple of layout rules required to keep the two-pass system efficient).

> [!NOTE]
> `dimi`, which is the package import name, stands for "deferred immediate mode (user) interface".

## Installation & Import

Install the latest version thorugh PyPI or clone & install from source

```bash
pip install dimi-ui
```

The import name differs from the PyPI package:

```python
import dimi
```

Every feature can be accessed through the following modules:

- `dimi`
- `dimi.widget`
- `dimi.app`
- `dimi.icon`
- `dimi.typehinting`
