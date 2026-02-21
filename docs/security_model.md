     # Security Model

## Several: Universal AI Agent Orchestrator

**Version:** 1.0.0  
**Date:** 2026-02-21  
**Status:** Draft  

---

## 1. Overview

This document defines the security architecture, threat model, and protective measures for Several. The design prioritizes **defense in depth**, **principle of least privilege**, and **zero trust** for external agents.

**Critical Principle:** Several is an **orchestrator**, not an executor. It does not run AI models directly but manages external CLI processes. Security boundaries must account for this delegation model.

---

## 2. Threat Model

### 2.1 Threat Actors

| Actor | Capability | Motivation | Risk Level |
|-------|-----------|------------|------------|
| **Malicious Agent** | Code execution via CLI | Data exfiltration, persistence | **Critical** |
| **Compromised Dependency** | Supply chain attack | Credential theft | **High** |
| **Local Attacker** | File system access | Session hijacking, data theft | **Medium** |
| **User Error** | Accidental exposure | Data loss, unauthorized access | **Medium** |
| **Network Attacker** | Man-in-the-middle | (Limited: offline tool) | **Low** |

### 2.2 Attack Vectors

```
┌─────────────────────────────────────────────────────────────────┐
│                        ATTACK SURFACE                            │
├─────────────────────────────────────────────────────────────────┤
│  1. AGENT INPUT                                                  │
│     └── Malicious prompt injection → Agent executes harmful code │
│                                                                  │
│  2. AGENT OUTPUT                                                 │
│     └── Control sequence injection → Terminal escape attacks     │
│                                                                  │
│  3. PROCESS SPAWN                                                │
│     └── Command injection via crafted agent configs              │
│                                                                  │
│  4. WORKSPACE ACCESS                                             │
│     └── Agent escapes worktree → Access to user files            │
│                                                                  │
│  5. CONFIGURATION                                                │
│     └── Malicious YAML → Arbitrary code execution                │
│                                                                  │
│  6. LOG FILES                                                    │
│     └── Sensitive data leakage (API keys in output)              │
│                                                                  │
│  7. DATABASE                                                     │
│     └── Unencrypted storage → Credential exposure                │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 Risk Assessment Matrix

| Threat | Likelihood | Impact | Risk | Mitigation Priority |
|--------|-----------|--------|------|---------------------|
| Agent escapes workspace | Medium | High | **Critical** | P0 |
| Prompt injection via output | Medium | High | **Critical** | P0 |
| API key leakage in logs | High | High | **Critical** | P0 |
| Malicious agent config | Low | Critical | **High** | P1 |
| Terminal escape sequences | Medium | Medium | **Medium** | P2 |
| Session hijacking | Low | Medium | **Low** | P3 |

---

## 3. Security Architecture

### 3.1 Defense Layers

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 6: USER EDUCATION                                         │
│  └── Warnings, confirmations, clear indicators of risk          │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 5: AUDIT & MONITORING                                     │
│  └── Comprehensive logging, anomaly detection, integrity checks  │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 4: DATA PROTECTION                                        │
│  └── Encryption at rest, secure deletion, output scrubbing       │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 3: PROCESS ISOLATION                                      │
│  └── Namespaces, chroot, resource limits, seccomp (future)       │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 2: FILE SYSTEM ISOLATION                                  │
│  └── Git worktrees, read-only mounts, strict permissions         │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 1: INPUT VALIDATION                                       │
│  └── Sanitization, allowlists, command injection prevention      │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Component Security Boundaries

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER SPACE                               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐ │
│  │   Several   │    │   User's    │    │   System Files      │ │
│  │  Process    │◀──▶│   Project   │    │   (read-only)       │ │
│  │  (Python)   │    │   Files     │    │                     │ │
│  └──────┬──────┘    └─────────────┘    └─────────────────────┘ │
│         │                                                        │
│         │ Spawns (isolated)                                      │
│         ▼                                                        │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              AGENT PROCESS SANDBOX                           │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │ │
│  │  │   Claude    │  │    Codex    │  │   Gemini/Qwen/etc   │  │ │
│  │  │   Process   │  │   Process   │  │      Process        │  │ │
│  │  │  (PTY)      │  │   (PTY)     │  │      (PTY)          │  │ │
│  │  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │ │
│  │         │                │                    │              │ │
│  │         └────────────────┴────────────────────┘              │ │
│  │                          │                                   │ │
│  │                   Git Worktree (isolated)                    │ │
│  │                   Read-only: System libs                      │ │
│  │                   No access: User home (except XDG dirs)      │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Input Validation & Sanitization

### 4.1 Command Injection Prevention

```python
class CommandBuilder:
    """
    Builds agent commands safely without shell injection.
    
    NEVER use shell=True or string concatenation.
    ALWAYS use list-based commands with proper escaping.
    """
    
    def build(self, agent: Agent, task: Task) -> List[str]:
        # Base command as list
        cmd = [str(agent.command)]
        
        # Add static args from config
        cmd.extend(agent.args)
        
        # Add dynamic args with strict validation
        if agent.supports_workspace:
            # Validate workspace path (must be under Several control)
            if not self._is_valid_workspace(task.workspace):
                raise SecurityError("Invalid workspace path")
            cmd.extend(["--cwd", str(task.workspace)])
        
        # Handle prompt - write to file instead of shell arg
        # Prevents injection via special characters
        prompt_file = self._write_prompt_file(task.prompt)
        cmd.extend(["--prompt-file", str(prompt_file)])
        
        return cmd
    
    def _is_valid_workspace(self, path: Path) -> bool:
        """Ensure path is within Several's workspace directory."""
        resolved = path.resolve()
        allowed_prefix = Path(XDG_DATA_HOME) / "several" / "data" / "workspaces"
        return str(resolved).startswith(str(allowed_prefix))
    
    def _write_prompt_file(self, prompt: str) -> Path:
        """Write prompt to temp file, return path."""
        # Atomic write with restricted permissions
        fd, path = tempfile.mkstemp(
            prefix="several-prompt-",
            dir=self.temp_dir,
            text=True
        )
        os.chmod(path, 0o600)  # User read/write only
        
        with os.fdopen(fd, 'w') as f:
            f.write(prompt)
        
        return Path(path)
