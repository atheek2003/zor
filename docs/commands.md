# Zor Command Guide

This document provides detailed information about each command available in Zor.

## Core Commands

### `zor ask`

Ask questions about your codebase with contextual awareness.

```bash
zor ask "How does rate limiting work in this project?"
```

**Options**: None


### `zor init`

Create a new project based on natural language instructions.

```bash
zor init "create a modern React portfolio app for a software engineer with dark theme"```
**Arguments**: 
- `--directory` : Specify the directory name for the new project

### `zor edit`

Edit a file based on natural language instructions.

```bash
zor edit path/to/file.py "Add error handling for network failures"
```

**Arguments**:
- `file_path`: Path to the file to edit
- `prompt`: Description of the changes to make

Zor will:
1. Show a diff of proposed changes
2. Ask for confirmation
3. Create a backup of the original file

### `zor interactive`

Start an interactive session with Zor.

```bash
zor interactive
```

This mode allows for back-and-forth conversation about your codebase. You can:
- Ask questions
- Request code explanations
- Edit files
- Generate code

Type `exit` to end the session.

### `zor generate_test`

Generate unit tests for a specific file.

```bash
zor generate_test zor/api.py
```

**Arguments**:
- `file_path`: Path to the file to test

**Options**:
- `--test-framework`: Specify the test framework (default: pytest)

```bash
zor generate_test zor/api.py --test-framework unittest
```

### `zor refactor`

Refactor code across multiple files based on natural language instructions.

```bash
zor refactor "Convert string concatenation to f-strings throughout the codebase"
```

**Arguments**:
- `prompt`: Description of the refactoring to perform

Zor will:
1. Identify affected files
2. Show a summary of changes
3. Display diffs for each file
4. Ask for confirmation
5. Optionally create a git commit

## Configuration Commands

### `zor setup`

Configure your Gemini API key.

```bash
zor setup
```

This interactive command will:
1. Prompt for your API key
2. Validate the key
3. Save it to your configuration

### `zor config`

View or update configuration settings.

```bash
# View all settings
zor config

# View a specific setting
zor config model

# Update a setting
zor config temperature 0.7
```

**Arguments** (all optional):
- `key`: Configuration key to view or update
- `value`: New value for the specified key

## Utility Commands

### `zor commit`

Create a git commit with a specified message.

```bash
zor commit "Fix rate limiting in API module"
```

**Arguments**:
- `message`: Commit message

### `zor history`

Show conversation history with Zor.

```bash
zor history
```

**Options**:
- `--limit`: Number of history items to show (default: 5)

```bash
zor history --limit 10
```

### `zor help`

Display available commands and their descriptions.

```bash
zor help
```

## Tips for Effective Use

1. **Be specific in your prompts**:
   - Good: "Add input validation to the edit_file function in file_ops.py"
   - Less effective: "Make the code better"

2. **Start with interactive mode** to get familiar with Zor's capabilities

3. **Use context in your questions**:
   - "How does the rate limiting work in api.py?" will give better results than
     "How does rate limiting work?"

4. **Generate tests first** when making significant changes to understand the current behavior

5. **Review diffs carefully** before accepting changes
