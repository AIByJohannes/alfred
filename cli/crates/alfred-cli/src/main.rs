use std::cell::Cell;
use std::env;
use std::io::{self, Stdout};
use std::path::{Path, PathBuf};
use std::time::{Duration, SystemTime, UNIX_EPOCH};

use alfred_core::{Message, Role};
use alfred_tools::config::Config;
use anyhow::Result;
use crossterm::event::{self, Event, KeyCode, KeyEventKind, KeyModifiers};
use crossterm::terminal::{
    disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen,
};
use crossterm::{execute, terminal};
use ratatui::backend::CrosstermBackend;
use ratatui::layout::{Constraint, Direction, Layout};
use ratatui::style::Style;
use ratatui::text::{Line, Span, Text};
use ratatui::widgets::{Block, Borders, Paragraph, Wrap};
use ratatui::Terminal;
use tokio::sync::mpsc;
use tokio::time;
use tokio_util::sync::CancellationToken;

mod acp;
mod markdown;
mod mcp_bridge;
mod memory;
mod tui;

use tui::{ONEDARK_BG, ONEDARK_BLUE, ONEDARK_FG, ONEDARK_GREEN, ONEDARK_RED};

const DEFAULT_SYSTEM_PROMPT: &str = include_str!("../../../prompts/SOUL.md");
const MAX_TOOL_DISPLAY_CHARS: usize = 1_200;

#[derive(Debug)]
enum AppEvent {
    Input(Event),
    Tick,
    AgentChunk {
        run_id: u64,
        content: String,
    },
    ToolStart {
        run_id: u64,
        name: String,
        input: serde_json::Value,
    },
    ToolEnd {
        run_id: u64,
        name: String,
        result: String,
        is_error: bool,
    },
    AgentError {
        run_id: u64,
        message: String,
    },
    AgentDone {
        run_id: u64,
    },
}

enum AppMode {
    Setup,
    Chat,
}

struct ActiveRun {
    id: u64,
    token: CancellationToken,
    cancelling: bool,
}

struct App {
    messages: Vec<Message>,
    input: String,
    streaming_idx: Option<usize>,
    scroll: u16,
    max_scroll: Cell<u16>,
    follow: bool,
    mode: AppMode,
    config: Config,
    active_run: Option<ActiveRun>,
    next_run_id: u64,
    session_id: String,
    skills: Vec<cersei::tools::skills::SkillMeta>,
    project_root: PathBuf,
    history: Vec<String>,
    history_pos: Option<usize>,
    draft: String,
}

impl App {
    async fn new() -> Self {
        let config = Config::load().await.unwrap_or_default();
        // Check both config and environment variable
        let mode = if config.openrouter_api_key.is_some() || env::var("OPENROUTER_API_KEY").is_ok()
        {
            AppMode::Chat
        } else {
            AppMode::Setup
        };

        let system_prompt = alfred_tools::config::load_system_prompt()
            .await
            .unwrap_or_else(|| DEFAULT_SYSTEM_PROMPT.to_string());

        let mut messages = Vec::new();
        if matches!(mode, AppMode::Chat) {
            messages.push(Message::new(Role::System, system_prompt));
        }

        let project_root = env::current_dir().unwrap_or_default();
        let skills = discover_skills(&project_root);

        Self {
            messages,
            input: String::new(),
            streaming_idx: None,
            scroll: 0,
            max_scroll: Cell::new(0),
            follow: true,
            mode,
            config,
            active_run: None,
            next_run_id: 1,
            session_id: new_session_id(),
            skills,
            project_root,
            history: Vec::new(),
            history_pos: None,
            draft: String::new(),
        }
    }

    fn is_running(&self) -> bool {
        self.active_run.is_some()
    }

    fn mode_is_chat(&self) -> bool {
        matches!(&self.mode, AppMode::Chat)
    }

    fn start_run(&mut self) -> (u64, CancellationToken) {
        let id = self.next_run_id;
        self.next_run_id += 1;
        let token = CancellationToken::new();
        self.active_run = Some(ActiveRun {
            id,
            token: token.clone(),
            cancelling: false,
        });
        (id, token)
    }

    /// Request cancellation but keep the run active until the agent has actually
    /// yielded. Cersei checks the token between turns, not inside a running tool.
    fn request_cancel(&mut self) -> bool {
        match self.active_run.as_mut() {
            Some(run) => {
                if !run.cancelling {
                    run.cancelling = true;
                    run.token.cancel();
                }
                true
            }
            None => false,
        }
    }

    fn is_cancelling(&self) -> bool {
        self.active_run.as_ref().is_some_and(|run| run.cancelling)
    }

    fn run_status(&self) -> tui::RunStatus {
        match self.active_run.as_ref() {
            Some(run) if run.cancelling => tui::RunStatus::Cancelling,
            Some(_) => tui::RunStatus::Running,
            None => tui::RunStatus::Idle,
        }
    }

    fn event_is_current(&self, run_id: u64) -> bool {
        self.active_run.as_ref().is_some_and(|run| run.id == run_id)
    }