```

### 4.2 Agent Configuration Validation

```python
class AgentConfigValidator:
    """
    Validates custom agent YAML configurations.
    Prevents malicious configurations from executing arbitrary code.
    """
    
    ALLOWED_BINARY_PATHS = [
        "/usr/bin/",
        "/usr/local/bin/",
        "/opt/",
        str(Path.home() / ".local/bin"),
    ]
    
    FORBIDDEN_ARGS = {
        "shell": ["--shell", "-c", "/bin/sh", "/bin/bash"],
        "eval": ["eval", "exec"],
        "redirect": [">", ">>", "<", "|", "$(", "`"],
    }
    
    def validate(self, config: Dict) -> ValidationResult:
        errors = []
        
        # 1. Validate command path
        cmd = config.get("command", {}).get("binary", "")
        if not self._is_allowed_path(cmd):
            errors.append(f"Binary path not allowed: {cmd}")
        
        # 2. Validate arguments
        for arg in config.get("command", {}).get("args", []):
            if self._contains_forbidden(arg):
                errors.append(f"Forbidden pattern in arg: {arg}")
        
        # 3. Validate environment variables
        for key, value in config.get("environment", {}).get("vars", {}).items():
            if self._is_dangerous_env(key, value):
                errors.append(f"Dangerous env var: {key}")
        
        # 4. Validate parsing regex (ReDoS prevention)
        for pattern in self._extract_patterns(config):
            if self._has_redos_risk(pattern):
                errors.append(f"Regex may cause ReDoS: {pattern}")
        
        return ValidationResult(valid=len(errors) == 0, errors=errors)
    
    def _is_allowed_path(self, path: str) -> bool:
        """Check if binary path is in allowed locations."""
        resolved = Path(path).resolve()
        return any(
            str(resolved).startswith(str(allowed))
            for allowed in self.ALLOWED_BINARY_PATHS
        )
    
    def _contains_forbidden(self, arg: str) -> bool:
        """Check for shell metacharacters and dangerous patterns."""
        for category, patterns in self.FORBIDDEN_ARGS.items():
            if any(p in arg for p in patterns):
                return True
        return False
