'''
When run, outputs a series of partially random JSON objects, separated by newlines, to stdout.

To run a test:
1. Run this program and pipe the output into your test program
2. Split the output by the newline character to create an array of JSON objects
3. Convert the JSON objects into a language-native object
4. Convert the JSON objects (the original strings produced by the test program) into JSONZ
5. Convert the JSONZ objects back into language-native objects
If the JSON -> native conversion produced the same objects as the JSON -> JSONZ -> native conversion, then test is a pass.
'''

from random import randint, choices
from decimal import Decimal
from math import log10, ceil
from sys import set_int_max_str_digits
from copy import copy

from json_with_decimals import dumps

# Big integers can store numbers so big they're impossible to compute today.
# This value is the upper limit of what the program will use when testing big integers.
# This number was arbitrarily chosen.
INT_UPPER_LIMIT = 2**100_000
VALID_UTF8_CHARS = list(range(0, 0xD800)) + list(range(0xE000, 0x110000))
# Length in digits of "{biggest integer}.{biggest integer}"
set_int_max_str_digits(2*ceil(log10(INT_UPPER_LIMIT))+1)

test_object = {
    "boolean true": True,
    "boolean false": False,
    "null": None,
    "string 0": "",
    "string ascii": "".join(chr(randint(0, 127)) for x in range(100_000)),
    "string utf-8": "".join(chr(x) for x in choices(VALID_UTF8_CHARS, k=100_000)),
    "resizing integer 1": randint(4294967296, 72057594037927935),
    "resizing integer 2": randint(18446744073709551616, 2**2040-1),
    "negative resizing integer 1": -randint(4294967296, 72057594037927935),
    "negative resizing integer 2": -randint(18446744073709551616, 2**2040-1),
    "unsigned 8-bit defined integer": randint(0, 255),
    "unsigned 8-bit defined integer 2": 0,
    "unsigned 16-bit defined integer": randint(256, 65535),
    "unsigned 24-bit defined integer": randint(65536, 16777215),
    "unsigned 32-bit defined integer": randint(16777216, 4294967295),
    "unsigned 64-bit defined integer": randint(72057594037927936, 18446744073709551615),
    "negative 8-bit defined integer": -randint(0, 255),
    "negative 16-bit defined integer": -randint(256, 65535),
    "negative 24-bit defined integer": -randint(65536, 16777215),
    "negative 32-bit defined integer": -randint(16777216, 4294967295),
    "negative 64-bit defined integer": -randint(72057594037927936, 18446744073709551615),
    # signed integers don't come from JSON, they're put directly into JSONZ if required
    "big integer": randint(2**2040, INT_UPPER_LIMIT),
    "negative big integer": -randint(2**2040, INT_UPPER_LIMIT),
    "decimal 1": Decimal(f"{randint(0, INT_UPPER_LIMIT)}.{randint(0, INT_UPPER_LIMIT)}"),
    "decimal 2": Decimal(f"-{randint(0, INT_UPPER_LIMIT)}.{randint(0, INT_UPPER_LIMIT)}"),
    "decimal 3": float(randint(2**54, 2**1000)), # Will be in 0.00e+0 form
    "decimal 4": -float(randint(2**54, 2**1000)),
    "object 1": {"meow": "meow"},
    "object 2": {},
    "object 3": {"meow": {}},
    # Bytes skipped as cannot be stored as JSON
    "multi-type array 1": [],
    "multi-type array 2": [[]]*100,
    "null array 1": [None],
    "null array 2": [None]*10_000,
    "bool array 1": [True],
    "bool array 2": [True]*10_000,
    "bool array 3": [False],
    "bool array 4": [False]*10_000,
    "bool array 5": choices([True, False], k=10_000),
    "string array 1": ["".join(chr(x) for x in choices(VALID_UTF8_CHARS, k=100)) for _ in range(1_000)],
    "string array 2": ["".join(chr(x) for x in choices(VALID_UTF8_CHARS, k=2)) for _ in range(10_000)],
    # Speedy string arrays are generated because of JSONZ config settings, not because of JSON content
    "resizing integer array": [-randint(4294967296, 72057594037927935) for x in range(10_000)],
    "negative resizing integer array": [-randint(4294967296, 72057594037927935) for x in range(10_000)],
    "unsigned 8-bit defined integer array": [randint(0, 255) for x in range(10_000)],
    "unsigned 16-bit defined integer array": [randint(256, 65535) for x in range(10_000)],
    "unsigned 24-bit defined integer array": [randint(65536, 16777215) for x in range(10_000)],
    "unsigned 32-bit defined integer array": [randint(16777216, 4294967295) for x in range(10_000)],
    "unsigned 64-bit defined integer array": [randint(72057594037927936, 18446744073709551615) for x in range(10_000)],
    "negative 8-bit defined integer array": [-randint(0, 255) for x in range(10_000)],
    "negative 16-bit defined integer array": [-randint(256, 65535) for x in range(10_000)],
    "negative 24-bit defined integer array": [-randint(65536, 16777215) for x in range(10_000)],
    "negative 32-bit defined integer array": [-randint(16777216, 4294967295) for x in range(10_000)],
    "negative 64-bit defined integer array": [-randint(72057594037927936, 18446744073709551615) for x in range(10_000)],
    "big integer array": [randint(2**2040, INT_UPPER_LIMIT) for x in range(100)],
    "negative big integer array": [randint(2**2040, INT_UPPER_LIMIT) for x in range(100)],
    "decimal array": [Decimal(f"{randint(-INT_UPPER_LIMIT, INT_UPPER_LIMIT)}.{randint(0, INT_UPPER_LIMIT)}") for x in range(100)],
    # special numbers like NaN and infinity are excluded because they're not officially part of the JSON spec and break some decoders
}

multi_type_array_3 = [test_object[x] for x in test_object]
multi_type_array_3.append(copy(multi_type_array_3))
test_object["multi-type array 3"] = multi_type_array_3

for x in test_object:
    print(dumps(test_object[x]))

test_object["object 4"] = copy(test_object)

print(dumps(test_object), end="")