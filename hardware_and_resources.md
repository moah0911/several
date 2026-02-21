   # Hardware & Resource Requirements

## Several: Universal AI Agent Orchestrator

**Version:** 1.0.0  
**Date:** 2026-02-21  
**Status:** Draft  

---

## 1. Overview

This document defines the hardware and resource requirements for running Several. Requirements are specified for three tiers: **Minimum**, **Recommended**, and **High-Performance** configurations.

**Important:** These requirements cover only the Several orchestrator itself. The actual AI agents (Claude Code, Codex, etc.) run as external processes and have their own resource requirements that must be considered separately.

---

## 2. System Requirements

### 2.1 Hardware Specifications

| Component | Minimum | Recommended | High-Performance |
|-----------|---------|-------------|------------------|
| **CPU** | 2 cores (x86_64/ARM64) | 4 cores | 8+ cores |
| **Architecture** | x86_64 or ARM64 | x86_64 or ARM64 | x86_64 or ARM64 |
| **RAM** | 512 MB | 2 GB | 4 GB |
| **Storage** | 100 MB | 500 MB | 2 GB |
| **Network** | Not required for core | Not required for core | Not required for core |
| **Display** | Terminal (80x24) | Terminal (120x40) | Terminal (160x50) |

### 2.2 Software Requirements

| Component | Minimum Version | Recommended | Notes |
|-----------|----------------|-------------|-------|
| **Operating System** | Linux 4.19, macOS 11, Windows 10 (WSL2) | Latest stable | Native Unix preferred |
| **Python** | 3.9 | 3.11+ | Required for runtime |
| **Terminal** | xterm-256color | iTerm2, Alacritty, Windows Terminal | Truecolor support recommended |
| **Shell** | bash, zsh, fish | Any POSIX-compliant | For agent detection |

### 2.3 External Dependencies

| Dependency | Purpose | Installation | Bundled |
|------------|---------|--------------|---------|
| `claude` | Claude Code agent | User-provided | No |
| `codex` | OpenAI Codex agent | User-provided | No |
| `gemini` | Google Gemini CLI | User-provided | No |
| `qwen-code` | Qwen Code agent | User-provided | No |
| `git` | Workspace isolation | System package | No |
| `tmux` | Optional: session persistence | System package | No |

---

## 3. Resource Breakdown

### 3.1 Memory Usage

```
Several Memory Model (per component)
====================================

Base Application:        ~50 MB
├── TUI Framework:       ~20 MB
├── Event Loop:          ~5 MB
├── State Manager:       ~10 MB
└── Buffer Pools:        ~15 MB

Per Active Agent:        ~30 MB (overhead only)
├── Process Wrapper:     ~10 MB
├── Stream Parser:       ~5 MB
├── Output Buffers:      ~10 MB
└── Event Queues:        ~5 MB

Session Persistence:     ~10 MB (SQLite cache)
Logging (per session):   ~5 MB (circular buffer)

Total Formula: 50 MB + (N_agents × 30 MB) + 15 MB overhead
```

**Examples:**
- 2 agents: ~120 MB
- 4 agents: ~180 MB
- 8 agents: ~300 MB
- 16 agents: ~540 MB

### 3.2 CPU Usage

| Scenario | CPU Usage | Notes |
|----------|-----------|-------|
| **Idle** | <1% | Event loop waiting |
| **TUI Updates** | 1-5% | 30fps rendering |
| **1 Agent Running** | 2-10% | Parsing output streams |
| **4 Agents Parallel** | 10-30% | Heavy regex parsing |
| **8+ Agents** | 30-60% | CPU-bound parsing |

**Optimization:** Parsing happens in background threads to avoid blocking UI.

### 3.3 Disk I/O

| Operation | I/O Pattern | Size |
|-----------|-------------|------|
| **Application Startup** | Read | ~20 MB (Python bytecode) |
| **Session Creation** | Write | ~10 KB (SQLite) |
| **Agent Output Logging** | Append | ~100 KB/s per agent |
| **Workspace Creation** | Write | ~1 MB per agent (git worktree) |
| **Session Export** | Write | ~1-10 MB (compressed) |

**Storage Growth:**
- Logs: ~100 MB/day (with rotation)
- Sessions: ~1 MB per 100 tasks
- Cache: Auto-cleared, max 500 MB

