# Multi-stage build for optimized production image
FROM rust:1.70-slim-bullseye as builder

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    pkg-config \
    libssl-dev \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy Cargo files first for better layer caching
COPY engine/Cargo.toml engine/Cargo.lock ./

# Create a dummy main.rs to build dependencies
RUN mkdir src && echo "fn main() {}" > src/main.rs

# Build dependencies only
RUN cargo build --release && rm -rf src target/release/deps/sol_volume_bot*

# Copy source code
COPY engine/src ./src

# Build the application
RUN cargo build --release

# Production stage
FROM debian:bullseye-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd -r -s /bin/false sol_volume_bot

# Create directories
RUN mkdir -p /app/config /app/data /app/logs
RUN chown -R sol_volume_bot:sol_volume_bot /app

# Copy binary from builder
COPY --from=builder /app/target/release/sol_volume_bot /usr/local/bin/sol_volume_bot

# Copy configuration template
COPY config/example.toml /app/config/

# Set working directory and user
WORKDIR /app
USER sol_volume_bot

# Expose metrics port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# Default command
ENTRYPOINT ["sol_volume_bot"]