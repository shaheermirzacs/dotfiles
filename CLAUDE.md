# CLAUDE.md - Guidelines for flco-client

## Development Tips

- You are assisting in code development by a company called skylark wireless, often abbreviated sklk
- If you don't know something DO NOT GUESS.
  - Instead think about ways to find documentation (in the case of python you can find the sources usually if there isn't documentation)
- Think about how to keep code simple.
  - Don't put so much effort into converting types to make things work in input in every case
  - It is not necessary for code to never throw exceptions. If bad input is received it is often better to allow the exception to occur than to handle it super gracefully.
- Think about how to avoid repeating code or writing new code.
  - If you aren't familiar with a library we are using (such as if it's internal to skylark) as about documentation or source code location before proceeding.
  - If you know of a library that solves a problem it's a good idea to use it.
  - Ask the user before adding a new library.
- If a test fails after two tries, consider if it might be related to dependency issues
- After two more attempts, if still unable to resolve, move on to another test and make a note
- All code should pass linting checks before committing
- When implementing new components:
  - Initially aim for moderate test coverage of happy paths (not 100% coverage)
  - Wait for code review before investing time in 100% coverage
  - Ask if 100% coverage should be a next step after initial implementation
  - This approach reduces rework if the implementation needs significant changes
- Test both the happy path and critical error conditions
- Remember what directory you are in when working
  - If you're in the toplevel working on code a layer deeper, consider using flags on commands that change directory before invoking (such as make -C, git -C).
- If working on code in a new folder check if there is a claude.md deeper in the hierarchy and read that.
- Avoid writing code that does raw bit manipulation as much as possible. If ever writing such code think about whether it's possible for that to be in a library that has its own unit tests.
- Use `uv` for _everything_. I CANNOT EMPHASIZE THIS ENOUGH
- To add a test dependency use `uv add <dependency> --group test`
- To run anything within the virtual environment, use `uv run`, `uv run coverage -m pytest ...`, etc
- To sync the environment, use `uv sync`. To sync test dependencies use `uv sync --group test`

### Testing Best Practices

- If a test requires a large number of mocks to add a small amount of coverage, don't add it unless specifically requested
- When testing code that emits warnings, use pytest's built-in context manager:

  ```python
  # To test that a specific warning is emitted:
  with pytest.warns(UserWarning, match="expected warning message"):
      result = function_that_should_warn()
  ```

- Avoid mocking objects of low complexity:
  - When an object is easy to create directly, prefer using the real object over a mock
  - If the mock requires setting up many attributes or behaviors, it's often simpler and more robust to use the real object

- When tests fail, consider that the problem might be in the source code, not the test:
  - If a test is failing consistently, investigate if the source code has issues
  - If a test and the source code have mismatching expectations (e.g., enum values), prefer fixing the source code to match documentation and standards
  - Error messages in failing tests can reveal inconsistencies or bugs in the implementation
  - Before modifying tests to work around implementation issues, consider if the implementation should be fixed instead

## Build/Test/Lint Commands

```bash
# Install development dependencies
make dev

# Install project as editable and setup dev environment 
make install

# Run all tests
make test

# Run a single test
uv run pytest test/test_broadcast.py::test_broadcast

# Generate test coverage report
make test-cov

# Linting with Ruff
make lint

# Type checking with mypy
make mypy

# Build documentation
make docs

# Build packages
make pip     # Build pip package
make deb     # Build debian package
```

## Code Style Guidelines

- **Python**: Compatible with Python 3.8+
- **Formatting**: Use Ruff for formatting (4-space indents, double quotes)
- **Line Length**: Follow Ruff defaults (88 characters)
- **Imports**: Group standard library, third-party, then local modules with blank lines between
- **Type Annotations**: Use proper type hints for parameters and return values
- **Naming**: snake_case for variables/functions, CamelCase for classes
- **Docstrings**: Include for functions with parameters and return values documented
- **Error Handling**: Use specific exception types; avoid bare except blocks where possible
- **Logging**: Use the provided logger (sklk_bowser.logger) instead of print statements

## Static Type Checking

- Run `make mypy` frequently during development to catch type errors early
- When adding or modifying code, add appropriate type annotations
- For uncertain cases, use `Optional` and `Union` types
- Use type stubs and docstrings to document function parameters and return types
- Type checking helps catch issues that tests might miss, particularly in error handling paths
- Use type hints from `from __future__ import annotations`
- Import style: EXPLICIT IMPORTS REQUIRED - DO NOT use wildcard imports
  - Imports at top of code always
- Type hints: Add where appropriate, especially on public interfaces
  - If considering using Any as a type annotation think about what could be used
  - It is best practice to choose something specific unless the user asks for general functionality
- Naming: snake_case for functions/variables, CamelCase for classes