    fn finish_run(&mut self, run_id: u64) {
        if self.event_is_current(run_id) {
            let cancelled = self.active_run.as_ref().is_some_and(|run| run.cancelling);
            self.active_run = None;
            self.streaming_idx = None;
            if cancelled {
                self.push_notice("Run cancelled.");
            }
        }
    }

    fn push_user(&mut self, content: String) {
        self.history.push(content.clone());
        self.history_pos = None;
        self.draft.clear();
        self.follow = true;
        self.messages.push(Message::new(Role::User, content));
    }

    fn push_notice(&mut self, content: impl Into<String>) {
        self.follow = true;
        self.messages
            .push(Message::new(Role::Assistant, content.into()));
    }

    fn push_tool_start(&mut self, name: &str, input: &serde_json::Value) {
        self.streaming_idx = None;
        self.follow = true;
        let args = serde_json::to_string_pretty(input).unwrap_or_else(|_| input.to_string());
        self.messages.push(Message::new(
            Role::Tool,
            format!(
                "🔧 {name}\n{}",
                truncate_chars(&args, MAX_TOOL_DISPLAY_CHARS)
            ),
        ));
    }

    fn push_tool_end(&mut self, name: &str, result: &str, is_error: bool) {
        self.streaming_idx = None;
        self.follow = true;
        let marker = if is_error { "❌" } else { "✅" };
        self.messages.push(Message::new(
            Role::Tool,
            format!(
                "{marker} {name}\n{}",
                truncate_chars(result, MAX_TOOL_DISPLAY_CHARS)
            ),
        ));
    }

    fn append_assistant_chunk(&mut self, chunk: String) {
        self.follow = true;
        let idx = match self.streaming_idx {
            Some(idx) => idx,
            None => {
                self.messages
                    .push(Message::new(Role::Assistant, String::new()));
                let idx = self.messages.len() - 1;
                self.streaming_idx = Some(idx);
                idx
            }
        };

        if let Some(message) = self.messages.get_mut(idx) {
            message.content.push_str(&chunk);
        }
    }

    fn slash_suggestions(&self) -> Vec<String> {
        slash_suggestions(&self.input, &self.skills)
    }

    fn clear_conversation(&mut self) {
        self.messages
            .retain(|message| matches!(message.role, Role::System));
        self.streaming_idx = None;
        self.scroll = 0;
        self.follow = true;
        self.session_id = new_session_id();
    }

    fn recall_previous(&mut self) {
        if self.history.is_empty() {
            return;
        }
        let index = match self.history_pos {
            Some(index) => index.saturating_sub(1),
            None => {
                self.draft = self.input.clone();
                self.history.len() - 1
            }
        };
        self.history_pos = Some(index);
        self.input = self.history[index].clone();
    }

    fn recall_next(&mut self) {
        let Some(index) = self.history_pos else {
            return;
        };
        if index + 1 < self.history.len() {
            self.history_pos = Some(index + 1);
            self.input = self.history[index + 1].clone();
        } else {
            self.history_pos = None;
            self.input = self.draft.clone();
        }
    }

    fn delete_word(&mut self) {
        while self.input.ends_with(' ') {
            self.input.pop();
        }
        while let Some(ch) = self.input.chars().last() {
            if ch.is_whitespace() {
                break;
            }
            self.input.pop();
        }
    }
}

fn new_session_id() -> String {
    let millis = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis();
    format!("tui-{}-{millis}", std::process::id())
}

fn truncate_chars(value: &str, limit: usize) -> String {
    if value.chars().count() <= limit {
        return value.to_string();
    }
    let suffix = "\n… (truncated)";
    let keep = limit.saturating_sub(suffix.chars().count());
    let mut truncated: String = value.chars().take(keep).collect();
    truncated.push_str(suffix);
    truncated
}

fn skill_extra_paths(root: &Path) -> Vec<PathBuf> {
    vec![root.join("skills")]
}

fn discover_skills(root: &Path) -> Vec<cersei::tools::skills::SkillMeta> {
    cersei::tools::skills::discovery::discover_all(Some(root), &skill_extra_paths(root))
}

const BUILTIN_COMMANDS: &[(&str, &str)] = &[
    ("skills", "List available skills"),
    ("help", "Show commands and keyboard shortcuts"),
    ("new", "Start a fresh conversation"),
    ("quit", "Exit Alfred"),
];

fn builtin_description(name: &str) -> Option<&'static str> {
    BUILTIN_COMMANDS
        .iter()
        .find(|(command, _)| *command == name)
        .map(|(_, description)| *description)
}

fn find_skill<'a>(
    name: &str,
    skills: &'a [cersei::tools::skills::SkillMeta],
) -> Option<&'a cersei::tools::skills::SkillMeta> {
    let lower = name.to_lowercase();
    skills.iter().find(|skill| {
        skill.name.to_lowercase() == lower
            || skill
                .aliases
                .iter()
                .any(|alias| alias.to_lowercase() == lower)
    })
}

