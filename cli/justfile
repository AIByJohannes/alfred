build:
    cargo build --workspace

build-cli:
    cargo build -p alfred-cli

run:
    cargo run -p alfred-cli

dev: run

install:
    cargo install --path crates/alfred-cli --locked

test:
    cargo test --workspace

clean:
    cargo clean

update-prompts:
    mkdir -p prompts
    curl -o prompts/SOUL.md https://raw.githubusercontent.com/AIByJohannes/alfred/refs/heads/main/core/prompts/SOUL.md
