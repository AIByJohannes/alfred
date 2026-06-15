use std::io::{self, BufRead, Write};
use std::path::PathBuf;

use alfred_core::{AgentEvent, AgentRouter, Message, Role};
use alfred_core::providers::openrouter::OpenRouterProvider;
use alfred_tools::config::Config;
use anyhow::Result;
use serde::{Deserialize, Serialize};

const ACP_VERSION: &str = "1";
const DEFAULT_SYSTEM_PROMPT: &str = include_str!("../../../../prompts/SOUL.md");

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type")]
enum AcpClientMessage {
    #[serde(rename = "session.start")]
    SessionStart {
        session_id: String,
        cwd: Option<String>,
    },
    #[serde(rename = "prompt.send")]
    PromptSend { prompt: String },
    #[serde(rename = "session.cancel")]
    SessionCancel,
    #[serde(rename = "session.close")]
    SessionClose,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
enum AcpServerEvent {
    Meta {
        session_id: String,
        cwd: String,
        backend: String,
        transport: String,
        version: String,
    },
    Delta { content: String },
    ToolRequest { name: String, arguments: serde_json::Value },
    ToolResult { name: String, output: String, is_error: bool },
    Artifact { label: String, path: Option<String>, url: Option<String> },
    Done { result: String },
    Error { message: String, exit_code: Option<i32> },
}

impl AcpServerEvent {
    fn emit(&self) {
        let line = serde_json::to_string(self).expect("acp event serializes");
        println!("{}", line);
        io::stdout().flush().ok();
    }
}

pub async fn run_acp(cwd: Option<PathBuf>) -> Result<()> {
    if let Some(ref dir) = cwd {
        std::env::set_current_dir(dir)?;
    }

    let config = Config::load().await.unwrap_or_default();
    let api_key = match std::env::var("OPENROUTER_API_KEY").ok().or(config.openrouter_api_key.clone()) {
        Some(key) if !key.is_empty() => key,
        _ => {
            AcpServerEvent::Error {
                message: "No OpenRouter API key found. Set OPENROUTER_API_KEY or configure it.".to_string(),
                exit_code: Some(1),
            }
            .emit();
            std::process::exit(1);
        }
    };

    let stdin = io::stdin();
    let mut stdin_lock = stdin.lock();
    let mut session: Option<ActiveSession> = None;
    let mut fatal_errors = 0;

    loop {
        let mut line = String::new();
        match stdin_lock.read_line(&mut line) {
            Ok(0) => break,
            Ok(_) => {}
            Err(e) => {
                eprintln!("{{\"type\":\"error\",\"message\":\"stdin read error: {}\"}}", e);
                break;
            }
        }

        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }

        let msg: AcpClientMessage = match serde_json::from_str(trimmed) {
            Ok(m) => m,
            Err(e) => {
                fatal_errors += 1;
                eprintln!(
                    "{{\"type\":\"error\",\"message\":\"Failed to parse ACP message: {}\"}}",
                    e
                );
                if fatal_errors >= 3 {
                    break;
                }
                continue;
            }
        };

        match msg {
            AcpClientMessage::SessionStart { session_id, cwd } => {
                let resolved_cwd = cwd
                    .map(PathBuf::from)
                    .filter(|p| p.is_dir())
                    .unwrap_or_else(|| std::env::current_dir().unwrap_or_default());

                let model = std::env::var("OPENROUTER_MODEL")
                    .ok()
                    .filter(|s| !s.trim().is_empty())
                    .unwrap_or_else(|| "deepseek/deepseek-v4-flash".to_string());
                session = Some(ActiveSession {
                    session_id,
                    cwd: resolved_cwd,
                    provider: OpenRouterProvider::new(api_key.clone(), model),
                });

                if let Some(ref s) = session {
                    AcpServerEvent::Meta {
                        session_id: s.session_id.clone(),
                        cwd: s.cwd.display().to_string(),
                        backend: "alfred-cli".to_string(),
                        transport: "acp".to_string(),
                        version: ACP_VERSION.to_string(),
                    }
                    .emit();
                }
            }

            AcpClientMessage::PromptSend { prompt } => {
                if let Some(ref mut s) = session {
                    run_agent_loop(&mut *s, &prompt).await;
                } else {
                    AcpServerEvent::Error {
                        message: "No active session. Send session.start first.".to_string(),
                        exit_code: None,
                    }
                    .emit();
                }
            }

            AcpClientMessage::SessionCancel => {
                AcpServerEvent::Error {
                    message: "Cancellation not yet implemented".to_string(),
                    exit_code: None,
                }
                .emit();
            }

            AcpClientMessage::SessionClose => {
                session = None;
            }
        }

        fatal_errors = 0;
    }

    Ok(())
}

struct ActiveSession {
    session_id: String,
    cwd: PathBuf,
    provider: OpenRouterProvider,
}

async fn run_agent_loop(session: &mut ActiveSession, prompt: &str) {
    let system_prompt = alfred_tools::config::load_system_prompt()
        .await
        .unwrap_or_else(|| DEFAULT_SYSTEM_PROMPT.to_string());

    let mut messages = Vec::new();
    messages.push(Message::new(Role::System, system_prompt));
    messages.push(Message::new(Role::User, prompt.to_string()));

    match session.provider.respond(&messages).await {
        Ok(events) => {
            for event in events {
                match event {
                    AgentEvent::MessageDelta(content) => {
                        AcpServerEvent::Delta { content }.emit();
                    }
                    AgentEvent::ToolRequest(call) => {
                        AcpServerEvent::ToolRequest {
                            name: call.name,
                            arguments: call.arguments,
                        }
                        .emit();
                    }
                    AgentEvent::ToolResult(result) => {
                        AcpServerEvent::ToolResult {
                            name: result.name,
                            output: result.output.to_string(),
                            is_error: result.is_error,
                        }
                        .emit();
                    }
                    AgentEvent::Done => {}
                }
            }
            AcpServerEvent::Done {
                result: "completed".to_string(),
            }
            .emit();
        }
        Err(e) => {
            AcpServerEvent::Error {
                message: e.to_string(),
                exit_code: None,
            }
            .emit();
        }
    }
}