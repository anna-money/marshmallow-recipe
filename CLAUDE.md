# CLAUDE.md

## Code Practices

### Import Guidelines
- Always use module level imports (except for typing)
- Use relative imports only within marshmallow_recipe package

### Naming Conventions
- **Private methods** must be started with `__`
- **Private fields** must be started with `__` 
- **Protected methods** must be started with `_`

### Code Guidelines
- Use classmethod instead of staticmethod if there are calls to a different static or class method
- **Always use `__slots__`** for classes to optimize memory usage and prevent dynamic attribute assignment
- Define `__slots__` as a tuple listing all instance attributes before the `__init__` method
- Do not use deprecated API
- No local imports
- marshmallow_recipe should work the same as marshmallow_recipe.nuked

### Tests Guidelines
- Always assert objects in full, do not do that field by field

### Development Workflow

- **NEVER commit directly to main branch** - Always create a feature branch first
- **Always run** `make lint` and `make test` before finishing any task. Both must pass without errors
- **Always run** `git add -A` after completing implementation
- **Always ensure** that things work for the versions of marshmallow mentioned in `ci.yml`
- **Always make changes** in-line with code practices within the repository
- All PRs **must be** reflected in CHANGELOG.md
- **When adding new features**: MUST update `examples/` with usage examples and update `context7.json` rules 
- Use Makefile where possible. Ask to modify/add it when you cannot do that.
