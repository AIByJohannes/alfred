use std::env;
use std::io::{self, Stdout};
use std::path::PathBuf;
use std::time::Duration;

use alfred_core::{Message, Role, AgentRouter, AgentEvent};
use alfred_core::providers::openrouter::OpenRouterProvider;
use alfred_tools::config::Config;
use anyhow::Result;
use crossterm::event::{self, Event, KeyCode, KeyEventKind, KeyModifiers};
use crossterm::terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen};
use crossterm::{execute, terminal};
use ratatui::backend::CrosstermBackend;
use ratatui::layout::{Constraint, Direction, Layout};
use ratatui::style::{Color, Style, Stylize};
use ratatui::text::{Line, Span, Text};
use ratatui::widgets::{Block, Borders, Paragraph, Wrap};
use ratatui::Terminal;
use tokio::sync::mpsc;
use tokio::time;

mod markdown;

// OneDark Theme Colors
const ONEDARK_BG: Color = Color::Rgb(40, 44, 52);
const ONEDARK_FG: Color = Color::Rgb(171, 178, 191);
const ONEDARK_RED: Color = Color::Rgb(224, 108, 117);
const ONEDARK_GREEN: Color = Color::Rgb(152, 195, 121);
const ONEDARK_BLUE: Color = Color::Rgb(97, 175, 239);
const ONEDARK_MAGENTA: Color = Color::Rgb(198, 120, 221);
const ONEDARK_CYAN: Color = Color::Rgb(86, 182, 194);

const DEFAULT_SYSTEM_PROMPT: &str = include_str!("../../../prompts/SOUL.md");

#[derive(Debug)]
enum AppEvent {
    Input(Event),
    Tick,
    AgentChunk(String),
    AgentDone,
}

enum AppMode {
    Setup,
    Chat,
}

struct App {
    messages: Vec<Message>,
    input: String,
    streaming_idx: Option<usize>,
    scroll: u16,
    mode: AppMode,
    config: Config,
}

impl App {
    async fn new() -> Self {
        let config = Config::load().await.unwrap_or_default();
        // Check both config and environment variable
        let mode = if config.openrouter_api_key.is_some() || env::var("OPENROUTER_API_KEY").is_ok() {
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

        Self {
            messages,
            input: String::new(),
            streaming_idx: None,
            scroll: 0,
            mode,
            config,
        }
    }

    fn push_user(&mut self, content: String) {
        self.messages.push(Message::new(Role::User, content));
    }

    fn append_assistant_chunk(&mut self, chunk: String) {
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
            if !message.content.is_empty() {
                message.content.push(' ');
            }
            message.content.push_str(&chunk);
        }
    }

    fn finish_assistant(&mut self) {
        self.streaming_idx = None;
    }

    fn render_messages(&self) -> Text<'_> {
        let mut lines = Vec::new();
        for message in &self.messages {
            let (label, color) = match message.role {
                Role::User => ("You", ONEDARK_GREEN),
                Role::Assistant => ("Alfred", ONEDARK_MAGENTA),
                Role::System => ("System", ONEDARK_CYAN),
                Role::Tool => ("Tool", ONEDARK_RED),
            };

            lines.push(Line::from(vec![
                Span::styled(format!("{}: ", label), Style::default().fg(color).bold()),
            ]));
            
            let content_lines = markdown::render_markdown(&message.content, Style::default().fg(ONEDARK_FG));
            lines.extend(content_lines);
            
            lines.push(Line::from(""));
        }
        Text::from(lines)
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
    map.insert("type".to_string(), serde_json::Value::String(event_type.to_string()));
    for (key, value) in fields {
        map.insert(key.to_string(), serde_json::Value::String(value.to_string()));
    }
    println!("{}", serde_json::Value::Object(map));
}

