# ---- Build stage ----
FROM rust:1.77 as builder
WORKDIR /app
COPY . .
RUN cargo build --release

# ---- Runtime stage ----
FROM debian:bullseye-slim
WORKDIR /app
COPY --from=builder /app/target/release/executor /usr/local/bin/executor
ENV RUST_LOG=info
CMD ["executor"]
