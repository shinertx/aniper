# ---- Build stage ----
FROM rust:latest as builder

# Install build dependencies for TLS
RUN apt-get update && apt-get install -y libssl-dev pkg-config && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1. Cache dependencies (use workspace lock)
COPY executor/Cargo.toml ./Cargo.toml
COPY Cargo.lock ./Cargo.lock
RUN mkdir -p src && echo "fn main() {}" > src/main.rs
RUN cargo build --release
RUN rm -rf src

# 2. Copy actual source and build
COPY executor/src ./src
RUN cargo build --release

# Strip the binary to reduce its size
RUN strip target/release/executor

# ---- Runtime stage ----
FROM debian:bookworm-slim

# Install necessary runtime dependencies, including SSL certificates
RUN apt-get update && apt-get install -y libssl3 ca-certificates && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the compiled binary from the builder stage
COPY --from=builder /app/target/release/executor /usr/local/bin/executor
ENV RUST_LOG=info
EXPOSE 9184
# Expose the metrics port
EXPOSE 9185
# Optional: use a non-root user for security
# RUN useradd -m appuser && chown -R appuser /app
# USER appuser
CMD ["executor"]