async fn run_json_mode(prompt: &str, _mode: &str, _cwd: Option<PathBuf>) -> Result<()> {
    let config = Config::load().await.unwrap_or_default();
    let api_key = match env::var("OPENROUTER_API_KEY").ok().or(config.openrouter_api_key.clone()) {
        Some(key) if !key.is_empty() => key,
        _ => {
            eprintln!("{{\"type\":\"error\",\"message\":\"No OpenRouter API key found. Set OPENROUTER_API_KEY or configure it.\"}}");
            std::process::exit(1);
        }
    };

    let system_prompt = alfred_tools::config::load_system_prompt()
        .await
        .unwrap_or_else(|| DEFAULT_SYSTEM_PROMPT.to_string());

    let mut messages = Vec::new();
    messages.push(Message::new(Role::System, system_prompt));
    messages.push(Message::new(Role::User, prompt.to_string()));

    let provider = OpenRouterProvider::new(api_key, "google/gemini-2.0-flash-001".to_string());

    match provider.respond(&messages).await {
        Ok(events) => {
            for event in events {
                match event {
                    AgentEvent::MessageDelta(content) => {
                        print_json_event("delta", &[("content", &content)]);
                    }
                    AgentEvent::ToolRequest(call) => {
                        let args_str = call.arguments.to_string();
                        print_json_event("tool_request", &[
                            ("name", &call.name),
                            ("arguments", &args_str),
                        ]);
                    }
                    AgentEvent::ToolResult(result) => {
                        let output_str = result.output.to_string();
                        print_json_event("tool_result", &[
                            ("name", &result.name),
                            ("output", &output_str),
                            ("is_error", &result.is_error.to_string()),
                        ]);
                    }
                    AgentEvent::Done => {}
                }
            }
            print_json_event("done", &[("result", "completed")]);
        }
        Err(e) => {
            eprintln!("Error: {}", e);
            std::process::exit(1);
        }
    }

    Ok(())
}

fn parse_args() -> Option<(String, String, Option<PathBuf>)> {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        return None;
    }

    if args[1] == "run" {
        let mut prompt = None;
        let mut mode = "fs-agent".to_string();
        let mut cwd = None;

        let mut i = 2;
        while i < args.len() {
            match args[i].as_str() {
                "--jsonl" => {}
                "--mode" if i + 1 < args.len() => {
                    mode = args[i + 1].clone();
                    i += 1;
                }
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
                _ => {}
            }
            i += 1;
        }

        if let Some(p) = prompt {
            return Some((p, mode, cwd));
        }
    }

    None
}

