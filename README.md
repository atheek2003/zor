#### Installation
```bash
pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple zor
```

#### Setup
```bash
zor setup
```
Paste your Gemini API key when prompted. You can get your API key from [Gemini](https://ai.google.dev/gemini-api/docs/api-key).

#### To see all the available commands and user manual
```bash
zor help
```

#### To see manual or detailed information about a specific command
```bash
zor <command_name> --help
```

## Some examples of using Zor

#### Ask a question about your codebase
```bash
zor ask "How do I implement rate limiting?"
```

#### Generate tests for a file
```bash
zor generate-test <file_name>.py
```

#### Start an interactive session
```bash
zor interactive
```

#### Edit a file using AI
```bash
zor edit <folder_name>/<file_name>.py "Add better error handling"
```
#### View your configuration
```bash
zor config
```

#### View your command history
```bash
zor history
```
