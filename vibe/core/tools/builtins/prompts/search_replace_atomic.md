Use `search_replace` to make targeted changes to files using `old_string` and `new_string`.

Arguments:
- `file_path`: The path to the file to modify.
- `old_string`: The exact text to replace.
- `new_string`: The text to replace it with.

## CRITICAL REQUIREMENTS:

1.  **UNIQUENESS**: The `old_string` MUST uniquely identify the specific instance you want to change.
    -   Include AT LEAST 3-5 lines of context BEFORE the change point.
    -   Include AT LEAST 3-5 lines of context AFTER the change point.
    -   Include all whitespace, indentation, and surrounding code exactly as it appears in the file.

2.  **SINGLE INSTANCE**: This tool can only change ONE instance at a time. If you need to change multiple instances:
    -   Make separate calls to this tool for each instance.

## Examples:

**Replacing code:**

```python
# To change 'return 42' to 'return sum([1, 2, 3])' inside a function

file_path = "src/calc.py"
old_string = """def calculate(a, b):
    # This is a comment
    print(f"Calculating {a} + {b}")
    return 42

def other_function():"""
new_string = """def calculate(a, b):
    # This is a comment
    print(f"Calculating {a} + {b}")
    return sum([1, 2, 3])

def other_function():"""
```

**Creating a new file:**
Provide `file_path` and `new_string`, leave `old_string` empty (or None).

**Deleting content:**
Provide `file_path` and `old_string`, leave `new_string` empty (or None).
