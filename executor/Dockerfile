# ---- Build stage ----
FROM rust:latest as builder

WORKDIR /app

# 1. Cache dependencies
COPY Cargo.toml Cargo.lock ./
RUN mkdir -p src && echo "fn main() {}" > src/main.rs
RUN cargo build --release
RUN rm -rf src

# 2. Copy source and build
COPY src ./src
RUN cargo build --release

# ---- Runtime stage ----
FROM debian:bookworm-slim
WORKDIR /app
RUN apt-get update && apt-get install -y libssl3 ca-certificates && rm -rf /var/lib/apt/lists/*
COPY --from=builder /app/target/release/executor /usr/local/bin/executor
ENV RUST_LOG=info
EXPOSE 9184
# Optional: use a non-root user for security
# RUN useradd -m appuser && chown -R appuser /app
# USER appuser
CMD ["executor"]
