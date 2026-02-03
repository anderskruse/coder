Use `search_replace` to make targeted changes to files using SEARCH/REPLACE blocks. This tool finds exact text matches and replaces them.

Arguments:
- `file_path`: The path to the file to modify
- `content`: The SEARCH/REPLACE blocks defining the changes

## Format 1: Standard (recommended for most models)  #### KK-code altercation

```
<<<<<<< SEARCH
[exact text to find in the file]
=======
[exact text to replace it with]
>>>>>>> REPLACE
```

#### KK-code altercation BEGIN ####
## Format 2: XML (recommended for Qwen models)

```xml
<search_replace>
  <search>[exact text to find in the file]</search>
  <replace>[exact text to replace it with]</replace>
</search_replace>
```

#### KK-code altercation END ####
You can include multiple SEARCH/REPLACE blocks to make multiple changes to the same file:

**Standard format:**  #### KK-code altercation
```
<<<<<<< SEARCH
def old_function():
    return "old value"
=======
def new_function():
    return "new value"
>>>>>>> REPLACE

<<<<<<< SEARCH
import os
=======
import os
import sys
>>>>>>> REPLACE
```

#### KK-code altercation BEGIN ####
**XML format:**
```xml
<search_replace>
  <search>def old_function():
    return "old value"</search>
  <replace>def new_function():
    return "new value"</replace>
</search_replace>

<search_replace>
  <search>import os</search>
  <replace>import os
import sys</replace>
</search_replace>
```

#### KK-code altercation END ####
IMPORTANT:

- The SEARCH text must match EXACTLY (including whitespace, indentation, and line endings)
- The SEARCH text must appear exactly once in the file - if it appears multiple times, the tool will error
#### KK-code altercation BEGIN ####
- For standard format: Use at least 5 equals signs (=====) between SEARCH and REPLACE sections
- For XML format: Content inside `<search>` and `<replace>` tags is used verbatim
#### KK-code altercation END ####
- The tool will provide detailed error messages showing context if search text is not found
- Each search/replace block is applied in order, so later blocks see the results of earlier ones
- Be careful with escape sequences in string literals - use \n not \\n for newlines in code
- **If you are a Qwen model, use the XML format for better results**  #### KK-code altercation