```

### 4.3 Output Sanitization

```python
class OutputSanitizer:
    """
    Sanitizes agent output before display/storage.
    Prevents terminal escape sequence attacks and data leakage.
    """
    
    # Patterns that could manipulate terminal
    DANGEROUS_SEQUENCES = re.compile(
        r'\x1b\[[0-9;]*[a-zA-Z]'  # ANSI escape sequences
        r'|\x1b\][0-9;]*\x07'      # OSC sequences
        r'|\x1b\[[\?0-9]*[hl]'     # Set/reset mode
        r'|\x1b#8'                 # DECALN (fill screen)
        r'|\x1b\([0-9A-Za-z]'      # Designate G0 charset
        r'|\x1b[0-9]*;[0-9]*[Hf]'  # Cursor position
    )
    
    # Patterns that might contain secrets
    SECRET_PATTERNS = [
        (re.compile(r'sk-[a-zA-Z0-9]{48}'), '[OPENAI_KEY_REDACTED]'),
        (re.compile(r'[a-zA-Z0-9]{40}'), '[API_KEY_REDACTED]'),  # Generic
        (re.compile(r'password["\']?\s*[:=]\s*["\']?[^\s"\']+'), 'password: [REDACTED]'),
        (re.compile(r'api[_-]?key["\']?\s*[:=]\s*["\']?[^\s"\']+'), 'api_key: [REDACTED]'),
    ]
    
    def sanitize_for_display(self, text: str) -> str:
        """Remove dangerous sequences for terminal display."""
        # Option 1: Strip all ANSI sequences
        clean = self.DANGEROUS_SEQUENCES.sub('', text)
        
        # Option 2: Allow safe formatting only (bold, colors)
        # clean = self._allow_safe_ansi(text)
        
        return clean
    
    def sanitize_for_logs(self, text: str) -> str:
        """Scrub secrets before writing to logs."""
        scrubbed = text
        for pattern, replacement in self.SECRET_PATTERNS:
            scrubbed = pattern.sub(replacement, scrubbed)
        return scrubbed
    
    def sanitize_for_storage(self, text: str, sensitivity: str = "high") -> str:
        """Full sanitization for database storage."""
        text = self.sanitize_for_display(text)
        text = self.sanitize_for_logs(text)
        
        if sensitivity == "high":
            # Additional encryption for highly sensitive outputs
            text = self._encrypt_sensitive(text)
        
        return text
