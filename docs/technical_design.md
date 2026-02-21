  # Technical Design Document

## Several: Universal AI Agent Orchestrator

**Version:** 1.0.0  
**Date:** 2026-02-21  
**Status:** Draft  

---

## 1. System Architecture

### 1.1 Layered Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           PRESENTATION LAYER                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │   Dashboard │  │  AgentGrid  │  │  TaskInput  │  │  StatusBar      │ │
│  │   Screen    │  │   Widget    │  │   Widget    │  │    Widget       │ │
│  │  (Textual)  │  │  (Textual)  │  │  (Textual)  │  │   (Textual)     │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └────────┬────────┘ │
│         └─────────────────┴─────────────────┴─────────────────┘          │
│                                    │                                     │
│                         ┌──────────┴──────────┐                         │
│                         │   Event Dispatcher   │                         │
│                         │   (asyncio.Queue)    │                         │
│                         └──────────┬──────────┘                         │
└────────────────────────────────────┼────────────────────────────────────┘
                                     │
┌────────────────────────────────────┼────────────────────────────────────┐
│                         ORCHESTRATION LAYER                              │
│                                    │                                     │
│  ┌─────────────────────────────────┴─────────────────────────────────┐  │
│  │                      TaskOrchestrator                              │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐   │  │
│  │  │   Parser    │  │  Scheduler  │  │    StateManager         │   │  │
│  │  │  (Input)    │  │ (asyncio)   │  │   (SQLite+aiosqlite)    │   │  │
│  │  └─────────────┘  └──────┬──────┘  └─────────────────────────┘   │  │
│  │                          │                                        │  │
│  │  ┌───────────────────────┴───────────────────────────────────┐   │  │
│  │  │                   AgentManager                             │   │  │
│  │  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────────┐ │   │  │
│  │  │  │Registry │ │Lifecycle│ │ Health  │ │  ProcessPool    │ │   │  │
│  │  │  │ (YAML)  │ │ (async) │ │ (Watch) │ │   (PTY-based)   │ │   │  │
│  │  │  └─────────┘ └─────────┘ └─────────┘ └─────────────────┘ │   │  │
│  │  └───────────────────────────────────────────────────────────┘   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
┌────────────────────────────────────┼────────────────────────────────────┐
│                           ADAPTER LAYER                                  │
│                                    │                                     │
│  ┌─────────────────────────────────┴─────────────────────────────────┐  │
│  │                      BaseAdapter (Abstract)                        │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐  │  │
│  │  │  Claude  │ │   Codex  │ │  Gemini  │ │   Qwen   │ │  Custom │  │  │
│  │  │  Adapter │ │  Adapter │ │  Adapter │ │  Adapter │ │ Adapter │  │  │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬────┘  │  │
│  │       └─────────────┴─────────────┴─────────────┴──────────┘       │  │
│  │                              │                                     │  │
│  │                    ┌─────────┴─────────┐                           │  │
│  │                    │   StreamParser    │                           │  │
│  │                    │ (Regex+Heuristic) │                           │  │
│  │                    └───────────────────┘                           │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
┌────────────────────────────────────┼────────────────────────────────────┐
│                         PROCESS LAYER                                    │
│                                    │                                     │
│  ┌─────────────────────────────────┴─────────────────────────────────┐  │
│  │                    ProcessWrapper (PTY)                            │  │
│  │                                                                    │  │
│  │   ┌──────────┐      ┌──────────┐      ┌──────────┐               │  │
│  │   │  stdin   │─────▶│   PTY    │─────▶│  Agent   │               │  │
│  │   │  writer  │      │  master  │      │   CLI    │               │  │
│  │   └──────────┘      └────┬─────┘      └────┬─────┘               │  │
│  │                          │                  │                      │  │
│  │                    ┌─────┘                  └─────┐                │  │
│  │                    ▼                              ▼                │  │
│  │              ┌──────────┐                  ┌──────────┐           │  │
│  │              │  stdout  │◀─────────────────│   PTY    │           │  │
│  │              │  parser  │                  │  slave   │           │  │
│  │              └──────────┘                  └──────────┘           │  │
│  │                                                                    │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Components