fn slash_suggestions(input: &str, skills: &[cersei::tools::skills::SkillMeta]) -> Vec<String> {
    if !input.starts_with('/') || input.contains(char::is_whitespace) {
        return Vec::new();
    }

    let prefix = input.trim_start_matches('/').to_lowercase();
    let mut suggestions = Vec::new();

    for (name, description) in BUILTIN_COMMANDS {
        if name.starts_with(&prefix) {
            suggestions.push(format!("/{name} — {description}"));
        }
    }
    for skill in skills {
        if skill.name.to_lowercase().starts_with(&prefix) {
            suggestions.push(format!("/{} — {}", skill.name, skill.description));
        }
    }

    suggestions.truncate(6);
    suggestions
}

fn complete_slash_input(
    input: &str,
    skills: &[cersei::tools::skills::SkillMeta],
) -> Option<String> {
    if !input.starts_with('/') || input.contains(char::is_whitespace) {
        return None;
    }

    let prefix = input.trim_start_matches('/').to_lowercase();
    let mut names: Vec<String> = BUILTIN_COMMANDS
        .iter()
        .filter(|(name, _)| name.starts_with(&prefix))
        .map(|(name, _)| name.to_string())
        .collect();
    names.extend(
        skills
            .iter()
            .filter(|skill| skill.name.to_lowercase().starts_with(&prefix))
            .map(|skill| skill.name.clone()),
    );

    if names.is_empty() {
        return None;
    }

    let replacement = if names.len() == 1 {
        format!("/{} ", names[0])
    } else {
        let common = longest_common_prefix(&names);
        if common.len() <= prefix.len() {
            return None;
        }
        format!("/{common}")
    };

    (replacement != input).then_some(replacement)
}

fn longest_common_prefix(values: &[String]) -> String {
    let Some(first) = values.first() else {
        return String::new();
    };
    let mut prefix = first.clone();
    for value in &values[1..] {
        while !value.starts_with(&prefix) {
            if prefix.pop().is_none() {
                return prefix;
            }
        }
    }
    prefix
}

fn skill_command_prompt(name: &str, args: &str, root: &Path) -> Option<String> {
    let loaded =
        cersei::tools::skills::discovery::load_skill(name, Some(root), &skill_extra_paths(root))?;
    Some(loaded.expand(Some(args).filter(|value| !value.is_empty())))
}

fn help_text() -> String {
    let lines = vec![
        "Commands".to_string(),
        "  /skills              list available skills".to_string(),
        "  /<skill> [args]      run a skill by name (Tab completes)".to_string(),
        "  /new                 start a fresh conversation".to_string(),
        "  /help                show this help".to_string(),
        "  /quit                exit Alfred".to_string(),
        String::new(),
        "Keys".to_string(),
        "  Enter                send".to_string(),
        "  Tab                  complete a slash command".to_string(),
        "  Up / Down            recall previous prompts".to_string(),
        "  PgUp / PgDn          scroll the transcript".to_string(),
        "  Esc                  cancel the current run".to_string(),
        "  Ctrl+C               clear input, cancel, or exit".to_string(),
        "  Ctrl+U               clear the input line".to_string(),
    ];
    lines.join("\n")
}

fn list_skills(skills: &[cersei::tools::skills::SkillMeta]) -> String {
    let discovered = cersei::tools::skills::discovery::format_skill_list(skills);
    format!("{discovered}\n\nRun one with /<skill> [args]. Bundled skills are always available.")
}

fn send_prompt(app: &mut App, visible: String, prompt: String, tx: &mpsc::Sender<AppEvent>) {
    let api_key = env::var("OPENROUTER_API_KEY")
        .ok()
        .or(app.config.openrouter_api_key.clone());

    let Some(key) = api_key else {
        app.input.clear();
        app.push_notice(
            "No OpenRouter API key found. Set OPENROUTER_API_KEY or restart Alfred to configure it.",
        );
        return;
    };

    let system_prompt = app
        .messages
        .iter()
        .find(|message| matches!(message.role, Role::System))
        .map(|message| message.content.clone())
        .unwrap_or_else(|| DEFAULT_SYSTEM_PROMPT.to_string());

    app.input.clear();
    app.push_user(visible);

    let (run_id, token) = app.start_run();
    spawn_agent(
        system_prompt,
        app.session_id.clone(),
        prompt,
        tx.clone(),
        key,
        run_id,
        token,
    );
}

