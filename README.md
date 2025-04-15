# Zor

<div align="center">
  <img src="assets/card.jpg" alt="Zor Logo" width="100" height="50" />
  <p><i>An Open-Source Claude Code-like Tool</i></p>
  
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
  [![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)
  [![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
</div>

## Overview

Zor is a powerful command-line tool that brings AI-powered code assistance to your terminal. Using the Gemini API, Zor helps you understand, modify, and improve your codebase through natural language.

Think of it as an open-source alternative to tools like Claude Code - your AI pair programmer in the terminal.

## Features

- 🧠 **Contextual Understanding**: Zor analyzes your entire codebase for informed assistance
- 💬 **Interactive Mode**: Have conversations about your code
- ✏️ **Edit Files**: Make changes using natural language instructions
- 🧪 **Generate Tests**: Automatically create tests for your code
- 🔄 **Refactor Code**: Implement complex changes across multiple files
- 🔧 **Git Integration**: Commit changes directly from Zor

## Installation

```bash
pip install zor
```

## Quick Start

1. **Configure your API key**:
   ```bash
   zor setup
   ```

2. **Ask about your code**:
   ```bash
   zor ask "How does the file reading in context.py work?"
   ```

3. **Start an interactive session**:
   ```bash
   zor interactive
   ```

## Documentation

For complete documentation, visit our [Documentation](docs/index.md).

## Example Usage

### Generate Tests

```bash
zor generate_test zor/context.py
```

### Edit a File

```bash
zor edit zor/main.py "Add better error handling to the setup command"
```

### Refactor Code

```bash
zor refactor "Improve error handling across the codebase by using custom exceptions"
```

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

Zor is licensed under the [MIT License](LICENSE).

## Acknowledgements

- Thanks to all contributors who have helped shape this project
- Inspired by tools like Claude Code and GitHub Copilot