### 2.1 TaskOrchestrator

Central coordinator managing task lifecycle.

```python
class TaskOrchestrator:
    """
    Manages task distribution, scheduling, and result aggregation.
    
    Responsibilities:
    - Parse user input into executable tasks
    - Schedule tasks across selected agents
    - Monitor execution progress
    - Aggregate and store results
    """
    
    def __init__(self, config: Config, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self.agent_manager = AgentManager(config)
        self.state_manager = StateManager(config.data_dir)
        self.scheduler = TaskScheduler()
        self.active_tasks: Dict[str, AgentTask] = {}
    
    async def submit_task(
        self, 
        prompt: str, 
        agents: List[str],
        mode: ExecutionMode = ExecutionMode.PARALLEL
    ) -> TaskResult:
        """
        Submit task to specified agents.
        
        Args:
            prompt: User input string
            agents: List of agent IDs to use
            mode: PARALLEL or SEQUENTIAL execution
        
        Returns:
            TaskResult with aggregated outputs
        """
        task_id = generate_uuid()
        task = Task(id=task_id, prompt=prompt, agents=agents, mode=mode)
        
        # Persist task
        await self.state_manager.save_task(task)
        
        # Dispatch to scheduler
        if mode == ExecutionMode.PARALLEL:
            results = await self.scheduler.run_parallel(task, self.agent_manager)
        else:
            results = await self.scheduler.run_sequential(task, self.agent_manager)
        
        # Aggregate and store
        task_result = TaskResult(task=task, agent_results=results)
        await self.state_manager.save_result(task_result)
        
        return task_result
    
    async def cancel_task(self, task_id: str) -> None:
        """Cancel running task and cleanup."""
        if task_id in self.active_tasks:
            await self.active_tasks[task_id].cancel()
            del self.active_tasks[task_id]
```

### 2.2 AgentManager

Manages agent lifecycle and discovery.

```python
class AgentManager:
    """
    Manages agent registration, discovery, and lifecycle.
    
    Discovery Strategy:
    1. Check PATH for known CLI commands (claude, codex, etc.)
    2. Load custom agents from ~/.several/config/agents/*.yaml
    3. Validate executables and versions
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.registry = AgentRegistry()
        self.process_pool = ProcessPool(max_workers=16)
        self.health_checker = HealthChecker()
    
    async def discover_agents(self) -> List[Agent]:
        """
        Auto-detect installed agent CLIs.
        
        Returns:
            List of available Agent instances
        """
        discovered = []
        
        # Check official agents
        for agent_type in OfficialAgent:
            if await self._check_executable(agent_type.value.command):
                agent = await self._create_agent(agent_type)
                discovered.append(agent)
        
        # Load custom agents
        custom_agents = await self._load_custom_agents()
        discovered.extend(custom_agents)
        
        return discovered
    
    async def spawn_agent(
        self, 
        agent_id: str, 
        task: Task
    ) -> AgentInstance:
        """
        Spawn agent process with proper isolation.
        
        Creates:
        - PTY for interactive support
        - Isolated working directory (git worktree)
        - Environment with sanitized variables
        """
        agent = self.registry.get(agent_id)
        
        # Create isolated workspace
        workspace = await self._create_workspace(task.id, agent_id)
        
        # Build command with args
        cmd = agent.build_command(
            prompt=task.prompt,
            workspace=workspace,
            context=task.context
        )
        
        # Spawn with PTY
        process = await self.process_pool.spawn(
            cmd=cmd,
            env=agent.sanitized_env(),
            cwd=workspace,
            pty=True  # Critical for interactive CLIs
        )
        
        return AgentInstance(
            agent=agent,
            process=process,
            workspace=workspace,
            start_time=datetime.now()
        )
    
    async def terminate_agent(self, instance: AgentInstance) -> None:
        """Graceful shutdown with fallback to kill."""
        try:
            await instance.process.terminate(timeout=5.0)
        except TimeoutError:
            await instance.process.kill()
        finally:
            await self._cleanup_workspace(instance.workspace)
```