/// Handle Enter in chat mode. Returns `Some(quit)` when the input was consumed,
/// or `None` when the input should be handled as a normal prompt.
fn handle_chat_submit(app: &mut App, content: &str, tx: &mpsc::Sender<AppEvent>) -> Option<bool> {
    if !content.starts_with('/') {
        send_prompt(app, content.to_string(), content.to_string(), tx);
        return Some(false);
    }

    let command = content.trim_start_matches('/');
    let (name, args) = command
        .split_once(char::is_whitespace)
        .unwrap_or((command, ""));
    let args = args.trim();

    match name.to_lowercase().as_str() {
        "" => {
            app.push_notice(format!("{}\n\n{}", list_skills(&app.skills), help_text()));
            app.input.clear();
            Some(false)
        }
        "skills" => {
            app.push_notice(list_skills(&app.skills));
            app.input.clear();
            Some(false)
        }
        "help" => {
            app.push_notice(help_text());
            app.input.clear();
            Some(false)
        }
        "new" => {
            app.clear_conversation();
            app.push_notice("New conversation.");
            app.input.clear();
            Some(false)
        }
        "quit" | "exit" => Some(true),
        _ => {
            if let Some(description) = builtin_description(name) {
                app.push_notice(format!("/{name} — {description}"));
                app.input.clear();
                return Some(false);
            }

            let Some(skill) = find_skill(name, &app.skills) else {
                app.push_notice(format!(
                    "Unknown command /{name}. Run /skills to browse available skills."
                ));
                app.input.clear();
                return Some(false);
            };

            let skill_name = skill.name.clone();
            if let Some(prompt) = skill_command_prompt(&skill_name, args, &app.project_root) {
                send_prompt(app, content.to_string(), prompt, tx);
            } else {
                app.push_notice(format!("Could not load skill /{skill_name}."));
                app.input.clear();
            }
            Some(false)
        }
    }
}

struct TerminalGuard;

impl Drop for TerminalGuard {
    fn drop(&mut self) {
        let _ = disable_raw_mode();
        let mut stdout = io::stdout();
        let _ = execute!(stdout, LeaveAlternateScreen);
        let _ = terminal::disable_raw_mode();
    }
}

fn init_terminal() -> Result<Terminal<CrosstermBackend<Stdout>>> {
    enable_raw_mode()?;
    let mut stdout = io::stdout();
    execute!(stdout, EnterAlternateScreen)?;
    let backend = CrosstermBackend::new(stdout);
    let terminal = Terminal::new(backend)?;
    Ok(terminal)
}

fn install_panic_hook() {
    let default_hook = std::panic::take_hook();
    std::panic::set_hook(Box::new(move |info| {
        let _ = disable_raw_mode();
        let mut stdout = io::stdout();
        let _ = execute!(stdout, LeaveAlternateScreen);
        default_hook(info);
    }));
}

fn print_json_event(event_type: &str, fields: &[(&str, &str)]) {
    let mut map = serde_json::Map::new();
    map.insert(
        "type".to_string(),
        serde_json::Value::String(event_type.to_string()),
    );
    for (key, value) in fields {
        map.insert(
            key.to_string(),
            serde_json::Value::String(value.to_string()),
        );
    }
    println!("{}", serde_json::Value::Object(map));
}

