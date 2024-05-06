# JSONZ - Compressed JSON files for storage and databases

## Contents

- [Introduction](#introduction)
- [Definitions, rules and concepts](#definitions-rules-and-concepts)
- [File structure](#file-structure)
- [Key map](#key-map)
- [How to implement JSONZ](#how-to-implement-jsonz)

## Introduction

JSONZ aims to use characteristics of JSON files to compress them better than general compression algorithms, while still allowing you to quickly access the value of a specified key.

The format prioritises output size over speed, however if configured correctly it should achieve decompression speeds (where "decompression" is conversion back to JSON) similar to general data compression algorithms.

The project aims to create something relatively configurable so that JSONZ may be used in a variety of situations, such as long-term archival storage or real-time database applications.

JSONZ compresses optimally under database conditions, where values such as keys are often repeated, both within the same file and across many files. In circumstances where data is not commonly repeated, consider using a general compression algorithm.

There is a strong likelyhood that this document contains mistakes and I encourage you to make an issue or pull request if you spot one. Any contribution, no matter how small, is appreciated.

# JSONZ version 1 specification

## Definitions, rules and concepts

This specification will repeatedly re-use terms and concepts that will be defined here so that the document may remain concise.

- Resizing integer - An integer that uses less bits to store smaller values. **A resizing integer begins with an unsigned 8-bit integer specifying the size in bytes of the unsigned integer that follows it**. This gives a resizing integer a range between $0$ and $2^{2040}-1$. If other types of integers are used, then this will be specified.
- **All integers will be stored as little-endian**.
- **JSONZ files are typically stored with the .jz extension**. This isn't required, but if a file uses ".jz" it is typically safe to assume that this should be parsed as a JSONZ file. Similarly, a ".jzs" file is typically a JSONZ string data file.
- **Strings are UTF-8 encoded**.

## File structure

Here is an overview of the file's structure in the case that the root object is an object, with the sections following explaining them more in depth.

- [**File metadata**](#file-metadata) - has a defined structure containing essential information about the file.
- [**String data**](#string-data) - an unstructured clump of bytes that can only be made sense of by following the pointers in the string map. Contains a combination of compressed and raw string data.
- [**String map**](#string-map) - define pointers to the locations of string data.
- [**Key map**](#key-map) - defines the relationship between a string ID representing a key, that key's data type and the data associated with that key

In the case that the root object is not an object, the file will contain a version number, the data type of the root object, and then the data for the root object immediately afterwards. See the [File metadata](#file-metadata) section for more details.

### File metadata

Contains essential data for reading the file. It will always be structured as follows:

- **1 byte, an unsigned 8-bit integer - the version number**. If you are following this specification, this should be 1, and you should throw an error given any other value. Future versions may be backwards compatible.
- **1 byte, indicating the data type of the root object**. JSON files typically store other objects, or sometimes arrays. However, JSON allows any data type to be stored without a key associated with it. This low level value without a key is from here on referred to as the root object.
- - **If the data type is an object, then the rest of this document applies**.
- - If the data type is any other type, see [Other data types as the root object](#other-data-types-as-the-root-object)
- **A 64-bit unsigned integer - the number of strings that are used as keys**.
- **A 64-bit unsigned integer - the size of the string data in bytes**.
- **A 64-bit unsigned integer - the size of the string map in bytes**.
- **A 64-bit unsigned integer - the number of JZS files required to load this file**.
- - **If this is not 0: the number of 128-bit sequences specified, representing the MD5 hashes of the JZS files required to use this file**.

Defined integers (instead of resizing integers) are used for the file metadata so that a set amount of space can be left for values to be replaced after the file is finished processing.

### String data files

There are many instances where the data in a JSONZ file, particularly the string value of keys, will be repeated many times across similar files in a dataset. String data files allow you to store a string map that can be shared across multiple JSONZ files.

A JZS file is structured as follows:

- **File metadata**:
- - An 8-bit unsigned integer indicating the version number (1)
- - A 64-bit unsigned integer indicating how many strings the JZS file contains
- - A 64-bit unsigned integer indicating the number of strings that are used as keys
- - A 64-bit unsigned integer indicating the length of the string data in bytes
- **String data**
- **String map**

How to load and use a JZS file will be covered in the [String map](#string-map) section.

### String map

A string map is made up of **integers representing the size of a string in bytes**.

We will use **resizing integers** for this. However, we additionally want to store whether the data is compressed or not. We can store this using **signed resizing integers** (resizing integers that use a signed integer to store its value): **a negative size indicates that the data is raw and uncompressed, and a positive size indicates that the data is Brotli compressed**.

When reading these size values, you should read until the end of the string map - the size of the string map is given in bytes in the file metadata.

When reading these size values, the **sizes refer to string IDs sequentially**: the first size refers string ID 1, the second to string ID 2, etc. The exception to this rule is when one or more JZS files are being used. When a JZS file is loaded, its strings are loaded into the first available string ID slots. Each JZS file fills these slots sequentially, and when the files are exhausted, then the next available string ID slots are used for the string data inside the JSONZ file itself (assuming it has any: the string map can be skipped completely if a byte size of 0 is specified in the file metadata).

In order to load a JZS file, you should first check that the MD5 hash of the entire JZS file matches an MD5 hash in the file metadata. JZS files should be read in the order that the MD5 hashes are written. (An implementation may allow you to manually override this rule, to prevent the need to update millions of hashes across millions of files, but it is then your responsibility to store which JZS files are required and in which order).

Unfortunately, the string map system could enable a denial-of-service attack if your application parses user-generated JSONZ files. A malicious user could create an extremely large string map filled with arbitrary data, since the string map can define pointers for string IDs that doesn't exist, and force your server to parse it. There are a couple of ways you can mitigate this:

1. **Set a limit on the size of string maps.** Remember that a string map does not store the data for the strings, so a large string map should considered suspicious. An example limit would be 10MB: this can store 5 million small strings, and the resizing integers alone would take a Python implementation 5-10 seconds to parse.
2. **Do not parse the entire string map.** Instead, parse when necessary. Parsing the string map is O(n): if you want to access the nth string, you need to parse the map for string IDs 1 through n to retreive the string's location (location caching is recommended).

**All keys that are used as strings should be parsed and stored - these must be at the start of the string map, and the quantity is specified in the file metadata**.

### Other data types as the root object

This section details how the file should be structured in cases where the root object is not an object. All files start with the version number and data type byte, so this information is omitted.

#### Strings and decimals

String data is placed directly after the data type byte, instead of using a string map.

Since there is no size value to store whether a string is compressed or not, we use the special "singular compressed string" to indicate this state. If the data type byte is "string", then the data is uncompressed, and if the data type byte is "singular compressed string" then the data is compressed.

#### Multi-type arrays, object arrays, string arrays and decimal arrays

The above arrays are stored similarly to if the root object is an object (with a string map and string data). The difference to a key map is that with a multi-type array you will be using an index map instead of a key map, and for a defined array you will be using an inferred map from the order of the data.

#### Other

All other types of objects are stored immediately after (or within) the data type byte, without a string map or string data.

## Key map

**A key in the key map must store two things: the string ID of the key, and the data type of the value**. Depending on the data type, various additional data may then be needed.

**The string ID of the key is stored as a resizing integer**.

**JSONZ supports all JSON data types. When read, all\* data is parsed back into a JSON data type. However, there are multiple different data types for storing the data optimally, dependent on its contents**.

JSON supports the following data types: string, number, object, array, boolean, null. The data types JSONZ can use to store data are shown in the table below.

| JSONZ data type                                                        | Data type byte value |
| ---------------------------------------------------------------------- | -------------------- |
| [boolean true](#booleans-null-nan-infinity-and-negative-infinity)      | 1                    |
| [boolean false](#booleans-null-nan-infinity-and-negative-infinity)     | 2                    |
| [null](#booleans-null-nan-infinity-and-negative-infinity)              | 3                    |
| [string](#strings)                                                     | 4                    |
| [resizing integer](#a-note-on-integers)                                | 5                    |
| [negative resizing integer](#a-note-on-integers)                       | 6                    |
| [unsigned 8-bit defined integer](#a-note-on-integers)                  | 7                    |
| [unsigned 16-bit defined integer](#a-note-on-integers)                 | 8                    |
| [unsigned 24-bit defined integer](#a-note-on-integers)                 | 9                    |
| [unsigned 32-bit defined integer](#a-note-on-integers)                 | 10                   |
| [unsigned 64-bit defined integer](#a-note-on-integers)                 | 11                   |
| [negative 8-bit defined integer](#a-note-on-integers)                  | 12                   |
| [negative 16-bit defined integer](#a-note-on-integers)                 | 13                   |
| [negative 24-bit defined integer](#a-note-on-integers)                 | 14                   |
| [negative 32-bit defined integer](#a-note-on-integers)                 | 15                   |
| [negative 64-bit defined integer](#a-note-on-integers)                 | 16                   |
| [signed 8-bit defined integer](#a-note-on-integers)                    | 17                   |
| [signed 32-bit defined integer](#a-note-on-integers)                   | 18                   |
| [signed 64-bit defined integer](#a-note-on-integers)                   | 19                   |
| [big integer](#big-integers)                                           | 20                   |
| [negative big integer](#a-note-on-integers)                            | 21                   |
| [decimal](#decimals)                                                   | 22                   |
| [object](#objects)                                                     | 23                   |
| [bytes*](#bytes)                                                       | 24                   |
| [multi-type array](#multi-type-arrays)                                 | 25                   |
| [boolean array](#boolean-array)                                        | 26                   |
| [null array](#null-array)                                              | 27                   |
| [string array](#string-array)                                          | 28                   |
| [resizing integer array](#resizing-integer-array)                      | 29                   |
| [negative resizing integer array](#resizing-integer-array)             | 30                   |
| [unsigned 8-bit integer array](#defined-integer-array)                 | 31                   |
| [unsigned 16-bit integer array](#defined-integer-array)                | 32                   |
| [unsigned 24-bit integer array](#defined-integer-array)                | 33                   |
| [unsigned 32-bit integer array](#defined-integer-array)                | 34                   |
| [unsigned 64-bit integer array](#defined-integer-array)                | 35                   |
| [negative 8-bit integer array](#defined-integer-array)                 | 36                   |
| [negative 16-bit integer array](#defined-integer-array)                | 37                   |
| [negative 24-bit integer array](#defined-integer-array)                | 38                   |
| [negative 32-bit integer array](#defined-integer-array)                | 39                   |
| [negative 64-bit integer array](#defined-integer-array)                | 40                   |
| [signed 8-bit integer array](#defined-integer-array)                   | 41                   |
| [signed 32-bit integer array](#defined-integer-array)                  | 42                   |
| [signed 64-bit integer array](#defined-integer-array)                  | 43                   |
| [big integer array](#big-integer-array)                                | 44                   |
| [negative big integer array](#big-integer-array)                       | 45                   |
| [decimal array](#decimal-array)                                        | 46                   |
| [object array](#object-array)                                          | 47                   |
| [bytes* array](#bytes-array)                                           | 48                   |
| [NaN](#booleans-null-nan-infinity-and-negative-infinity)               | 49                   |
| [infinity](#booleans-null-nan-infinity-and-negative-infinity)          | 50                   |
| [negative infinity](#booleans-null-nan-infinity-and-negative-infinity) | 51                   |
| [singular compressed string**](#singular-compressed-string)            | 255                  |

*JSONZ can optionally support bytes. Bytes cannot be parsed into JSON and should be stored using the appropriate object within the language your implementation uses. Bytes functionality should be disabled by default, as trying to convert a JSONZ file containing bytes into a JSON file will result in an error.

**Only to be used in the context where a string is a root object. Should be rejected if used in a normal keymap.

**The data type of a key is stored as an 8-bit unsigned integer with a pre-defined code**. The existence of only 52 data types out of a possible 255 makes it very easy for someone to create their own custom data types within an implementation of JSONZ, and I'd recommend making it trivial to do this in your implementation.

### Booleans, null, NaN, infinity and negative infinity

**The value is implied from the data type itself**.

- If the data type is "boolean true", then the value is true.
- If the data type is "boolean false", then the value is false.
- If the data type is "null", then the value is null.
- If the data type is NaN, then the value is NaN.
- If the data type is infinity, then the value is infinity.
- If the data type is negative infinity, then the value is negative infinity.

### Strings

Strings are stored as a string ID. After the data type byte, **use a resizing integer to represent a string ID**.

To read a string:
1. Read the string map until you find the size of the desired string ID.
2. Find the start of the string data. It is directly after the file metadata, so you should cache this position.
3. Move to the position in the string data given by summing the sizes of all previous string IDs in the current file (do not sum the sizes of strings in other files, such as loaded JZS files).
4. Read the number of bytes specified by the absolute value of the size given in the string map.
5. If the size in the string map is negative, decompress the string using Brotli.

### A note on integers

Rather than the traditional idea of a data type, JSONZ calculates which data type can store a piece of data most optimally when a file is written. This makes concepts like signed integers redundant, because **we can instead take advantage of the data type itself to store whether a number is positive or negative**. For example, the integers 727 and -727 will both be stored as the raw unsigned integer 727, but their true value will be interpreted differently dependent on the data type.

This fact is equally reflected in the inclusion of defined and resizing integers: JSONZ will infer at write time which data type would work best. This allows it to maintain flexibility while still optimising as much as is reasonable.

You may notice the inclusion of signed integers as data types. A JSONZ implementation should never use these unless it is explicitly instructed to - these primarily exist so that if a user wants to write a large amount of signed integer data, they can do this without the processing overhead of first parsing them into integers. Instead, the bytes can instead be written directly to the file.

### Resizing and defined integers

Resizing and defined integers are **stored directly after the data type byte**.

A resizing integer is defined as before - start with an 8-bit unsigned integer defining how many bytes the following unsigned integer is.

Positive or negative is described above.

Defined integers take up a defined amount of space. They exist because of their common usage and so a JSONZ implementation may use them to save space over using a resizing integer. See [Determining the type of a value](#number) for more information.

Defined integers have a few benefits and uses:
- They are quicker to parse than resizing integers.
- For certain integers, defined integers can take up less space than a resizing integer.
- If your data is already in encoded as a defined integer, you can write it directly to a JSONZ file instead of having to parse the data into an integer object first.

### Big integers

JSON allows for integers of infinite size. There is no reasonable way we can do this without creating an unacceptably large storage overhead. However, we can create a data type that stores integers that are impossibly large.

A big integer **starts with a resizing integer**. This represents **the number of bytes tha the integer takes up**. This is then followed by the **unsigned integer containing the value**.

Fun fact: the maximum value of a big integer has more than a centillion centillion digits. The repetition is intended.

### Decimals

**JSONZ v1 uses strings to store decimal numbers** as this seems to be the most effective way to store a decimal with infinite precision at this time. This will most likely be one of the first things to be optimised at a later date. **Decimals are stored as a string ID**, the same as strings are.

### Objects

An object **begins with the object's size in bytes** (so it can be skipped when parsing). This is then **followed by the object's key map**.

### Bytes

JSONZ can **optionally** support bytes. **Bytes cannot be parsed into JSON** and should be stored using the appropriate object within the language your implementation uses. **Bytes functionality should be disabled by default**, as trying to convert a JSONZ file containing bytes into a JSON file will result in an error.

A bytes object is first stored by **first using a resizing integer to specify its size in bytes, followed by the bytes themselves**. 

### Multi-type arrays

A multi-type array is stored by first using an **unsigned 64-bit integer representing its size in bytes**. It is then **followed by an index map**. An index map is similar in structure to a key map with one key difference: **string IDs representing keys are omitted**. A multi-type array is structured by the data types and bytes of the data inside it. It is parsed sequentially: the first piece of data is index 0, and so on until the size specified in bytes has been reached. **It is important that your implementation respects the size in bytes specified** and raises an index error when it is exceeded, otherwise you could end up returning garbage data for high indexes.

### Defined type arrays

Defined type arrays are an efficient way of storing arrays that contain only a single type of data. Data type bytes for the objects inside the array are omitted and depending on the type certain optimisations can be used.

Note: You'll notice that many arrays use unsigned 64-bit integers to store the size of the array, but a defined integer array uses a resizing integer. A resizing integer is used for a defined integer array because its size can be calculated using its length, and a resizing integer allows for a larger maximum size. However, in other situations, the size of the array is not known until after the array is written/generated, so an exact size must be used so that an implementation can leave an empty space for the size, write the array, then fill in the size later.

#### Boolean array

A boolean array **begins with a resizing integer containing the array's length (the number of booleans inside the array)**. Boolean arrays then optimise by **using a single bit to store each boolean**. To retrieve the index x in a boolean array you can read the first (x integer division 8 plus 1) bytes, bitwise right shift the data by x, and bitwise AND 1 to get a boolean 1 or 0.

When the number of booleans in an array is not a multiple of 8, **pad the last byte with 0 bits**. For this reason, it is important that you enforce the length of the array in your implementation.

To get the number of bytes a boolean array takes up (so you can skip it), divide the length of the array by 8 and round up (ceiling function).

### Null array

A null array is **a resizing integer specifying its length (the number of null objects in the array)**. Because all the objects are null, no other data is needed.

### String array

A string array **begins with the length of the array in bytes as an unsigned 64-bit integer, followed by sequential resizing integers representing string IDs**. Note that the size of the array in bytes is the amount of space that the string IDs take to store, not the size of the strings themselves.

### Resizing integer array

A resizing integer array **begins with the length of the array in bytes as an unsigned 64-bit integer, followed by the data for the integers**.

Reading a resizing integer array is O(n) because you must parse all integers 0 to n-1 before parsing the nth integer you'd like to retrieve.

### Defined integer array

A defined integer array **begins with the number of integer objects in the array, followed by the data for the integers**.

Reading a defined integer array is skippable and O(1) to access because an index can be multiplied by the size of an integer to calculate its position.

### Big integer array

Structured the **same as a [resizing integer array](#resizing-integer-array)**.

### Decimal array

Structured the **same as a [string array](#string-array)**.

### Object array

An object array **begins with a resizing integer representing the size of the array in bytes**. This is then **followed by the data for the objects**.

### Bytes array

A bytes array is an array of bytes objects. For a collection of bytes, use [bytes](#bytes)

A bytes array **begins with a resizing integer representing the total size of all the bytes objects in the array in bytes** (the unit of size). This is then **followed by the data for the bytes objects**.

### Singular compressed string

Used to represent a compressed string data type when a string is a root object. Invalid in any other context. See [Other data types as the root object](#other-data-types-as-the-root-object)

## How to implement JSONZ

### Reading a resizing integer

1. Read 1 byte.
2. That byte is an unsigned 8-bit integer, convert it to an integer we'll call x.
3. Read x bytes.
4. Those bytes are an unsigned little-endian integer, which is the value of the resizing integer.

Example Python implementation:
```py
def from_ri(byte_stream):
  size = int.from_bytes(byte_stream.read(1))
  return int.from_bytes(byte_stream.read(size), "little")
```

### Writing a resizing integer

1. Let the integer you would like to convert be $i$.
2. If the value is 0, then the resizing integer is a single byte with the value 0.
3. Iterate through the sequence $x=2^{8n}$, starting with n=1. For each value in the sequence, if $i \lt x$, then return x as the "size".
4. Write the "size" as an unsigned 8-bit integer.
5. Write the integer using the "size" number of bytes in unsigned little-endian form.

Python example:
```py
POWERS_OF_TWO = [2**x for x in range(8, 2048, 8)]

def find_ri_size(i):
 for x in range(256):
  if i < POWERS_OF_TWO[x]:
   return x+1
 return 255

def to_ri(i):
 if i == 0:
  return b'\x00'
 size = find_ri_size(i)
 return size.to_bytes(1) + i.to_bytes(size, "little")
```

### Reading a JZ file

1. Start with a JZ file, and 0 or more JZS files. You should calculate the MD5 hash of a JZS file when it is provided and cache it until it is modified.
2. Parse the JZ file metadata. The rest of these instructions assume that the root object is an object.
3. If a hash in the file metadata does not match the hash of one of the provided JZS files (meaning a required JZS file is not present), raise an error.
4. For each file corresponding to a hash in the JZ metadata, in the order the hashes are written:
    - Parse the JZS metadata
    - Read at least the number of strings that are used as keys (specified in the metadata), read the values of these strings from the string data and store them in memory with their associated string IDs
    - Start assigning string IDs from 1 and assign them sequentially. For example, if the first JZS file has 102 strings, then the first string in the second JZS file is string ID 103

(Note: one flaw of this implementation is that every time you update a JZS file, you have to update the associated hash in every JZ file that references that JZS file. To address this flaw, an implementation may allow you to force the loading of a JZS file that is not specified in the JZ file metadata. This removes the requirement to rehash but also means it is your responsibility to store which JZS files are needed for a JZ file to be opened and in what order.)

5. Parse the data in the JZ string map for the strings that are used as keys. Read the values of these strings from the string data and store them in memory.
6. Parse the key map. Construct a dictionary in memory, using string IDs as keys, and using a "skeleton object" as a value. The skeleton object stores different data depending on the data type: for example, a boolean value would store the value of the boolean in its skeleton, whereas a multi-type array would store the byte location of the array and the array's size, so it can be seeked to and parsed only when it's required.

(Note: Parsing of objects is optional. You can either parse objects when parsing the key map, or you can parse an object only when the module tries to access the object's key.)

(Note: It is possible to parse the key map on-demand. This would be useful in a situation where files are frequently opened and closed, as it would reduce latency for reading a single key. However, in a situation where a single file is open for a long period, it would reduce latency consistency, and increase code complexity.)

7. Retreive values as required.

### Writing a JZS file

(Note: It is recommended that you do not immediately overwrite a JZS file. If you wish to update a file, first create a temporary file to work in, then when closing the file delete the original and rename the temporary file to make it permanent. I recommend this because string compression is an expensive task, and using this method you can simply copy the bytes of already compressed strings instead of compressing them again.)

1. Start with two lists of strings you'd like to store, usually strings that are repeated across a number of files. One list, the key list, contains strings that are used as keys. The other, the value list, contains strings that are not used as keys.
2. To your output file, write an 8-bit unsigned integer with a value of the version number (1).
3. Write the number of strings in the list as an unsigned 64-bit integer.
4. Write the number of strings in the key list as an unsigned 64-bit integer.
5. Write 8 empty bytes, you'll overwrite these later.
6. Sort the key list by the number of times each string appears in the associated JZ file, in descending order so the most frequently appearing string is written first. Repeat this for the value list.
7. Write the first string in the key list to the file. At this point you may choose to compress it using the Brotli algorithm, or leave it uncompressed.
8. In a new list, called the sizes list, store the size in bytes of the string you just wrote to the file (after compression, if you compressed it). If you compressed the string, store the value as a negative: a string that is 727 bytes after compression would be stored as -727 in the sizes list.
9. Repeat steps 7-8 for the rest of the strings in the key list.
10. Repeat steps 7-9 for the strings in the value list. You may keep adding to the same sizes list.
11. Write each value in the sizes list in order as a signed resizing integer. To do this, first calculate the logarithm base 2 of the number. Convert the result to bytes by dividing by 8, adding 1 and converting to an integer. Write the result as an unsigned 8-bit integer (using 0 as the value if the calculation resulted in an error). Then, convert the size into a signed integer, with a size in bytes equal to the result of the previous calculation, and write that to the file. Repeat for every size.
12. For each size in the list, calculate its absolute value (or "positive version": 727 becomes 727 and -727 become 727). Then, sum all the results.
13. In the file, seek to the 18th byte (probably seeking to 17 in your language). Then, write the sum as an unsigned 64-bit integer before closing the file.

### Determining the data type of a value

First, determine the JSON data type, then follow the relevant instructions.

#### Booleans, null, NaN, infinity and negative infinity

The data type stores the value. So, for true use [boolean true](#booleans-null-nan-infinity-and-negative-infinity), false use [boolean false](#booleans-null-nan-infinity-and-negative-infinity), null use [null](#booleans-null-nan-infinity-and-negative-infinity), NaN use [NaN](#booleans-null-nan-infinity-and-negative-infinity), infinity use [infinity](#booleans-null-nan-infinity-and-negative-infinity) and negative infinity use [negative infinity](#booleans-null-nan-infinity-and-negative-infinity).

#### String

For a single string, use the [string](#strings) data type, unless the string is the root object. If the string is the root object, then use [singular compressed string](#singular-compressed-string), or for an array of only strings use [string array](#string-array).

#### Number

First, determine if the number is an integer. If not, use [decimal](#decimals) (convert the number to a string).

If the number is an integer, let $x$ be the integer. Use the table below to find the right data type. You do not have to run these checks in the order given, this is simply for readability. For negative numbers, use the same ranges and the corresponding negative data type.

| Condition                                            | Condition (power notation)                  | Data type                                               | Negative data type                                     |
|------------------------------------------------------|---------------------------------------------|---------------------------------------------------------|--------------------------------------------------------|
| $0 \leq x \leq$ 255                                  | $0 \leq x \leq 2^8-1$                       | [unsigned 8-bit defined integer](#a-note-on-integers)   | [negative 8-bit defined integer](#a-note-on-integers)  |
| $256 \leq x \leq 65535$                              | $2^8 \leq x \leq 2^{16}-1$                  | [unsigned 16-bit defined integer](#a-note-on-integers)  | [negative 16-bit defined integer](#a-note-on-integers) |
| $65536 \leq x \leq 16777215$                         | $2^{16} \leq x \leq 2^{24}-1$               | [unsigned 24-bit defined integer](#a-note-on-integers)  | [negative 24-bit defined integer](#a-note-on-integers) |
| $16777216 \leq x \leq 4294967295$                    | $2^{24} \leq x \leq 2^{32}-1$               | [unsigned 32-bit defined integer](#a-note-on-integers)  | [negative 32-bit defined integer](#a-note-on-integers) |
| $4294967296 \leq x \leq 72057594037927935$           | $2^{32} \leq x \leq 2^{56-1}$               | [resizing integer](#a-note-on-integers)                 | [negative resizing integer](#a-note-on-integers)       |
| $72057594037927936 \leq x \leq 18446744073709551615$ | $2^{56} \leq x \leq  2^{64}-1$              | [unsigned 64-bit defined integer](#a-note-on-integers)  | [negative 64-bit defined integer](#a-note-on-integers) |
| $18446744073709551616 \leq x \leq 2^{2040}-1$        | $2^{64}+1 \leq x \leq 2^{2040}-1$           | [resizing integer](#a-note-on-integers)                 | [negative resizing integer](#a-note-on-integers)       |
| $2^{2040} \leq x \leq 2^{2^{2043}-8}-1$              | $2^{2040} \leq x \leq 2^{2^{2043}-8}-1$     | [big integer](#big-integers)                            | [negative big integer](#a-note-on-integers)            |

#### Objects

[Object](#objects)

#### Bytes

[Bytes](#bytes). For data that must be JSON compatible, consider using a string or an integer.

#### Array

Are all of the values in the array of the same type? If no, use a [multi-type array](#multi-type-arrays). If yes, use the other steps in this section to determine the data type of the objects, then use a defined type array, described in the [key map](#key-map) section. Note that when determining the type of something like an integer array can be more difficult, because all integers must fit into the data type you specify.

### Writing a JZ file if the root object is not an object - most types

This section does not cover: strings, decimals, multi-type arrays, object arrays, string arrays and decimal arrays.

1. Start with the data you would like to store.
2. To your output file, write 1 as an unsigned 8-bit integer, the version number.
3. Write to the file an unsigned 8-bit integer, the data type byte for the object you want to store.
4. Write to the file any additional information required. For example, for an integer you would write the value of the integer in the desired format, or for a boolean you would add no additional data.

### Writing a JZ file if the root object is not an object - strings and decimals

1. Start with the string or decimal you'd like to store.
2. To your output file, write 1 as an unsigned 8-bit integer, the version number.
3. Write to the file the "string" data type byte if the data is uncompressed, or the "singular compressed string" data type byte if the data is uncompressed.
4. Write the UTF-8 encoded (and compressed if specified) string data to the file.

### Writing a JZ file if the root object is not an object - string arrays and decimal arrays

1. Start with the array you would like to write.
2. Write 1 as an unsigned 8-bit integer, the version number, to the output file. Write the data type byte of the root object.
3. Write 32 empty bytes (filled with 0s) to leave space for the metadata.
4. Write the MD5 hashes of any JZS files being used, in the order they should be loaded.
5. Create a list of unique strings, ordered by frequency in descending order.
6. Create a second list, this will be called the "string sizes list".
7. For each string in the list:
- Calculate if you would like to store the string as compressed or uncompressed.
- Calculate the size of the output string. If the string is compressed, store this number as negative (an uncompressed 727 byte string would be stored as 727 and a compressed 727 byte string would be stored as -727). Append this value to the string sizes list.
- Write the string to the file.
8. For each size in the string sizes list, write the size to the file as a signed resizing integer. This is identical to [writing a resizing integer](#writing-a-resizing-integer), except that in step 5 you instead write the number in signed little-endian form.
9. Write 8 empty bytes. This is where you will write the size of the array later.
10. For each string in the array, write its string ID as a resizing integer. String IDs start counting from 1 (or, if a JZS was loaded, the first available integer) for the first string you wrote, and increase sequentially for each string written after that.
11. Write the size of the array in the designated location.
12. Fill in the 32 empty bytes from earlier with the appropriate metadata.

### Writing a JZ file if the root object is a object, object array or multi-type array

1. Start with the array or object you would like to write.
2. Write 1 as an unsigned 8-bit integer, the version number, to the output file. Write the data type byte of the root object.
3. Write 32 empty bytes (filled with 0s) to leave space for the metadata.
4. Write the MD5 hashes of any JZS files being used, in the order they should be loaded.
5. Create a list of unique strings used as keys, ordered by frequency in descending order.
6. Create a second list, this will be called the "key string sizes list".
7. For each string in the list:
- Calculate if you would like to store the string as compressed or uncompressed.
- Calculate the size of the output string. If the string is compressed, store this number as negative (an uncompressed 727 byte string would be stored as 727 and a compressed 727 byte string would be stored as -727). Append this value to the key string sizes list.
- Write the string to the file.
8. Create a list of unique strings not used as keys, ordered by frequency in descending order.
9. Create a second list, this will be called the "non-key string sizes list".
10. For each string in the list:
- Calculate if you would like to store the string as compressed or uncompressed.
- Calculate the size of the output string. If the string is compressed, store this number as negative (an uncompressed 727 byte string would be stored as 727 and a compressed 727 byte string would be stored as -727). Append this value to the non-key string sizes list.
- Write the string to the file.
11. For each size in the key string sizes list, write the size to the file as a signed resizing integer. This is identical to [writing a resizing integer](#writing-a-resizing-integer), except that in step 5 you instead write the number in signed little-endian form.
12. Repeat step 11 but for the strings in the non-key string sizes list.
13. Write the data for the array or object. This is usually a multi-step process involving constructing an key map or index map using different types, depending on your data. See [Determining the data type of a value](#determining-the-data-type-of-a-value) and [Key map](#key-map).
14. Fill in the 32 empty bytes from earlier with the appropriate metadata.