```

---

## 5. Process Isolation

### 5.1 Workspace Isolation

```python
class WorkspaceManager:
    """
    Creates isolated workspaces using git worktrees.
    Prevents agents from accessing files outside their workspace.
    """
    
    async def create_workspace(self, task_id: str, agent_id: str) -> Path:
        """
        Create isolated workspace for agent execution.
        """
        # Base directory under Several control
        base = Path(XDG_DATA_HOME) / "several" / "data" / "workspaces"
        base.mkdir(parents=True, exist_ok=True, mode=0o700)
        
        # Unique workspace name
        workspace_name = f"several-{agent_id}-{task_id}"
        workspace_path = base / workspace_name
        
        # Create git worktree from user's project
        project_root = self._find_git_root(Path.cwd())
        
        if project_root:
            # Use git worktree for efficient copy-on-write
            await self._create_worktree(project_root, workspace_path)
        else:
            # Fallback: shallow copy with rsync
            await self._copy_project(Path.cwd(), workspace_path)
        
        # Restrict permissions
        self._lockdown_workspace(workspace_path)
        
        # Create marker file
        (workspace_path / ".several-workspace").touch(mode=0o600)
        
        return workspace_path
    
    def _lockdown_workspace(self, path: Path) -> None:
        """
        Apply restrictive permissions to workspace.
        """
        # Owner: full access
        # Group: none
        # Other: none
        os.chmod(path, 0o700)
        
        # Set ACLs if available (Linux)
        if sys.platform == "linux":
            subprocess.run(
                ["setfacl", "-b", str(path)],  # Remove all ACLs
                check=False
            )
            subprocess.run(
                ["setfacl", "-m", "u::rwx,g::---,o::---", str(path)],
                check=False
            )
        
        # Mark as immutable (optional, Linux only)
        # chattr +i (requires root, use with caution)
    
    async def _create_worktree(self, source: Path, dest: Path) -> None:
        """
        Create git worktree for copy-on-write isolation.
        """
        # Ensure clean state
        if dest.exists():
            shutil.rmtree(dest)
        
        # Create worktree
        proc = await asyncio.create_subprocess_exec(
            "git", "worktree", "add", "--detach", str(dest),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=source
        )
        
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            raise WorkspaceError(f"Git worktree failed: {stderr.decode()}")
        
        # Configure worktree to ignore .several files
        gitignore = dest / ".gitignore"
        with open(gitignore, "a") as f:
            f.write("\n# Several workspace\n.several-*\n")
```

### 5.2 Process Resource Limits

```python
class ProcessLimiter:
    """
    Applies resource limits to agent subprocesses.
    Prevents resource exhaustion attacks.
    """
    
    def apply_limits(self):
        """
        Apply limits in preexec_fn (Unix only).
        Called in child process before exec().
        """
        import resource
        
        # CPU time: 10 minutes (600 seconds)
        resource.setrlimit(resource.RLIMIT_CPU, (600, 600))
        
        # Memory: 2 GB
        resource.setrlimit(
            resource.RLIMIT_AS, 
            (2 * 1024 * 1024 * 1024, 2 * 1024 * 1024 * 1024)
        )
        
        # File size: 100 MB (prevent disk fill)
        resource.setrlimit(
            resource.RLIMIT_FSIZE,
            (100 * 1024 * 1024, 100 * 1024 * 1024)
        )
        
        # Number of open files: 256
        resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))
        
        # Number of processes: 32 (prevent fork bombs)
        resource.setrlimit(resource.RLIMIT_NPROC, (32, 32))
        
        # Disable core dumps (prevent data leakage)
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        
        # Set umask to restrict file creation
        os.umask(0o077)  # User only, no group/other access
    
    def setup_chroot(self, workspace: Path):
        """
        Setup chroot jail (requires root, optional).
        Ultimate isolation - not enabled by default.
        """
        # This requires root privileges and is complex
        # Consider using containers (Docker/Podman) instead
        pass