### 2.3 StreamParser

Parses agent output streams for events and progress.

```python
class StreamParser:
    """
    Parses stdout/stderr from agent processes.
    
    Uses regex patterns and heuristics to extract:
    - Progress indicators
    - Token usage
    - Tool calls (file edits, commands)
    - Completion status
    - Error conditions
    """
    
    def __init__(self, agent_type: str):
        self.agent_type = agent_type
        self.patterns = self._load_patterns(agent_type)
        self.buffer = ""
        self.state = ParserState.IDLE
    
    def feed(self, chunk: str) -> List[ParseEvent]:
        """
        Process new output chunk.
        
        Returns:
            List of structured events extracted from stream
        """
        self.buffer += chunk
        events = []
        
        # Check for complete lines
        while '\n' in self.buffer:
            line, self.buffer = self.buffer.split('\n', 1)
            event = self._parse_line(line)
            if event:
                events.append(event)
        
        # Check buffer for patterns (progress indicators often inline)
        event = self._parse_buffer(self.buffer)
        if event:
            events.append(event)
            self.buffer = ""  # Consume matched portion
        
        return events
    
    def _parse_line(self, line: str) -> Optional[ParseEvent]:
        """Parse single line against known patterns."""
        for pattern_type, regex in self.patterns.items():
            match = regex.search(line)
            if match:
                return self._create_event(pattern_type, match)
        return None
    
    def _parse_buffer(self, buffer: str) -> Optional[ParseEvent]:
        """
        Parse partial buffer for inline patterns.
        E.g., "Progress: 45%" without newline
        """
        # Progress heuristics
        progress_match = re.search(r'(\d{1,3})%', buffer)
        if progress_match:
            return ProgressEvent(percent=int(progress_match.group(1)))
        
        # Token usage heuristics
        token_match = re.search(r'tokens[:\s]*(\d+)', buffer, re.I)
        if token_match:
            return TokenEvent(count=int(token_match.group(1)))
        
        return None
```

### 2.4 ProcessWrapper

Manages subprocess with PTY support.

```python
class ProcessWrapper:
    """
    Wraps agent CLI subprocess with async I/O and PTY support.
    
    Critical for capturing output from interactive CLIs that
    check isatty() to enable colors and progress bars.
    """
    
    def __init__(
        self,
        cmd: List[str],
        env: Dict[str, str],
        cwd: Path,
        pty: bool = True
    ):
        self.cmd = cmd
        self.env = env
        self.cwd = cwd
        self.pty = pty
        self.pid: Optional[int] = None
        self.master_fd: Optional[int] = None
        self._stdout_queue = asyncio.Queue()
        self._stderr_queue = asyncio.Queue()
        self._stdin_writer: Optional[asyncio.StreamWriter] = None
    
    async def start(self) -> None:
        """Start subprocess with PTY if requested."""
        if self.pty:
            self.master_fd, slave_fd = pty.openpty()
            
            self.process = await asyncio.create_subprocess_exec(
                *self.cmd,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,  # Merged in PTY
                env=self.env,
                cwd=self.cwd,
                close_fds=True
            )
            
            os.close(slave_fd)
            self.pid = self.process.pid
            
            # Start reader task
            asyncio.create_task(self._read_pty())
        else:
            self.process = await asyncio.create_subprocess_exec(
                *self.cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self.env,
                cwd=self.cwd
            )
            self.pid = self.process.pid
            
            # Start readers
            asyncio.create_task(self._read_pipe(self.process.stdout, 'stdout'))
            asyncio.create_task(self._read_pipe(self.process.stderr, 'stderr'))
    
    async def _read_pty(self) -> None:
        """Read from PTY master fd."""
        loop = asyncio.get_event_loop()
        
        while True:
            try:
                # Use selector for non-blocking read
                data = await loop.run_in_executor(
                    None, 
                    os.read, 
                    self.master_fd, 
                    8192
                )
                
                if not data:
                    break
                
                decoded = data.decode('utf-8', errors='replace')
                await self._stdout_queue.put(decoded)
                
            except OSError:
                break
        
        await self._stdout_queue.put(None)  # EOF marker
    
    async def read_stdout(self) -> AsyncIterator[str]:
        """Async iterator for stdout chunks."""
        while True:
            chunk = await self._stdout_queue.get()
            if chunk is None:
                break
            yield chunk
    
    async def write_stdin(self, data: str) -> None:
        """Write to stdin (for interactive prompts)."""
        if self.pty and self.master_fd:
            os.write(self.master_fd, data.encode())
        elif self._stdin_writer:
            self._stdin_writer.write(data.encode())
            await self._stdin_writer.drain()
    
    async def terminate(self, timeout: float = 5.0) -> None:
        """Graceful termination."""
        self.process.terminate()
        
        try:
            await asyncio.wait_for(self.process.wait(), timeout)
        except asyncio.TimeoutError:
            self.process.kill()
            await self.process.wait()
        
        if self.master_fd:
            os.close(self.master_fd)
```

