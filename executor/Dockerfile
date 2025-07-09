# ---- Build stage ----
FROM rust:1.77 as builder

WORKDIR /app

# 1. Cache dependencies
COPY Cargo.toml Cargo.lock ./
RUN mkdir src && echo "fn main() {}" > src/main.rs
RUN cargo build --release
RUN rm -rf src

# 2. Copy source and build
COPY . .
RUN cargo build --release

# ---- Runtime stage ----
FROM debian:bookworm-slim
WORKDIR /app
COPY --from=builder /app/target/release/executor /usr/local/bin/executor
ENV RUST_LOG=info
CMD ["executor"]