```

---

## 6. Data Protection

### 6.1 Encryption at Rest

```python
class DataEncryption:
    """
    Optional encryption for sensitive data.
    Uses AES-256-GCM via cryptography library.
    """
    
    def __init__(self, key: Optional[bytes] = None):
        if key is None:
            # Derive key from user password or system keyring
            key = self._derive_key()
        self.key = key
    
    def encrypt(self, plaintext: str) -> bytes:
        """Encrypt sensitive data before storage."""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        
        aesgcm = AESGCM(self.key)
        nonce = os.urandom(12)
        
        ciphertext = aesgcm.encrypt(
            nonce,
            plaintext.encode('utf-8'),
            associated_data=None
        )
        
        # Store nonce + ciphertext
        return nonce + ciphertext
    
    def decrypt(self, encrypted: bytes) -> str:
        """Decrypt data from storage."""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        
        nonce = encrypted[:12]
        ciphertext = encrypted[12:]
        
        aesgcm = AESGCM(self.key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        
        return plaintext.decode('utf-8')
    
    def _derive_key(self) -> bytes:
        """
        Derive encryption key from system keyring or password.
        """
        import keyring
        
        # Try system keyring first
        key = keyring.get_password("several", "encryption-key")
        if key:
            return base64.b64decode(key)
        
        # Generate new key
        key = os.urandom(32)
        keyring.set_password("several", "encryption-key", base64.b64encode(key).decode())
        
        return key
```

### 6.2 Secure Deletion

```python
class SecureDeletion:
    """
    Securely delete sensitive files.
    """
    
    def secure_delete(self, path: Path, passes: int = 3) -> None:
        """
        Overwrite file before deletion to prevent recovery.
        """
        if not path.exists():
            return
        
        file_size = path.stat().st_size
        
        with open(path, "r+b") as f:
            for pass_num in range(passes):
                # Random data
                f.seek(0)
                f.write(os.urandom(file_size))
                f.flush()
                os.fsync(f.fileno())
                
                # Zeros
                f.seek(0)
                f.write(b'\x00' * file_size)
                f.flush()
                os.fsync(f.fileno())
        
        # Rename before delete (obscure original name)
        temp_name = path.parent / f".several-shred-{uuid.uuid4()}"
        path.rename(temp_name)
        temp_name.unlink()
```

---

## 7. Audit & Monitoring

### 7.1 Security Event Logging

```python
class SecurityAudit:
    """
    Logs security-relevant events for forensics.
    """
    
    SECURITY_EVENTS = {
        "AGENT_SPAWN": "Agent process spawned",
        "AGENT_TERMINATE": "Agent process terminated",
        "WORKSPACE_CREATE": "Workspace created",
        "WORKSPACE_ACCESS_VIOLATION": "Agent attempted to access outside workspace",
        "CONFIG_VALIDATION_FAIL": "Agent config failed security validation",
        "SUSPICIOUS_OUTPUT": "Potentially malicious output detected",
        "PRIVILEGE_ESCALATION": "Agent attempted privilege escalation",
        "SECRET_LEAK": "Potential secret leaked in output",
    }
    
    def log_event(self, event_type: str, details: Dict):
        """Log security event with full context."""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "severity": self._calculate_severity(event_type),
            "details": details,
            "session_id": get_current_session(),
            "user": get_current_user(),
            "hash": self._calculate_hash(details),  # Integrity
        }
        
        # Write to separate security log
        self._write_security_log(event)
        
        # Alert if critical
        if event["severity"] == "CRITICAL":
            self._alert_admin(event)
    
    def _calculate_severity(self, event_type: str) -> str:
        """Map event types to severity levels."""
        critical_events = {
            "WORKSPACE_ACCESS_VIOLATION",
            "PRIVILEGE_ESCALATION",
            "SECRET_LEAK",
        }
        high_events = {
            "SUSPICIOUS_OUTPUT",
            "CONFIG_VALIDATION_FAIL",
        }
        
        if event_type in critical_events:
            return "CRITICAL"
        elif event_type in high_events:
            return "HIGH"
        return "INFO"
