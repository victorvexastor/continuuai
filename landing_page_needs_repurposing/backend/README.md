# IDE Backend

Blazing-fast Rust backend for the NeuAIs Lab IDE with file operations, git integration, and terminal support.

## Features

- ✅ **File Operations**: Tree view, read, write, create, delete
- ✅ **Git Integration**: Status, commit, branches, diff, log (using git2)
- ✅ **Terminal**: Real bash terminal via WebSocket (portable-pty)
- ✅ **CORS Enabled**: Works with React frontend on different port

## Quick Start

```bash
# Build and run
cargo run

# Or build release
cargo build --release
./target/release/ide-backend
```

Server runs on `http://localhost:3002`

## API Endpoints

### File Operations

```
GET    /api/files/tree?path=/         # Get file tree
GET    /api/files/content?path=file   # Get file content
PUT    /api/files/content?path=file   # Save file (body: content)
POST   /api/files/create?path=file    # Create file/folder
DELETE /api/files/delete?path=file    # Delete file/folder
```

### Git Operations

```
GET  /api/git/status           # Git status
GET  /api/git/branches         # List branches
GET  /api/git/log              # Commit history
GET  /api/git/diff?file=path   # File diff
POST /api/git/commit           # Commit (body: {message})
POST /api/git/checkout         # Checkout branch (body: {branch})
```

### Terminal

```
WS /api/terminal               # WebSocket terminal
```

## Workspace

Files are stored in `./workspace/` directory. This directory will be created automatically if it doesn't exist.

## Development

```bash
# Watch mode (requires cargo-watch)
cargo watch -x run

# Check for errors
cargo check

# Run tests
cargo test
```

## Tech Stack

- **Axum** - Web framework
- **git2** - Git operations
- **portable-pty** - Terminal emulation  
- **tokio** - Async runtime
- **serde** - Serialization

## License

MIT