### 3.4 Network Usage

Several itself is **offline-capable**. Network usage comes only from:
- Initial installation (pip download)
- Optional: Telemetry (disabled by default)
- Not included: Agent network usage (Claude API calls, etc.)

---

## 4. Scaling Characteristics

### 4.1 Agent Scaling Limits

```
┌─────────────────────────────────────────────────────────────┐
│  Agent Count vs Resource Usage                               │
│                                                              │
│  Agents │ Memory │  CPU   │ Disk I/O │ Latency │ Recommended │
│  ───────┼────────┼────────┼──────────┼─────────┼─────────────│
│    1    │  80MB  │   5%   │  Low     │  <1ms   │    Yes      │
│    2    │ 110MB  │  10%   │  Low     │  <1ms   │    Yes      │
│    4    │ 170MB  │  20%   │  Medium  │  <2ms   │    Yes      │
│    8    │ 290MB  │  40%   │  High    │  <5ms   │    Yes      │
│   16    │ 530MB  │  70%   │  High    │  <10ms  │  Caution    │
│   32    │ 1010MB │  90%   │  Very Hi │  >20ms  │   No*       │
│                                                              │
│  *32+ agents possible but UI becomes unusable               │
│   Use CLI mode instead: several task -a agent1,agent2,...   │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Bottleneck Analysis

| Bottleneck | Threshold | Mitigation |
|------------|-----------|------------|
| **File Descriptors** | 256 soft limit | Increase ulimit -n 4096 |
| **Process Limits** | 1024 per user | Increase ulimit -u 4096 |
| **PTY Devices** | /dev/pts exhaustion | Reuse PTYs, cleanup on exit |
| **SQLite Locks** | Concurrent writes | WAL mode, connection pooling |
| **Terminal Bandwidth** | Scrollback lag | Limit output buffer size |

---

## 5. Platform-Specific Notes

### 5.1 Linux

**Recommended Distributions:**
- Ubuntu 22.04 LTS+
- Debian 12+
- Fedora 38+
- Arch Linux (rolling)

**Kernel Parameters:**
```bash
# /etc/sysctl.conf for high agent counts
fs.file-max = 65536
fs.inotify.max_user_watches = 524288
kernel.pty.max = 4096
```

**Systemd Limits:**
```ini
# /etc/systemd/system.conf
DefaultLimitNOFILE=4096
DefaultLimitNPROC=4096
```

### 5.2 macOS

**Supported Versions:**
- macOS 11 (Big Sur) minimum
- macOS 14 (Sonoma) recommended

**Notable Limits:**
- Default maxfiles: 256 (too low)
- PTY allocation: Dynamic

**Fix Limits:**
```bash
# Add to ~/.zshrc or ~/.bash_profile
ulimit -n 4096
ulimit -u 2048
```

### 5.3 Windows (WSL2)

**Requirements:**
- Windows 10 version 2004+ or Windows 11
- WSL2 with Ubuntu 22.04+

**WSL2 Configuration:**
```ini
# %UserProfile%\.wslconfig
[wsl2]
memory=4GB
processors=4
localhostForwarding=true
```

**Limitations:**
- PTY support less robust than native Linux
- File system performance slower for workspace operations
- Terminal emulator compatibility varies

---

## 6. Agent-Specific Resource Considerations

Since Several orchestrates external agents, total resource usage is:

```
Total Resources = Several + Σ(Agent_i resources)
```

### 6.1 Known Agent Requirements

| Agent | Memory/Instance | CPU | Notes |
|-------|----------------|-----|-------|
| **Claude Code** | 50-200 MB | Low | API-based, minimal local |
| **Codex** | 50-100 MB | Low | API-based |
| **Gemini CLI** | 100-300 MB | Medium | May run local inference |
| **Qwen Code** | 200-500 MB | High | Often local model |
| **Aider** | 100-200 MB | Low | API-based |
| **Custom** | Varies | Varies | User-defined |

### 6.2 Resource Planning Example

**Scenario:** Run Claude + Codex + Gemini simultaneously on 4-core laptop

```
Several Orchestrator:     180 MB (3 agents)
Claude Code:              150 MB
Codex:                    100 MB
Gemini CLI:               250 MB
─────────────────────────────────────
Total Several + Agents:   ~680 MB