```

### 7.2 Integrity Checking

```python
class IntegrityChecker:
    """
    Verifies integrity of Several's own files.
    Detects tampering.
    """
    
    def __init__(self):
        self.manifest_path = Path(XDG_DATA_HOME) / "several" / "manifest.json"
    
    def generate_manifest(self):
        """Generate SHA-256 hashes of all Several files."""
        manifest = {
            "version": get_version(),
            "created_at": datetime.utcnow().isoformat(),
            "files": {}
        }
        
        several_root = Path(__file__).parent
        
        for file_path in several_root.rglob("*.py"):
            relative = file_path.relative_to(several_root)
            manifest["files"][str(relative)] = self._hash_file(file_path)
        
        with open(self.manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
    
    def verify_integrity(self) -> bool:
        """Verify current files match manifest."""
        if not self.manifest_path.exists():
            return False
        
        with open(self.manifest_path) as f:
            manifest = json.load(f)
        
        several_root = Path(__file__).parent
        
        for relative_path, expected_hash in manifest["files"].items():
            file_path = several_root / relative_path
            if not file_path.exists():
                return False
            
            actual_hash = self._hash_file(file_path)
            if actual_hash != expected_hash:
                return False
        
        return True
    
    def _hash_file(self, path: Path) -> str:
        """Calculate SHA-256 hash of file."""
        h = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                h.update(chunk)
        return h.hexdigest()
```

---

## 8. User Safety Features

### 8.1 Dangerous Operation Confirmations

```python
class SafetyConfirmations:
    """
    Require user confirmation for risky operations.
    """
    
    DANGEROUS_PATTERNS = [
        (r'\brm\s+-rf\b', "Recursive delete detected"),
        (r'\bformat\b', "Disk format detected"),
        (r'\bdd\s+if=', "Direct disk write detected"),
        (r'\bmv\s+.*\s+/', "Move to root detected"),
        (r'\bchmod\s+-R\s+777\b', "Overly permissive chmod"),
        (r'\bcurl\s+.*\s*\|\s*sh\b', "Pipe to shell detected"),
        (r'\bwget\s+.*\s*\|\s*bash\b', "Pipe to bash detected"),
    ]
    
    def check_prompt(self, prompt: str) -> SafetyCheck:
        """Check if prompt contains dangerous patterns."""
        warnings = []
        
        for pattern, message in self.DANGEROUS_PATTERNS:
            if re.search(pattern, prompt, re.IGNORECASE):
                warnings.append(message)
        
        if warnings:
            return SafetyCheck(
                safe=False,
                warnings=warnings,
                requires_confirmation=True
            )
        
        return SafetyCheck(safe=True)
    
    def check_agent_output(self, output: str) -> SafetyCheck:
        """Check if agent output contains dangerous commands."""
        # Similar pattern matching for tool calls
        pass
```

### 8.2 Visual Security Indicators

```
TUI Security Indicators:
┌─────────────────────────────────────────────────────────────┐
│  🔒 Secure  │  ⚠️ Unverified Agent  │  🛡️ Sandbox Active    │
└─────────────────────────────────────────────────────────────┘

Agent Pane Security States:
┌─────────────┐
│ 🤖 Claude   │
│ 🔒 Official │  ← Green: Verified official agent
│ ● Running   │
└─────────────┘

┌─────────────┐
│ 🏢 Custom   │
│ ⚠️ Unverified│  ← Yellow: Custom agent, user verified
│ ● Running   │
└─────────────┘

┌─────────────┐
│ 👤 Unknown  │
│ 🛑 Blocked  │  ← Red: Failed validation, blocked
│ ✗ Stopped   │
└─────────────┘
```

---

## 9. Incident Response

### 9.1 Automated Responses

| Detection | Automatic Action | User Notification |
|-----------|-----------------|-------------------|
| Workspace escape attempt | Kill agent, quarantine workspace | Immediate modal |
| Secret in output | Scrub from logs, mask in UI | Toast warning |
| Resource exhaustion | SIGTERM agent, preserve data | Status bar alert |
| Invalid config | Refuse to load agent | Config error message |
| Integrity check fail | Refuse to start | Fatal error dialog |

### 9.2 Manual Response Procedures

**Agent Compromise Suspected:**
1. Kill all agent processes: `several agents kill --all`
2. Export session for forensics: `several sessions export --security`
3. Review security log: `several logs --security`
4. Quarantine workspace: `several workspace quarantine <id>`
5. Report: File issue with security logs

---

## 10. Security Checklist

### For Users

- [ ] Verify agent binaries before adding custom agents
- [ ] Review custom agent configs for malicious patterns
- [ ] Enable encryption for sensitive projects
- [ ] Regularly review security logs
- [ ] Keep Several updated to latest version

### For Developers

- [ ] Run security tests: `pytest tests/security/`
- [ ] Verify all subprocess calls use list args (no shell=True)
- [ ] Check for hardcoded secrets in codebase
- [ ] Validate all YAML parsing with safe_load
- [ ] Ensure all file operations use resolved paths
- [ ] Test with malicious agent configs (fuzzing)

---
