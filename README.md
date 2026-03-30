# Codroid

[![PyPI - Version](https://img.shields.io/pypi/v/codroid-robot-sdk.svg)](https://pypi.org/project/codroid-robot-sdk)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/codroid-robot-sdk.svg)](https://pypi.org/project/codroid-robot-sdk)

-----

## Table of Contents

- [Codroid](#codroid)
  - [Table of Contents](#table-of-contents)
  - [Installation](#installation)
  - [Basic Usage](#basic-usage)
  - [License](#license)

## Installation

```console
pip install codroid-robot-sdk
```

## Basic Usage
```python
from codroid import CodroidControlInterface

# Initialize and connect automatically
with CodroidControlInterface(host="192.168.1.136") as robot:
    robot.to_remote()
    robot.switch_on()
```

## License

`codroid` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
