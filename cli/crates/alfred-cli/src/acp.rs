use std::io::{self, BufRead, Write};
use std::path::PathBuf;

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
    Delta {
        content: String,
    },
    ToolRequest {
        name: String,
        arguments: serde_json::Value,
    },
    ToolResult {
        name: String,
        output: String,
        is_error: bool,
    },
    Artifact {
        label: String,
        path: Option<String>,
        url: Option<String>,
    },
    Done {
        result: String,
    },
    Error {
        message: String,
        exit_code: Option<i32>,
    },
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
    let api_key = match std::env::var("OPENROUTER_API_KEY")
        .ok()
        .or(config.openrouter_api_key.clone())
    {
        Some(key) if !key.is_empty() => key,
        _ => {
            AcpServerEvent::Error {
                message: "No OpenRouter API key found. Set OPENROUTER_API_KEY or configure it."
                    .to_string(),
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
                eprintln!(
                    "{{\"type\":\"error\",\"message\":\"stdin read error: {}\"}}",
                    e
                );
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

                session = Some(ActiveSession {
                    session_id,
                    cwd: resolved_cwd,
                    api_key: api_key.clone(),
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
    api_key: String,
}

async fn run_agent_loop(session: &mut ActiveSession, prompt: &str) {
    std::env::set_var("OPENROUTER_API_KEY", &session.api_key);

    let system_prompt = alfred_tools::config::load_system_prompt()
        .await
        .unwrap_or_else(|| DEFAULT_SYSTEM_PROMPT.to_string());

    let (provider, resolved_model) =
        match cersei::provider::router::from_model_string(&openrouter_model()) {
            Ok(provider) => provider,
            Err(e) => {
                AcpServerEvent::Error {
                    message: format!("Failed to initialize provider: {e}"),
                    exit_code: None,
                }
                .emit();
                return;
            }
        };

    let (db_path, sessions_dir) = memory_paths();
    let memory = match crate::memory::AlfredMemory::open(&db_path, &sessions_dir) {
        Ok(memory) => memory,
        Err(e) => {
            AcpServerEvent::Error {
                message: format!("Failed to open AlfredMemory: {e}"),
                exit_code: None,
            }
            .emit();
            return;
        }
    };

    let agent = match cersei::Agent::builder()
        .provider_boxed(provider)
        .model(resolved_model)
        .tools(cersei::tools::coding())
        .system_prompt(system_prompt)
        .working_dir(&session.cwd)
        .session_id(&session.session_id)
        .memory(memory)
        .build()
    {
        Ok(agent) => agent,
        Err(e) => {
            AcpServerEvent::Error {
                message: format!("Failed to build agent: {e}"),
                exit_code: None,
            }
            .emit();
            return;
        }
    };

    let agent = std::sync::Arc::new(agent);
    let mut stream = agent.run_stream(prompt);

    while let Some(event) = stream.next().await {
        match event {
            cersei::AgentEvent::TextDelta(content) => {
                AcpServerEvent::Delta { content }.emit();
            }
            cersei::AgentEvent::ToolStart { name, input, .. } => {
                AcpServerEvent::ToolRequest {
                    name,
                    arguments: input,
                }
                .emit();
            }
            cersei::AgentEvent::ToolEnd {
                name,
                result,
                is_error,
                ..
            } => {
                AcpServerEvent::ToolResult {
                    name,
                    output: result,
                    is_error,
                }
                .emit();
            }
            _ => {}
        }
    }

    AcpServerEvent::Done {
        result: "completed".to_string(),
    }
    .emit();
}

fn openrouter_model() -> String {
    let model = std::env::var("OPENROUTER_MODEL")
        .ok()
        .filter(|s| !s.trim().is_empty())
        .unwrap_or_else(|| "deepseek/deepseek-v4-flash".to_string());

    if model.starts_with("openrouter/") {
        model
    } else {
        format!("openrouter/{model}")
    }
}

fn memory_paths() -> (PathBuf, PathBuf) {
    let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
    let alfred_config_dir = PathBuf::from(home).join(".config").join("alfred");
    (
        alfred_config_dir.join("graph.db"),
        alfred_config_dir.join("sessions"),
    )
}
