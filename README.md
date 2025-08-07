# HEXFIX

## Overview

**HEXFIX** is a Python toolkit for working with Motorola HEX / S-record files. It helps firmware engineers inspect, edit and prepare data for programming. The library is aimed at embedded developers who need to customize firmware images, manage memory layouts and assemble files for flashing or analysis.

## Features

### Merge SREC files
Combine the contents of two S-record streams into a single file, resolving overlapping records and preserving order.

### Extract an address range
Select a start and end address to slice out a portion of an S-record file. Partial records are automatically trimmed so that only bytes in the requested range remain.

### Relocate data blocks
Move a block of bytes from one address range to another. Record addresses are rewritten and surrounding data is preserved, making it easy to adjust firmware layouts.

## Installation

```bash
pip install hexfix
```

## Example

```python
from hexfix import merge_srec, extract_range_srec, relocate_range_srec
```