Recommended: 2 GB RAM (3x headroom for OS + other apps)
```

---

## 7. Performance Tuning

### 7.1 Environment Variables

| Variable | Default | Tuning |
|----------|---------|--------|
| `SEVERAL_MAX_AGENTS` | 8 | Reduce if memory-constrained |
| `SEVERAL_BUFFER_SIZE` | 65536 | Reduce for memory, increase for throughput |
| `SEVERAL_PARSE_THREADS` | 4 | Match CPU core count |
| `SEVERAL_LOG_LEVEL` | info | Set to warning to reduce I/O |
| `SEVERAL_DB_POOL_SIZE` | 5 | Increase for high concurrency |

### 7.2 Configuration Tuning

```yaml
# ~/.local/share/several/config/config.yaml
performance:
  max_concurrent_agents: 8
  buffer_size: 65536
  parse_threads: 4
  enable_compression: true  # Compress session exports
  
  # Memory management
  max_output_buffer: 10MB   # Per agent
  log_rotation: 5           # Keep 5 log files
  log_max_size: 100MB       # Per file
  
  # UI responsiveness
  refresh_rate: 30          # Hz
  debounce_ms: 16           # Input debouncing
```

### 7.3 System Tuning

**For Development Workstations:**
```bash
# Increase file descriptor limits
ulimit -n 4096

# Enable TCP keepalive for long sessions
sysctl -w net.ipv4.tcp_keepalive_time=60

# Optimize SQLite for write-heavy workload
# (Applied automatically by Several)
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA cache_size=10000;
```

---

## 8. Monitoring & Diagnostics

### 8.1 Built-in Metrics

Several exposes internal metrics via logs:

```
2026-02-21 14:30:22 [METRICS] several.memory_usage=180MB
2026-02-21 14:30:22 [METRICS] several.active_agents=3
2026-02-21 14:30:22 [METRICS] several.event_queue_depth=0
2026-02-21 14:30:22 [METRICS] agent.claude.memory=150MB
2026-02-21 14:30:22 [METRICS] agent.claude.cpu_percent=2.5
```

### 8.2 Resource Monitoring Commands

```bash
# Monitor Several process
htop -p $(pgrep -f "several")

# Check file descriptor usage
ls /proc/$(pgrep -f "several")/fd | wc -l

# Monitor disk I/O
iotop -p $(pgrep -f "several")

# Check PTY allocation
ls /dev/pts/ | wc -l

# Database size
du -h ~/.local/share/several/data/several.db
```

### 8.3 Performance Profiling

```bash
# CPU profiling
python -m cProfile -o several.prof -m several

# Memory profiling
python -m memory_profiler several

# Async debugging
PYTHONASYNCIODEBUG=1 several -v
```

---

## 9. Deployment Scenarios

### 9.1 Personal Laptop (Recommended)

**Specs:** 4 cores, 8 GB RAM, SSD
**Agents:** 2-4 concurrent
**Use Case:** Daily development, comparing model outputs

### 9.2 Workstation

**Specs:** 8+ cores, 32 GB RAM, NVMe SSD
**Agents:** 8-16 concurrent
**Use Case:** AI research, batch processing, team shared

### 9.3 CI/CD Runner

**Specs:** 2 cores, 4 GB RAM, ephemeral
**Agents:** 1-2 concurrent (sequential)
**Use Case:** Automated code review, testing

### 9.4 Remote Server (SSH)

**Specs:** 4 cores, 16 GB RAM, cloud instance
**Agents:** 4-8 concurrent
**Use Case:** 24/7 availability, shared team resource
**Note:** Use `several` CLI mode, TUI over SSH with tmux

---

## 10. Troubleshooting Resource Issues

| Symptom | Cause | Solution |
|---------|-------|----------|
| "Too many open files" | FD limit | `ulimit -n 4096` |
| UI lag/stuttering | High CPU parsing | Reduce agent count, disable animations |
| Memory growth | Output buffer accumulation | Lower `max_output_buffer` |
| "No PTY available" | PTY exhaustion | Kill zombie processes |
| Database locked | Concurrent writes | Enable WAL mode |
| Slow startup | Large log files | Rotate/clear logs |

---