---

## 3. Data Models

### 3.1 Core Entities

```python
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Dict, List, Any
from datetime import datetime
from pathlib import Path

class AgentStatus(Enum):
    IDLE = auto()
    STARTING = auto()
    RUNNING = auto()
    PAUSED = auto()
    COMPLETED = auto()
    ERROR = auto()
    CANCELLED = auto()

class ExecutionMode(Enum):
    PARALLEL = auto()      # All agents simultaneously
    SEQUENTIAL = auto()    # Chain: output of A → input of B

@dataclass
class Agent:
    """Agent configuration and metadata."""
    id: str
    name: str
    type: str  # 'claude', 'codex', 'custom'
    version: str
    command: Path
    args: List[str]
    env: Dict[str, str]
    parser_config: Dict[str, Any]
    icon: str = "🤖"
    color: str = "#FFFFFF"
    max_timeout: int = 300

@dataclass
class Task:
    """User task definition."""
    id: str
    prompt: str
    agents: List[str]
    mode: ExecutionMode
    context: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=datetime.now)
    timeout: int = 300

@dataclass
class AgentResult:
    """Result from single agent execution."""
    agent_id: str
    status: AgentStatus
    output: str
    exit_code: Optional[int]
    tokens_used: int = 0
    tokens_input: int = 0
    tokens_output: int = 0
    duration_ms: int = 0
    files_modified: List[str] = field(default_factory=list)
    tool_calls: List[Dict] = field(default_factory=list)
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None

@dataclass
class TaskResult:
    """Aggregated task result."""
    task: Task
    agent_results: List[AgentResult]
    completed_at: datetime = field(default_factory=datetime.now)
    
    @property
    def success(self) -> bool:
        return all(
            r.status == AgentStatus.COMPLETED 
            for r in self.agent_results
        )
```

### 3.2 Event System

```python
from typing import Protocol
import asyncio

class Event(Protocol):
    """Base event interface."""
    event_id: str
    timestamp: datetime
    agent_id: Optional[str]
    type: str

@dataclass
class ProgressEvent:
    """Agent progress update."""
    event_id: str = field(default_factory=generate_uuid)
    timestamp: datetime = field(default_factory=datetime.now)
    agent_id: Optional[str] = None
    type: str = "progress"
    percent: int = 0
    message: str = ""
    tokens_used: int = 0

@dataclass
class ToolCallEvent:
    """Agent executed a tool."""
    event_id: str = field(default_factory=generate_uuid)
    timestamp: datetime = field(default_factory=datetime.now)
    agent_id: Optional[str] = None
    type: str = "tool_call"
    tool_name: str
    arguments: Dict[str, Any]
    result: Optional[str] = None

@dataclass
class AgentStateEvent:
    """Agent lifecycle event."""
    event_id: str = field(default_factory=generate_uuid)
    timestamp: datetime = field(default_factory=datetime.now)
    agent_id: Optional[str] = None
    type: str = "state_change"
    previous: AgentStatus
    current: AgentStatus
    reason: Optional[str] = None

class EventBus:
    """Async event bus for decoupled communication."""
    
    def __init__(self):
        self._subscribers: Dict[str, List[callable]] = {}
        self._queue = asyncio.Queue()
        self._running = False
    
    def subscribe(self, event_type: str, handler: callable) -> None:
        """Subscribe to event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
    
    async def publish(self, event: Event) -> None:
        """Publish event to all subscribers."""
        await self._queue.put(event)
    
    async def _dispatch_loop(self) -> None:
        """Background task to dispatch events."""
        self._running = True
        while self._running:
            event = await self._queue.get()
            handlers = self._subscribers.get(event.type, [])
            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        asyncio.create_task(handler(event))
                    else:
                        handler(event)
                except Exception as e:
                    logger.error(f"Event handler failed: {e}")
```

