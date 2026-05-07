# Zeotap Durable Execution Engine

**GitHub:** [https://github.com/Krishna-IITB/zeotap-durable-engine](https://github.com/Krishna-IITB/zeotap-durable-engine)

---

## 📋 Submission Information

**Assignment:** Software Engineer Intern - Zeotap  
**Submitted By:** Krishna, IIT Bombay (Electrical Engineering - Dual Degree)  
**Submission Deadline:** January 26, 2026  
**Contact:** krishnasingh89200@gmail.com  

This repository contains Assignment 1: Building a Native Durable Execution Engine. All code, tests, and documentation are included. The assignment demonstrates crash recovery, parallel execution, and automatic sequence ID generation (bonus challenge).

---

## Overview

A production-ready durable workflow execution engine that survives process crashes and resumes from the exact point of failure. Unlike standard programs where a crash wipes memory and requires a full restart, this engine uses SQLite persistence to enable crash recovery, memoization, and parallel execution.

Inspired by durable execution patterns used in DBOS, Temporal, Cadence, and Azure Durable Functions.

---

## Key Features

- **Crash Recovery**: Process can die at any point and resume without re-executing completed steps
- **Memoization**: Completed steps are automatically cached and skipped on restart
- **Parallel Execution**: Multiple steps can run concurrently with thread-safe database writes
- **Loop Support**: Handles loops with unique sequence tracking per iteration
- **Conditional Logic**: Supports branching (if/else) without ID collisions
- **Type Safety**: Generic-based Step primitive supports any return type
- **Zero DSLs**: Pure idiomatic Go code, no custom XML or orchestrators
- **Automatic Sequence IDs**: No manual step ID management (Bonus Challenge Implemented)

---

## Architecture

### Core Components

```
zeotap-durable-engine/
├── engine/
│   ├── context.go            # Workflow execution context
│   ├── step.go               # Generic step primitive
│   ├── storage.go            # SQLite persistence layer
│   ├── workflow.go           # Workflow runner
│   └── workflow_test.go      # Automated tests
├── examples/
│   ├── onboarding/           # Employee onboarding workflow
│   ├── loop_test/            # Loop iteration tracking
│   ├── conditional_test/     # Branching logic
│   └── zombie_test/          # Crash-before-save recovery
├── main/
│   └── main.go               # CLI entry point
├── go.mod
├── go.sum
├── README.md
└── Prompts.txt
```

### How It Works

1. **Step Execution**: Developer wraps side-effect code in `engine.Step()`
2. **Memoization Check**: Engine queries SQLite to see if step already completed
3. **Conditional Execution**: If cached, return stored result. If not, execute function
4. **Persistence**: Save result to database with unique key (workflow_id + step_key)
5. **Crash Recovery**: On restart, completed steps are skipped, incomplete steps re-execute

### Sequence Management (Bonus Challenge)

To support loops and conditional logic, the engine uses an atomic counter to generate unique step keys:

```go
// Context maintains a sequence counter
func (c *Context) getNextSequence() int64 {
    return atomic.AddInt64(&c.sequenceID, 1)
}

// Step keys are generated as: <step_id>_<sequence>
// Example: loop_step_1, loop_step_2, loop_step_3
```

This ensures:
- Same step ID called multiple times gets unique database keys
- No manual string ID management required
- Thread-safe using atomic operations

---

## Database Schema

**Table: steps**

| Column | Type | Description |
|--------|------|-------------|
| workflow_id | TEXT | Unique identifier for workflow instance |
| step_key | TEXT | Step ID + sequence number (e.g., "create_record_1") |
| status | TEXT | Execution status ("completed") |
| output | TEXT | JSON-serialized step result |

**Primary Key:** `(workflow_id, step_key)` - Ensures no duplicate steps per workflow

### SQL Schema

```sql
CREATE TABLE IF NOT EXISTS steps (
  workflow_id TEXT NOT NULL,
  step_key    TEXT NOT NULL,
  status      TEXT NOT NULL,
  output      TEXT,
  PRIMARY KEY (workflow_id, step_key)
);
```

---

## Quick Start

### Prerequisites

- Go 1.21 or higher
- SQLite (automatically included via mattn/go-sqlite3)

### Installation

```bash
# Clone repository
git clone https://github.com/Krishna-IITB/zeotap-durable-engine.git
cd zeotap-durable-engine

# Install dependencies
go mod download

# Build application
go build -o app ./main
```

### Basic Usage

```bash
# Run a workflow
./app workflow_001 onboarding

# Run with specific demo
./app demo onboarding           # Employee onboarding
./app loop_demo loop            # Loop test
./app zombie_demo zombie        # Zombie step test
```

### Crash Simulation

```bash
# Start workflow
./app workflow_001 onboarding

# Press Ctrl+C after Step 1 completes (simulates crash)
^C

# Resume (same workflow_id) - Step 1 will be skipped
./app workflow_001 onboarding
```

### Database Inspection

```bash
# View all completed steps
sqlite3 workflow.db "SELECT workflow_id, step_key, status FROM steps;"

# View full details
sqlite3 workflow.db "SELECT * FROM steps;"
```

---

## Usage Examples

### 1. Employee Onboarding Workflow

```bash
./app workflow_001 onboarding
```

**Steps:**
- Step 1: Create employee record (sequential)
- Step 2 & 3: Provision laptop + Setup email access (parallel - 33% faster)
- Step 4: Send welcome email (sequential)

**Crash Recovery Test:**

```bash
# Start workflow
./app workflow_001 onboarding

# Press Ctrl+C after Step 1 completes
^C

# Resume - Step 1 will be skipped!
./app workflow_001 onboarding
```

### 2. Loop Support Test

```bash
./app loop_demo loop
```

Demonstrates sequence tracking for 3 iterations of the same step.

### 3. Conditional Logic Test

```bash
./app cond_demo conditional
```

Shows branching (if/else) without step ID collisions.

### 4. Zombie Step Problem Test

```bash
./app zombie_demo zombie

# Press Ctrl+C during "3 second delay" message
# Resume to see crash-before-save recovery
./app zombie_demo zombie
```

---

## Testing

### Automated Tests

```bash
# Run unit tests with verbose output
go test ./engine -v

# Expected output:
# === RUN   TestStepMemoization
# --- PASS: TestStepMemoization (0.00s)
# === RUN   TestConcurrentWrites
# --- PASS: TestConcurrentWrites (0.00s)
# PASS
# ok      zeotap-durable-engine/engine    0.123s
```

**Tests Included:**
- `TestStepMemoization`: Verifies steps execute once and skip on re-run
- `TestConcurrentWrites`: Validates thread-safe parallel database writes

### Manual Test Coverage

| Test Scenario | Validated |
|--------------|-----------|
| Basic workflow execution | ✅ |
| Crash recovery (onboarding) | ✅ |
| Idempotency (skip completed) | ✅ |
| Parallel execution timing | ✅ (4.4s vs 6s) |
| Thread safety | ✅ (no SQLITE_BUSY) |
| Loop support | ✅ |
| Loop crash recovery | ✅ |
| Conditional logic | ✅ |
| Zombie step handling | ✅ |

---

## Non-Functional Features

### Performance Optimizations

- **Lock-Free Sequence Generation**: Uses `atomic.AddInt64()` for O(1) step ID generation
- **Query Optimization**: Single database query per step check (no N+1 problems)
- **Parallel Execution**: Concurrent steps execute simultaneously (33% faster: 4.4s vs 6s)
- **Minimal Memory Footprint**: Streams results without loading entire workflow history
- **Connection Pooling**: SQLite connection reused across workflow execution

### Security

- **SQL Injection Protection**: All queries use parameterized statements (? placeholders)
- **Input Validation**: Workflow IDs validated before database operations
- **Error Safety**: Errors logged with context but don't expose internal details
- **No Hardcoded Credentials**: Database path is configurable

### Reliability & Resilience

- **Atomic Database Operations**: All writes are transactional (all-or-nothing)
- **Crash Recovery**: Process can terminate at any point and resume cleanly
- **Zombie Step Handling**: 
  - **Problem**: Process crashes after step executes but before database save
  - **Solution**: Step re-executes on resume (at-least-once semantics)
  - **Guarantee**: No persisted state is lost; idempotent operations recommended to avoid duplicate side-effects
  - **Example**: Database UPSERTs, check-before-write patterns ensure safety
- **Thread-Safe Writes**: Mutex-based synchronization (serialized writes on single DB connection) prevents SQLITE_BUSY errors
- **At-Least-Once Execution**: Idempotent operations recommended for exactly-once semantics

### Observability & Debugging

- **Structured Logging**: Clear prefixes ([RUN], [SKIP], [DONE]) for step lifecycle
- **Step Tracing**: Every step logged with unique key (e.g., `create_record_1`)
- **Database Inspection**: SQLite file can be queried directly for workflow state

```bash
sqlite3 workflow.db "SELECT * FROM steps;"
```

- **Error Context**: All errors include step ID, workflow ID, and operation type

### Concurrency Model

- **Goroutine-Based Parallelism**: Steps can spawn goroutines for fan-out execution
- **Fan-In Pattern**: Parent step waits for all parallel children via channels
- **Mutex Protection**: Database writes are serialized to prevent race conditions (single connection with mutex lock)
- **No Deadlocks**: Lock acquisition order is consistent

---

## Known Limitations

- **At-Least-Once Semantics**: If process crashes after step execution but before database save, step will re-execute on resume. Recommend idempotent operations (e.g., UPSERTs, check-before-write).
- **Single-Node Engine**: Designed for single-process execution. Multi-node distributed durability requires additional coordination (out of scope).
- **SQLite Concurrency**: Mutex-based writes eliminate SQLITE_BUSY in typical scenarios, but extreme contention may surface transient errors.

---

## Assignment Requirements Checklist

### Deliverables

- ✅ **engine/**: Core library with Context, Step primitive, Storage, and Workflow runner
- ✅ **examples/onboarding/**: Employee onboarding with sequential + parallel steps
- ✅ **main/App**: CLI tool for starting workflows and simulating crashes
- ✅ **README.md**: This comprehensive documentation
- ✅ **Prompts.txt**: All prompts utilized across AI tooling

### Functional Requirements

- ✅ **Workflow Runner**: NewWorkflow() and Run() implemented
- ✅ **Step Primitive**: Generic Step[T any]() with type safety
- ✅ **Resilience**: Crash recovery tested extensively
- ✅ **Concurrency**: Parallel steps with thread-safe database writes

### Persistence Layer

- ✅ **RDBMS**: SQLite with proper schema
- ✅ **Steps Table**: workflow_id, step_key, status, output
- ✅ **Unique Constraint**: Composite primary key prevents duplicates
- ✅ **Serialization**: JSON for storing step results

### Technical Constraints

- ✅ **Type Safety**: Go generics used throughout
- ✅ **Serialization**: Standard encoding/json library
- ✅ **No DSLs**: Pure idiomatic Go code

### Evaluation Criteria

- ✅ **Correctness**: Skips completed steps on restart
- ✅ **Concurrency**: Handles parallel writes without SQLITE_BUSY
- ✅ **Cleanliness**: Idiomatic Go API, clear function signatures
- ✅ **Resilience**: Zombie step problem solved
- ✅ **Testcases**: Automated tests included

### Bonus Challenge

- ✅ **Automatic Sequence ID**: Implemented using atomic counter (no manual IDs needed)

---

## API Reference

### Step Primitive Signature

```go
// Generic step function - supports any return type
func Step[T any](ctx *Context, id string, fn func() (T, error)) (T, error)
```

### Creating a Workflow

```go
wf, err := engine.NewWorkflow("./workflow.db")
if err != nil {
    log.Fatal(err)
}
defer wf.Close()

err = wf.Run("workflow_id", func(ctx *engine.Context) error {
    // Define your workflow here
    return nil
})
```

### Defining Steps

```go
// Sequential step
result, err := engine.Step(ctx, "step_name", func() (ReturnType, error) {
    // Your side-effect code here
    return value, nil
})

// Parallel steps (using goroutines)
errCh := make(chan error, 2)

go func() {
    _, err := engine.Step(ctx, "parallel_step_1", func() (string, error) {
        return "result1", nil
    })
    errCh <- err
}()

go func() {
    _, err := engine.Step(ctx, "parallel_step_2", func() (string, error) {
        return "result2", nil
    })
    errCh <- err
}()

// Wait for completion
for i := 0; i < 2; i++ {
    if err := <-errCh; err != nil {
        return err
    }
}
```

---

## Troubleshooting

**Issue:** `database is locked` error  
**Cause:** Multiple concurrent writes without proper synchronization  
**Solution:** Engine uses mutex protection - ensure you're not opening multiple workflow instances

**Issue:** Steps re-execute every time  
**Cause:** Workflow ID is changing between runs  
**Solution:** Use the same workflow ID when resuming

**Issue:** Database file not found  
**Cause:** Relative path issues  
**Solution:** Use absolute path or ensure working directory is correct

---

## Performance Benchmarks

### Parallel vs Sequential Execution

**Test:** Employee onboarding with 2 parallel steps (laptop + email)

| Execution Mode | Time | Improvement |
|---------------|------|-------------|
| Sequential | 6.0s | Baseline |
| Parallel (Implementation) | 4.4s | **33% faster** |

**Conclusion:** Parallelism provides significant speedup for I/O-bound operations.

---
