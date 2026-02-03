Use `search_replace` to make targeted changes to files using XML SEARCH/REPLACE blocks.

Arguments:
- `file_path`: The path to the file to modify
- `content`: The SEARCH/REPLACE blocks defining the changes

## Format:

```xml
<search_replace>
  <search>[exact text to find in the file]</search>
  <replace>[exact text to replace it with]</replace>
</search_replace>
```

## Examples:

**Single change:**

```xml
<search_replace>
  <search>def old_function():
    return "old value"</search>
  <replace>def new_function():
    return "new value"</replace>
</search_replace>
```

**Multiple changes to the same file:**

```xml
<search_replace>
  <search>import os</search>
  <replace>import os
import sys</replace>
</search_replace>

<search_replace>
  <search>def calculate():
    return 42</search>
  <replace>def calculate():
    return sum([1, 2, 3])</replace>
</search_replace>
```

## IMPORTANT Rules:

- The `<search>` text must match EXACTLY (including whitespace, indentation, and line endings)
- The `<search>` text must appear exactly once in the file - if it appears multiple times, the tool will error
- Content inside `<search>` and `<replace>` tags is used verbatim - no escaping needed
- Each block is applied in order, so later blocks see the results of earlier ones
- Be careful with escape sequences in string literals - use \n not \\n for newlines in code
- The tool will provide detailed error messages with context if search text is not found
