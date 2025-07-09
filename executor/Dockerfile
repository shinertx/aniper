# ---- Build stage ----
FROM rust:1.77 as builder

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
COPY --from=builder /app/target/release/executor /usr/local/bin/executor
ENV RUST_LOG=info
CMD ["executor"]