fn openrouter_model() -> String {
    let model = std::env::var("OPENROUTER_MODEL")
        .ok()
        .filter(|s| !s.trim().is_empty())
        .unwrap_or_else(|| "google/gemini-3.5-flash".to_string());

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

async fn run_json_mode(
    prompt: &str,
    cwd: Option<PathBuf>,
    session_id: Option<String>,
) -> Result<()> {
    let config = Config::load().await.unwrap_or_default();
    let api_key = match env::var("OPENROUTER_API_KEY")
        .ok()
        .or(config.openrouter_api_key.clone())
    {
        Some(key) if !key.is_empty() => key,
        _ => {
            eprintln!("{{\"type\":\"error\",\"message\":\"No OpenRouter API key found. Set OPENROUTER_API_KEY or configure it.\"}}");
            std::process::exit(1);
        }
    };
    env::set_var("OPENROUTER_API_KEY", &api_key);

    let system_prompt = alfred_tools::config::load_system_prompt()
        .await
        .unwrap_or_else(|| DEFAULT_SYSTEM_PROMPT.to_string());

    let (provider, resolved_model) =
        match cersei::provider::router::from_model_string(&openrouter_model()) {
            Ok(provider) => provider,
            Err(e) => {
                eprintln!(
                    "{}",
                    serde_json::json!({
                        "type": "error",
                        "message": format!("Failed to initialize provider: {e}"),
                    })
                );
                std::process::exit(1);
            }
        };

    let (db_path, sessions_dir) = memory_paths();
    let memory = match memory::AlfredMemory::open(&db_path, &sessions_dir) {
        Ok(memory) => memory,
        Err(e) => {
            eprintln!(
                "{}",
                serde_json::json!({
                    "type": "error",
                    "message": format!("Failed to open AlfredMemory: {e}"),
                })
            );
            std::process::exit(1);
        }
    };

    let working_dir = cwd.unwrap_or_else(|| std::env::current_dir().unwrap_or_default());
    let mut tools = cersei::tools::coding();
    tools.push(Box::new(
        cersei::tools::skill_tool::SkillTool::new()
            .with_project_root(&working_dir)
            .with_extra_path(working_dir.join("skills")),
    ));
    if let Some(mcp_tool) = mcp_bridge::connect_tool(&config.mcp_servers).await {
        tools.push(mcp_tool);
    }

    let mut agent_builder = cersei::Agent::builder()
        .provider_boxed(provider)
        .model(resolved_model)
        .tools(tools)
        .system_prompt(system_prompt)
        .working_dir(&working_dir)
        .memory(memory);

    if let Some(ref sid) = session_id {
        agent_builder = agent_builder.session_id(sid);
    }

    let agent = match agent_builder.build() {
        Ok(agent) => agent,
        Err(e) => {
            eprintln!(
                "{}",
                serde_json::json!({
                    "type": "error",
                    "message": format!("Failed to build agent: {e}"),
                })
            );
            std::process::exit(1);
        }
    };

    let agent = std::sync::Arc::new(agent);
    let mut stream = agent.run_stream(prompt);

    while let Some(event) = stream.next().await {
        match event {
            cersei::AgentEvent::TextDelta(content) => {
                print_json_event("delta", &[("content", &content)]);
            }
            cersei::AgentEvent::ToolStart { name, input, .. } => {
                let args_str = input.to_string();
                print_json_event("tool_request", &[("name", &name), ("arguments", &args_str)]);
            }
            cersei::AgentEvent::ToolEnd {
                name,
                result,
                is_error,
                ..
            } => {
                print_json_event(
                    "tool_result",
                    &[
                        ("name", &name),
                        ("output", &result),
                        ("is_error", &is_error.to_string()),
                    ],
                );
            }
            _ => {}
        }
    }

    print_json_event("done", &[("result", "completed")]);

    Ok(())
}

fn parse_acp_args() -> Option<Option<PathBuf>> {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 || args[1] != "acp" {
        return None;
    }

    let mut cwd: Option<PathBuf> = None;
    let mut i = 2;
    while i < args.len() {
        if args[i] == "--cwd" && i + 1 < args.len() {
            let p = PathBuf::from(&args[i + 1]);
            if p.is_dir() {
                cwd = Some(p);
            }
            i += 2;
        } else {
            i += 1;
        }
    }

    Some(cwd)
}

#[tokio::main]
async fn main() -> Result<()> {
    if let Some(cwd) = parse_acp_args() {
        return acp::run_acp(cwd).await;
    }

    let args: Vec<String> = env::args().collect();
    if args.len() >= 3 && args[1] == "run" {
        let mut prompt: Option<String> = None;
        let mut cwd: Option<PathBuf> = None;
        let mut session_id: Option<String> = None;
        let mut i = 2;
        while i < args.len() {
            match args[i].as_str() {
                "--jsonl" => {}
                "--prompt" if i + 1 < args.len() => {
                    prompt = Some(args[i + 1].clone());
                    i += 1;
                }
                "--cwd" if i + 1 < args.len() => {
                    let p = PathBuf::from(&args[i + 1]);
                    if p.is_dir() {
                        cwd = Some(p);
                    }
                    i += 1;
                }
                "--session-id" if i + 1 < args.len() => {
                    session_id = Some(args[i + 1].clone());
                    i += 1;
                }
                _ => {}
            }
            i += 1;
        }
        if let Some(p) = prompt {
            if let Some(ref dir) = cwd {
                std::env::set_current_dir(dir)?;
            }
            return run_json_mode(&p, cwd, session_id).await;
        }
    }

    let log_filter = env::var("RUST_LOG").unwrap_or_else(|_| "error".to_string());
    tracing_subscriber::fmt().with_env_filter(log_filter).init();

    install_panic_hook();
    let _terminal_guard = TerminalGuard;
    let mut terminal = init_terminal()?;

    let (tx, mut rx) = mpsc::channel::<AppEvent>(256);

    spawn_input_reader(tx.clone());
    spawn_tick(tx.clone());

    let mut app = App::new().await;

    loop {
        let suggestions = app.slash_suggestions();
        terminal.draw(|frame| {
            // Set background for the whole area?
            // Ratatui widgets draw over what's there.
            // We'll apply the style to the widgets.

            match app.mode {
                AppMode::Setup => {
                    let chunks = Layout::default()
                        .direction(Direction::Vertical)
                        .constraints([Constraint::Min(1), Constraint::Length(3)])
                        .split(frame.size());

                    let info = Paragraph::new(Text::from(vec![
                        Line::from("Welcome to Alfred CLI!"),
                        Line::from(""),
                        Line::from("Please enter your OpenRouter API Key to get started."),
                        Line::from(vec![
                            Span::raw("("),
                            Span::styled("Press ESC to quit", Style::default().fg(ONEDARK_RED)),
                            Span::raw(")"),
                        ]),
                    ]))
                    .block(
                        Block::default()
                            .borders(Borders::ALL)
                            .title("Setup")
                            .border_style(Style::default().fg(ONEDARK_BLUE)),
                    )
                    .style(Style::default().fg(ONEDARK_FG).bg(ONEDARK_BG))
                    .wrap(Wrap { trim: false });
                    frame.render_widget(info, chunks[0]);

                    let input = Paragraph::new(format!("> {}", app.input))
                        .block(
                            Block::default()
                                .borders(Borders::ALL)
                                .title("API Key")
                                .border_style(Style::default().fg(ONEDARK_BLUE)),
                        )
                        .style(Style::default().fg(ONEDARK_GREEN).bg(ONEDARK_BG));
                    frame.render_widget(input, chunks[1]);
                }
                AppMode::Chat => {
                    if tui::conversation_started(&app.messages) {
                        let messages = tui::render_transcript(&app.messages);
                        let max_scroll = tui::draw_conversation(
                            frame,
                            &messages,
                            &app.input,
                            app.scroll,
                            &suggestions,
                            app.run_status(),
                            app.follow,
                        );
                        app.max_scroll.set(max_scroll);
                    } else {
                        tui::draw_welcome(frame, &app.input, &suggestions);
                    }
                }
            }
        })?;

        let event = match rx.recv().await {
            Some(event) => event,
            None => break,
        };

        match event {
            AppEvent::Input(Event::Key(key)) if key.kind == KeyEventKind::Press => match key.code {
                KeyCode::Char('c') if key.modifiers.contains(KeyModifiers::CONTROL) => {
                    if !app.mode_is_chat() {
                        break;
                    }
                    if app.is_running() {
                        if app.is_cancelling() {
                            break;
                        }
                        app.request_cancel();
                    } else if app.input.is_empty() {
                        break;
                    } else {
                        app.input.clear();
                    }
                }
                KeyCode::Char('d') if key.modifiers.contains(KeyModifiers::CONTROL) => {
                    if app.input.is_empty() {
                        break;
                    }
                    app.input.pop();
                }
                KeyCode::Char('u') if key.modifiers.contains(KeyModifiers::CONTROL) => {
                    app.input.clear();
                }
                KeyCode::Char('w') if key.modifiers.contains(KeyModifiers::CONTROL) => {
                    app.delete_word();
                }
                KeyCode::Esc => {
                    if !app.mode_is_chat() {
                        break;
                    }
                    if !app.request_cancel() {
                        if app.input.is_empty() {
                            break;
                        }
                        app.input.clear();
                    }
                }
                KeyCode::Tab => {
                    if let Some(completed) = complete_slash_input(&app.input, &app.skills) {
                        app.input = completed;
                    }
                }
                KeyCode::Enter => {
                    let content = app.input.trim().to_string();
                    if content.is_empty() || app.is_running() {
                        continue;
                    }
                    match app.mode {
                        AppMode::Setup => {
                            app.config.openrouter_api_key = Some(content);
                            if let Err(e) = app.config.save().await {
                                eprintln!("Failed to save config: {}", e);
                            }

                            let system_prompt = alfred_tools::config::load_system_prompt()
                                .await
                                .unwrap_or_else(|| DEFAULT_SYSTEM_PROMPT.to_string());
                            app.messages.push(Message::new(Role::System, system_prompt));

                            app.mode = AppMode::Chat;
                            app.input.clear();
                        }
                        AppMode::Chat => {
                            if let Some(quit) = handle_chat_submit(&mut app, &content, &tx) {
                                if quit {
                                    break;
                                }
                            } else {
                                continue;
                            }
                        }
                    }
                }
                KeyCode::Backspace => {
                    app.input.pop();
                }
                KeyCode::Up => {
                    if app.mode_is_chat() && !app.history.is_empty() {
                        app.recall_previous();
                    } else if app.mode_is_chat() {
                        let max = app.max_scroll.get();
                        if app.follow {
                            app.scroll = max;
                            app.follow = false;
                        }
                        app.scroll = app.scroll.saturating_sub(1);
                    }
                }
                KeyCode::Down => {
                    if app.mode_is_chat() && app.history_pos.is_some() {
                        app.recall_next();
                    } else if app.mode_is_chat() {
                        let max = app.max_scroll.get();
                        app.follow = false;
                        app.scroll = app.scroll.saturating_add(1).min(max);
                        if app.scroll >= max {
                            app.follow = true;
                        }
                    }
                }
                KeyCode::PageUp => {
                    if app.mode_is_chat() {
                        let max = app.max_scroll.get();
                        if app.follow {
                            app.scroll = max;
                            app.follow = false;
                        }
                        app.scroll = app.scroll.saturating_sub(10);
                    }
                }
                KeyCode::PageDown => {
                    if app.mode_is_chat() {
                        let max = app.max_scroll.get();
                        app.follow = false;
                        app.scroll = app.scroll.saturating_add(10).min(max);
                        if app.scroll >= max {
                            app.follow = true;
                        }
                    }
                }
                KeyCode::Char(ch) => {
                    app.input.push(ch);
                }
                _ => {}
            },
            AppEvent::Input(Event::Resize(_, _)) => {}
            AppEvent::AgentChunk { run_id, content } => {
                if app.event_is_current(run_id) {
                    app.append_assistant_chunk(content);
                }
            }
            AppEvent::ToolStart {
                run_id,
                name,
                input,
            } => {
                if app.event_is_current(run_id) {
                    app.push_tool_start(&name, &input);
                }
            }
            AppEvent::ToolEnd {
                run_id,
                name,
                result,
                is_error,
            } => {
                if app.event_is_current(run_id) {
                    app.push_tool_end(&name, &result, is_error);
                }
            }
            AppEvent::AgentError { run_id, message } => {
                if app.event_is_current(run_id) {
                    app.push_notice(format!("Error: {message}"));
                    app.finish_run(run_id);
                }
            }
            AppEvent::AgentDone { run_id } => app.finish_run(run_id),
            AppEvent::Tick => {}
            _ => {}
        }
    }

    Ok(())
}

fn spawn_input_reader(tx: mpsc::Sender<AppEvent>) {
    tokio::spawn(async move {
        loop {
            let event_ready =
                tokio::task::spawn_blocking(|| event::poll(Duration::from_millis(250)))
                    .await
                    .ok()
                    .and_then(|res| res.ok())
                    .unwrap_or(false);
            if event_ready {
                if let Ok(ev) = event::read() {
                    if tx.send(AppEvent::Input(ev)).await.is_err() {
                        break;
                    }
                }
            }
        }
    });
}

fn spawn_tick(tx: mpsc::Sender<AppEvent>) {
    tokio::spawn(async move {
        let mut interval = time::interval(Duration::from_millis(250));
        loop {
            interval.tick().await;
            if tx.send(AppEvent::Tick).await.is_err() {
                break;
            }
        }
    });
}

fn spawn_agent(
    system_prompt: String,
    session_id: String,
    prompt: String,
    tx: mpsc::Sender<AppEvent>,
    api_key: String,
    run_id: u64,
    cancel_token: CancellationToken,
) {
    tokio::spawn(async move {
        env::set_var("OPENROUTER_API_KEY", &api_key);
        let config = Config::load().await.unwrap_or_default();

        let (provider, resolved_model) =
            match cersei::provider::router::from_model_string(&openrouter_model()) {
                Ok(provider) => provider,
                Err(e) => {
                    let _ = tx
                        .send(AppEvent::AgentError {
                            run_id,
                            message: e.to_string(),
                        })
                        .await;
                    return;
                }
            };

        let (db_path, sessions_dir) = memory_paths();
        let memory = match memory::AlfredMemory::open(&db_path, &sessions_dir) {
            Ok(memory) => memory,
            Err(e) => {
                let _ = tx
                    .send(AppEvent::AgentError {
                        run_id,
                        message: format!("Error opening AlfredMemory: {e}"),
                    })
                    .await;
                return;
            }
        };

        let working_dir = std::env::current_dir().unwrap_or_default();
        let mut tools = cersei::tools::coding();
        tools.push(Box::new(
            cersei::tools::skill_tool::SkillTool::new()
                .with_project_root(&working_dir)
                .with_extra_path(working_dir.join("skills")),
        ));
        if let Some(mcp_tool) = mcp_bridge::connect_tool(&config.mcp_servers).await {
            tools.push(mcp_tool);
        }

        let agent = match cersei::Agent::builder()
            .provider_boxed(provider)
            .model(resolved_model)
            .tools(tools)
            .system_prompt(system_prompt)
            .session_id(session_id)
            .memory(memory)
            .working_dir(working_dir)
            .cancel_token(cancel_token.clone())
            .build()
        {
            Ok(agent) => agent,
            Err(e) => {
                let _ = tx
                    .send(AppEvent::AgentError {
                        run_id,
                        message: format!("Error building agent: {e}"),
                    })
                    .await;
                return;
            }
        };

        let agent = std::sync::Arc::new(agent);
        let mut stream = agent.run_stream(&prompt);

        let mut cancel_sent = false;
        loop {
            tokio::select! {
                _ = cancel_token.cancelled(), if !cancel_sent => {
                    stream.cancel();
                    cancel_sent = true;
                }
                event = stream.next() => {
                    match event {
                        Some(cersei::AgentEvent::TextDelta(content)) => {
                            if tx
                                .send(AppEvent::AgentChunk { run_id, content })
                                .await
                                .is_err()
                            {
                                return;
                            }
                        }
                        Some(cersei::AgentEvent::ToolStart { name, input, .. }) => {
                            if tx
                                .send(AppEvent::ToolStart { run_id, name, input })
                                .await
                                .is_err()
                            {
                                return;
                            }
                        }
                        Some(cersei::AgentEvent::ToolEnd {
                            name,
                            result,
                            is_error,
                            ..
                        }) => {
                            if tx
                                .send(AppEvent::ToolEnd {
                                    run_id,
                                    name,
                                    result,
                                    is_error,
                                })
                                .await
                                .is_err()
                            {
                                return;
                            }
                        }
                        Some(cersei::AgentEvent::Error(message)) => {
                            if message.to_lowercase().contains("cancelled") {
                                let _ = tx.send(AppEvent::AgentDone { run_id }).await;
                            } else {
                                let _ = tx.send(AppEvent::AgentError { run_id, message }).await;
                            }
                            return;
                        }
                        Some(cersei::AgentEvent::Complete(_)) | None => {
                            let _ = tx.send(AppEvent::AgentDone { run_id }).await;
                            return;
                        }
                        Some(_) => {}
                    }
                }
            }
        }
    });
}

#[cfg(test)]
mod tests {
    use super::*;
    use cersei::tools::skills::SkillMeta;

    fn skill(name: &str, description: &str) -> SkillMeta {
        SkillMeta {
            name: name.to_string(),
            description: description.to_string(),
            path: None,
            bundled: true,
            aliases: Vec::new(),
            allowed_tools: None,
            argument_hint: None,
            format: cersei::tools::skills::SkillFormat::Bundled,
        }
    }

    fn test_app(skills: Vec<SkillMeta>) -> App {
        App {
            messages: vec![Message::new(Role::System, "system".to_string())],
            input: String::new(),
            streaming_idx: None,
            scroll: 0,
            max_scroll: Cell::new(0),
            follow: true,
            mode: AppMode::Chat,
            config: Config::default(),
            active_run: None,
            next_run_id: 1,
            session_id: "test-session".to_string(),
            skills,
            project_root: PathBuf::from("."),
            history: Vec::new(),
            history_pos: None,
            draft: String::new(),
        }
    }

    #[test]
    fn slash_suggestions_include_builtins_and_skills() {
        let skills = vec![skill("debug", "Debug a failure")];
        let suggestions = slash_suggestions("/", &skills);
        assert!(suggestions.iter().any(|item| item.starts_with("/skills")));
        assert!(suggestions.iter().any(|item| item.starts_with("/debug")));

        let filtered = slash_suggestions("/de", &skills);
        assert_eq!(filtered.len(), 1);
        assert!(filtered[0].starts_with("/debug"));
    }

    #[test]
    fn tab_completion_extends_unique_and_shared_prefixes() {
        let skills = vec![skill("debug", "Debug"), skill("deploy", "Deploy")];
        assert_eq!(
            complete_slash_input("/deb", &skills).as_deref(),
            Some("/debug ")
        );
        assert_eq!(complete_slash_input("/d", &skills).as_deref(), Some("/de"));
    }

    #[test]
    fn truncation_marks_long_tool_output() {
        let output = "x".repeat(MAX_TOOL_DISPLAY_CHARS + 10);
        let truncated = truncate_chars(&output, MAX_TOOL_DISPLAY_CHARS);
        assert!(truncated.ends_with("(truncated)"));
        assert!(truncated.len() < output.len());
    }

    #[test]
    fn tool_activity_breaks_the_assistant_stream() {
        let mut app = test_app(Vec::new());
        app.append_assistant_chunk("before".to_string());
        app.push_tool_start("Bash", &serde_json::json!({"command": "ls"}));
        app.append_assistant_chunk("after".to_string());

        assert_eq!(app.messages.len(), 4);
        assert_eq!(app.messages[1].content, "before");
        assert!(matches!(app.messages[2].role, Role::Tool));
        assert_eq!(app.messages[3].content, "after");
    }

    #[test]
    fn history_recall_restores_the_draft() {
        let mut app = test_app(Vec::new());
        app.push_user("first".to_string());
        app.push_user("second".to_string());
        app.input = "draft".to_string();

        app.recall_previous();
        assert_eq!(app.input, "second");
        app.recall_previous();
        assert_eq!(app.input, "first");
        app.recall_next();
        assert_eq!(app.input, "second");
        app.recall_next();
        assert_eq!(app.input, "draft");
    }

    #[test]
    fn cancellation_stays_active_until_the_agent_finishes() {
        let mut app = test_app(Vec::new());
        let (run_id, _token) = app.start_run();

        assert!(app.request_cancel());
        assert!(app.is_running());
        assert!(app.is_cancelling());

        app.finish_run(run_id);
        assert!(!app.is_running());
        assert!(!app.is_cancelling());
        assert!(app.messages.last().unwrap().content.contains("cancelled"));
    }

    #[tokio::test]
    async fn new_command_keeps_only_the_system_prompt() {
        let mut app = test_app(vec![skill("debug", "Debug")]);
        app.push_user("/debug something".to_string());
        let (tx, _rx) = mpsc::channel(4);

        let handled = handle_chat_submit(&mut app, "/new", &tx);
        assert_eq!(handled, Some(false));
        assert_eq!(app.messages.len(), 2);
        assert!(matches!(app.messages[0].role, Role::System));
    }

    #[tokio::test]
    async fn unknown_commands_are_reported_without_starting_a_run() {
        let mut app = test_app(vec![skill("debug", "Debug")]);
        let (tx, _rx) = mpsc::channel(4);

        let handled = handle_chat_submit(&mut app, "/nope", &tx);
        assert_eq!(handled, Some(false));
        assert!(app.active_run.is_none());
        assert!(app.messages[1].content.contains("Unknown command"));
    }
}
