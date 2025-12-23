# syntax = docker/dockerfile:1

# Build stage
FROM rust:1.75-slim as builder

WORKDIR /app

# Install dependencies for git2 and openssl
RUN apt-get update && apt-get install -y \
    pkg-config \
    libssl-dev \
    libgit2-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy manifests
COPY Cargo.toml Cargo.lock ./

# Copy source code
COPY src ./src

# Build for release
RUN cargo build --release

# Runtime stage
FROM debian:bookworm-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    ca-certificates \
    libgit2-1.5 \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Copy the binary from builder
COPY --from=builder /app/target/release/ide-backend /app/ide-backend

# Create workspace directory
RUN mkdir -p /app/workspace

# Expose port
EXPOSE 3002

# Run the binary
CMD ["/app/ide-backend"]
