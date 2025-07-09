# ---- Build stage ----
FROM rust:latest as builder

WORKDIR /app

# 1. Cache dependencies
COPY Cargo.toml Cargo.lock ./
COPY executor/Cargo.toml executor/
RUN mkdir executor/src && echo "fn main() {}" > executor/src/main.rs
RUN cargo build --release
RUN rm -rf executor/src

# 2. Copy source and build
COPY executor/ executor/
RUN cargo build --release

# ---- Runtime stage ----
FROM debian:bookworm-slim
WORKDIR /app
# Install OpenSSL 3 and CA certificates for Rust binary
RUN apt-get update && apt-get install -y libssl3 ca-certificates && rm -rf /var/lib/apt/lists/*
COPY --from=builder /app/target/release/executor /usr/local/bin/executor
ENV RUST_LOG=info
CMD ["executor"]