#[tokio::main]
async fn main() -> Result<()> {
    if let Some((prompt, mode, cwd)) = parse_args() {
        if let Some(ref dir) = cwd {
            std::env::set_current_dir(dir)?;
        }
        return run_json_mode(&prompt, &mode, cwd).await;
    }

    tracing_subscriber::fmt()
        .with_env_filter("info")
        .init();

    install_panic_hook();
    let _terminal_guard = TerminalGuard;
    let mut terminal = init_terminal()?;

    let (tx, mut rx) = mpsc::channel::<AppEvent>(256);

    spawn_input_reader(tx.clone());
    spawn_tick(tx.clone());

    let mut app = App::new().await;

    loop {
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
                    .block(Block::default()
                        .borders(Borders::ALL)
                        .title("Setup")
                        .border_style(Style::default().fg(ONEDARK_BLUE))
                    )
                    .style(Style::default().fg(ONEDARK_FG).bg(ONEDARK_BG))
                    .wrap(Wrap { trim: false });
                    frame.render_widget(info, chunks[0]);

                    let input = Paragraph::new(format!("> {}", app.input))
                        .block(Block::default()
                            .borders(Borders::ALL)
                            .title("API Key")
                            .border_style(Style::default().fg(ONEDARK_BLUE))
                        )
                        .style(Style::default().fg(ONEDARK_GREEN).bg(ONEDARK_BG));
                    frame.render_widget(input, chunks[1]);
                }
                AppMode::Chat => {
                    let chunks = Layout::default()
                        .direction(Direction::Vertical)
                        .constraints([Constraint::Min(2), Constraint::Length(3)])
                        .split(frame.size());

                    let messages = Paragraph::new(app.render_messages())
                        .block(Block::default()
                            .borders(Borders::ALL)
                            .title("Alfred")
                            .border_style(Style::default().fg(ONEDARK_BLUE))
                        )
                        .style(Style::default().fg(ONEDARK_FG).bg(ONEDARK_BG))
                        .wrap(Wrap { trim: false })
                        .scroll((app.scroll, 0));
                    frame.render_widget(messages, chunks[0]);

                    let input = Paragraph::new(format!("> {}", app.input))
                        .block(Block::default()
                            .borders(Borders::ALL)
                            .title("Input")
                            .border_style(Style::default().fg(ONEDARK_BLUE))
                        )
                        .style(Style::default().fg(ONEDARK_GREEN).bg(ONEDARK_BG));
                    frame.render_widget(input, chunks[1]);
                }
            }
        })?;

        let event = match rx.recv().await {
            Some(event) => event,
            None => break,
        };

        match event {
            AppEvent::Input(Event::Key(key)) if key.kind == KeyEventKind::Press => {
                match key.code {
                    KeyCode::Char('c') if key.modifiers.contains(KeyModifiers::CONTROL) => break,
                    KeyCode::Esc => break,
                    KeyCode::Enter => {
                        let content = app.input.trim().to_string();
                        if !content.is_empty() {
                            match app.mode {
                                AppMode::Setup => {
                                    app.config.openrouter_api_key = Some(content);
                                    if let Err(e) = app.config.save().await {
                                         // In a real app we might show an error message
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
                                    app.push_user(content.clone());
                                    app.input.clear();
                                    
                                    // Prioritize env var, then config
                                    let api_key = env::var("OPENROUTER_API_KEY")
                                        .ok()
                                        .or(app.config.openrouter_api_key.clone());

                                    if let Some(key) = api_key {
                                        spawn_agent(app.messages.clone(), tx.clone(), key);
                                    } else {
                                        spawn_mock_agent(content, tx.clone());
                                    }
                                }
                            }
                        }
                    }
                    KeyCode::Backspace => {
                        app.input.pop();
                    }
                    KeyCode::Up => {
                        app.scroll = app.scroll.saturating_add(1);
                    }
                    KeyCode::Down => {
                        app.scroll = app.scroll.saturating_sub(1);
                    }
                    KeyCode::Char(ch) => {
                        app.input.push(ch);
                    }
                    _ => {}
                }
            }
            AppEvent::Input(Event::Resize(_, _)) => {}
            AppEvent::AgentChunk(chunk) => app.append_assistant_chunk(chunk),
            AppEvent::AgentDone => app.finish_assistant(),
            AppEvent::Tick => {}
            _ => {}
        }
    }

    Ok(())
}

fn spawn_input_reader(tx: mpsc::Sender<AppEvent>) {
    tokio::spawn(async move {
        loop {
            let event_ready = tokio::task::spawn_blocking(|| event::poll(Duration::from_millis(250)))
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

fn spawn_mock_agent(input: String, tx: mpsc::Sender<AppEvent>) {
    tokio::spawn(async move {
        let reply = format!("(mock) I heard: {}", input);
        for chunk in reply.split_whitespace() {
            if tx.send(AppEvent::AgentChunk(chunk.to_string())).await.is_err() {
                return;
            }
            time::sleep(Duration::from_millis(80)).await;
        }
        let _ = tx.send(AppEvent::AgentDone).await;
    });
}

fn spawn_agent(messages: Vec<Message>, tx: mpsc::Sender<AppEvent>, api_key: String) {
    tokio::spawn(async move {
        // Use a default model, e.g., google/gemini-2.0-flash-001 (free on OpenRouter) or openai/gpt-3.5-turbo
        let provider = OpenRouterProvider::new(api_key, "google/gemini-2.0-flash-001".to_string());
        
        match provider.respond(&messages).await {
            Ok(events) => {
                for event in events {
                    match event {
                        AgentEvent::MessageDelta(content) => {
                             if tx.send(AppEvent::AgentChunk(content)).await.is_err() {
                                return;
                            }
                        }
                        _ => {}
                    }
                }
            }
            Err(e) => {
                let _ = tx.send(AppEvent::AgentChunk(format!("Error: {}", e))).await;
            }
        }
        let _ = tx.send(AppEvent::AgentDone).await;
    });
}

