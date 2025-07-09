# ---- Build stage ----
FROM rust:1.77-slim as builder

WORKDIR /app

# 1. Cache dependencies
COPY executor/Cargo.toml executor/Cargo.lock executor/
RUN mkdir -p executor/src && echo "fn main() {}" > executor/src/main.rs
RUN cd executor && cargo build --release
RUN rm -rf executor/src

# 2. Copy source and build
COPY executor/src executor/src
# Copy any other files needed for build (optional, e.g. .env if needed at build time)
# COPY executor/.env executor/.env
RUN cd executor && cargo build --release

# ---- Runtime stage ----
FROM debian:bookworm-slim
WORKDIR /app
RUN apt-get update && apt-get install -y libssl3 ca-certificates && rm -rf /var/lib/apt/lists/*
COPY --from=builder /app/executor/target/release/executor /usr/local/bin/executor
ENV RUST_LOG=info
CMD ["executor"]