---

## 4. Concurrency Model

### 4.1 Async Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Main Thread (asyncio)                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   TUI App   │  │ Orchestrator│  │    Event Dispatch   │  │
│  │  (Textual)  │  │   (async)   │  │      (async)        │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
│         └─────────────────┴────────────────────┘             │
│                          │                                   │
│                   ┌──────┴──────┐                           │
│                   │  asyncio Loop │                           │
│                   │   (uvloop)    │                           │
│                   └──────┬──────┘                           │
└──────────────────────────┼───────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│ Agent Task 1  │  │ Agent Task 2  │  │ Agent Task N  │
│ (subprocess)  │  │ (subprocess)  │  │ (subprocess)  │
│               │  │               │  │               │
│ ┌───────────┐ │  │ ┌───────────┐ │  │ ┌───────────┐ │
│ │ PTY Reader│ │  │ │ PTY Reader│ │  │ │ PTY Reader│ │
│ │  (async)  │ │  │  │  (async) │ │  │  │  (async) │ │
│ └───────────┘ │  │ └───────────┘ │  │ └───────────┘ │
└───────────────┘  └───────────────┘  └───────────────┘
```

### 4.2 Task Scheduling

```python
class TaskScheduler:
    """
    Schedules tasks across agents with parallel/sequential support.
    """
    
    def __init__(self, max_concurrent: int = 8):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def run_parallel(
        self, 
        task: Task,
        agent_manager: AgentManager
    ) -> List[AgentResult]:
        """
        Execute task on all agents simultaneously.
        """
        async def run_single(agent_id: str) -> AgentResult:
            async with self.semaphore:
                instance = await agent_manager.spawn_agent(agent_id, task)
                
                try:
                    result = await self._execute_with_timeout(
                        instance, 
                        task.timeout
                    )
                    return result
                finally:
                    await agent_manager.terminate_agent(instance)
        
        # Create tasks for all agents
        coroutines = [
            run_single(agent_id) 
            for agent_id in task.agents
        ]
        
        # Run with progress tracking
        results = await tqdm_asyncio.gather(
            *coroutines,
            desc=f"Task {task.id[:8]}",
            total=len(coroutines)
        )
        
        return results
    
    async def run_sequential(
        self,
        task: Task,
        agent_manager: AgentManager
    ) -> List[AgentResult]:
        """
        Chain agents: output of agent N → input of agent N+1.
        """
        results = []
        current_prompt = task.prompt
        context = {}
        
        for agent_id in task.agents:
            # Create sub-task with current prompt
            sub_task = Task(
                id=f"{task.id}-{agent_id}",
                prompt=current_prompt,
                agents=[agent_id],
                mode=ExecutionMode.PARALLEL,
                context=context
            )
            
            # Execute
            instance = await agent_manager.spawn_agent(agent_id, sub_task)
            result = await self._execute_with_timeout(instance, task.timeout)
            results.append(result)
            
            # Update prompt for next agent
            current_prompt = result.output
            context['previous_agent'] = agent_id
            context['previous_output'] = result.output
            
            await agent_manager.terminate_agent(instance)
        
        return results
    
    async def _execute_with_timeout(
        self,
        instance: AgentInstance,
        timeout: int
    ) -> AgentResult:
        """Execute agent with timeout and progress tracking."""
        start_time = datetime.now()
        
        try:
            # Create parser for this agent
            parser = StreamParser(instance.agent.type)
            
            # Start output processing
            output_buffer = []
            
            async for chunk in instance.process.read_stdout():
                # Parse for events
                events = parser.feed(chunk)
                for event in events:
                    await self._handle_event(event, instance)
                
                output_buffer.append(chunk)
            
            # Wait for process completion
            exit_code = await asyncio.wait_for(
                instance.process.wait(),
                timeout=timeout
            )
            
            duration = (datetime.now() - start_time).total_seconds() * 1000
            
            return AgentResult(
                agent_id=instance.agent.id,
                status=AgentStatus.COMPLETED if exit_code == 0 else AgentStatus.ERROR,
                output=''.join(output_buffer),
                exit_code=exit_code,
                duration_ms=int(duration),
                tokens_used=parser.total_tokens,
                files_modified=parser.files_modified,
                tool_calls=parser.tool_calls
            )
            
        except asyncio.TimeoutError:
            return AgentResult(
                agent_id=instance.agent.id,
                status=AgentStatus.ERROR,
                output=''.join(output_buffer),
                error_message=f"Timeout after {timeout}s",
                duration_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )
```

---

## 5. Error Handling & Resilience

### 5.1 Error Categories

| Category | Examples | Handling Strategy |
|----------|----------|-------------------|
| **Agent Not Found** | CLI not installed | Mark as absent, skip gracefully |
| **Spawn Failure** | Permission denied, bad path | Retry once, then fail |
| **Runtime Error** | Agent crashed, OOM | Capture stderr, mark failed |
| **Timeout** | Task exceeded limit | SIGTERM, then SIGKILL |
| **Parse Error** | Unknown output format | Log warning, continue with heuristics |
| **Resource Exhaustion** | Too many FDs, memory | Backpressure, queue tasks |

### 5.2 Circuit Breaker Pattern

```python
class CircuitBreaker:
    """
    Prevents cascading failures when agent repeatedly fails.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitState.CLOSED
    
    def record_success(self) -> None:
        self.failures = 0
        self.state = CircuitState.CLOSED
    
    def record_failure(self) -> None:
        self.failures += 1
        self.last_failure_time = datetime.now()
        
        if self.failures >= self.failure_threshold:
            self.state = CircuitState.OPEN
    
    def can_execute(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        
        # Check if recovery timeout passed
        if self.last_failure_time:
            elapsed = (datetime.now() - self.last_failure_time).seconds
            if elapsed > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                return True
        
        return False
```

---

## 6. Integration Points

### 6.1 Agent CLI Interface

Several expects agents to follow this contract:

| Aspect | Requirement |
|--------|-------------|
| **Input** | Prompt via stdin or `--prompt` arg |
| **Output** | stdout (response), stderr (logs) |
| **Exit Code** | 0 = success, non-zero = error |
| **Interactive** | Must work with PTY (isatty) |
| **Cancellation** | Respond to SIGTERM |

### 6.2 Configuration Schema

```yaml
# ~/.local/share/several/config/agents/custom.yaml
name: my-custom-agent
type: custom

command:
  path: /usr/local/bin/my-ai
  args:
    - "--interactive"
    - "--cwd={workspace}"
    - "--context={context_file}"

environment:
  inherit: true  # Inherit parent env
  vars:
    MY_API_KEY: "${MY_API_KEY}"  # From shell env
    LOG_LEVEL: "info"

detection:
  command: "my-ai --version"
  min_version: "1.0.0"
  regex: "version (\\d+\\.\\d+\\.\\d+)"

parsing:
  progress:
    regex: "Progress: (\\d+)%"
    group: 1
  tokens:
    regex: "Tokens: (\\d+)/(\\d+)"
    used_group: 1
    total_group: 2
  tool_call:
    start_regex: "▶ Running: (\\w+)"
    end_regex: "◀ Completed: (\\w+)"
  
  # Heuristic settings
  heuristics:
    enable: true
    idle_timeout: 30  # Seconds before progress stall warning

ui:
  icon: "🚀"
  color: "#FF6B6B"
  label: "My Custom Agent"
```

---
