# Contributing to Hearth

Thanks for your interest in contributing to Hearth!

## Development Setup

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd hearth
   ```

2. **Set up virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   export ENTITY_HOME=/tmp/test_entity
   export ENTITY_USER=test_user
   export XAI_API_KEY=your_test_key
   ```

4. **Verify installation**
   ```bash
   python verify-install.py
   ```

## Project Structure

```
hearth/
├── core/              # Core systems
│   ├── providers/     # AI model providers
│   ├── api.py         # REST API
│   ├── tasks.py       # Task management
│   ├── skills.py      # Skill system
│   └── ...
├── agents/            # Agent implementations
├── web/               # Web UI
│   ├── templates/     # Jinja2 templates
│   └── static/        # CSS/JS assets
├── integrations/      # External integrations
├── docs/              # Documentation
└── tests/             # Test suite (if present)
```

## Making Changes

1. **Create a branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Follow existing code style
   - Add docstrings to new functions
   - Update documentation if needed

3. **Test your changes**
   ```bash
   # Test manually
   python main.py serve

   # Verify nothing broke
   python verify-install.py
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: description of your changes"
   ```

## Commit Message Guidelines

Use conventional commits:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `refactor:` Code refactoring
- `test:` Test additions/changes
- `chore:` Maintenance tasks

## Code Style

- **Python**: Follow PEP 8
- **Docstrings**: Use Google style
- **Type hints**: Use where appropriate
- **Line length**: Max 100 characters

## Adding a New Provider

To add a new AI model provider:

1. Create `core/providers/your_provider.py`:
   ```python
   from .base import BaseProvider, AgentResponse

   class YourProvider(BaseProvider):
       def chat(self, messages, **kwargs) -> AgentResponse:
           # Implementation
           pass
   ```

2. Register in `core/providers/__init__.py`:
   ```python
   from .your_provider import YourProvider

   PROVIDERS = {
       'your_provider': YourProvider,
       # ...
   }
   ```

3. Add to documentation

## Adding Web UI Pages

1. Create template in `web/templates/your_page.html`
2. Add route in `web/app.py`
3. Update navigation in `web/templates/base.html`
4. Test with HTMX if using dynamic features

## Testing

Currently, Hearth uses manual testing. When adding features:

1. Test the feature manually
2. Verify it works with different providers
3. Check Web UI and REST API both work
4. Test with a fresh entity (empty database)

## Documentation

When adding features:
- Update relevant docs in `docs/`
- Add usage examples
- Update README.md if needed

## Pull Request Process

1. Update the README.md with details of changes if needed
2. Update documentation in `docs/`
3. Ensure your code follows the style guidelines
4. Create the pull request with a clear description

## Questions?

Open an issue for:
- Bug reports
- Feature requests
- Questions about the codebase

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
