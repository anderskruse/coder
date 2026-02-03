Use `search_replace` to make targeted changes to files using SEARCH/REPLACE blocks.

Arguments:
- `file_path`: The path to the file to modify
- `content`: The SEARCH/REPLACE blocks defining the changes

## Format:

```
<<<<<<< SEARCH
[exact text to find in the file]
=======
[exact text to replace it with]
>>>>>>> REPLACE
```

## Examples:

**Single change:**

```
<<<<<<< SEARCH
def old_function():
    return "old value"
=======
def new_function():
    return "new value"
>>>>>>> REPLACE
```

**Multiple changes to the same file:**

```
<<<<<<< SEARCH
import os
=======
import os
import sys
>>>>>>> REPLACE

<<<<<<< SEARCH
def calculate():
    return 42
=======
def calculate():
    return sum([1, 2, 3])
>>>>>>> REPLACE
```

## IMPORTANT Rules:

- The SEARCH text must match EXACTLY (including whitespace, indentation, and line endings)
- The SEARCH text must appear exactly once in the file - if it appears multiple times, the tool will error
- Use exactly 7 angle brackets (or at least 5) for the markers: `<<<<<<<` and `>>>>>>>`
- Use at least 7 equals signs (=======) between SEARCH and REPLACE sections
- The tool will provide detailed error messages with context if search text is not found
- Each search/replace block is applied in order, so later blocks see the results of earlier ones
- Be careful with escape sequences in string literals - use \n not \\n for newlines in code
