//! Rendering helpers for the interactive terminal UI.

use alfred_core::{Message, Role};
use ratatui::layout::{Alignment, Rect};
use ratatui::style::{Color, Style, Stylize};
use ratatui::text::{Line, Span, Text};
use ratatui::widgets::{Block, Borders, Clear, Paragraph, Wrap};
use ratatui::Frame;
use unicode_width::{UnicodeWidthChar, UnicodeWidthStr};

pub const ONEDARK_BG: Color = Color::Rgb(40, 44, 52);
pub const ONEDARK_FG: Color = Color::Rgb(171, 178, 191);
pub const ONEDARK_RED: Color = Color::Rgb(224, 108, 117);
pub const ONEDARK_GREEN: Color = Color::Rgb(152, 195, 121);
pub const ONEDARK_BLUE: Color = Color::Rgb(97, 175, 239);
pub const ONEDARK_MAGENTA: Color = Color::Rgb(198, 120, 221);

const MAX_WELCOME_WIDTH: u16 = 80;
const INPUT_PREFIX: &str = "> ";

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RunStatus {
    Idle,
    Running,
    Cancelling,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ChatLayout {
    pub transcript: Option<Rect>,
    pub composer: Rect,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct WelcomeLayout {
    pub heading: Option<Rect>,
    pub composer: Rect,
    pub hints: Option<Rect>,
}

/// Whether the transcript has anything worth showing beyond the system prompt.
pub fn conversation_started(messages: &[Message]) -> bool {
    messages
        .iter()
        .any(|message| !matches!(message.role, Role::System))
}

pub fn chat_layout(area: Rect) -> ChatLayout {
    if area.height == 0 {
        return ChatLayout {
            transcript: None,
            composer: Rect::new(area.x, area.y, area.width, 0),
        };
    }

    let composer_height = composer_height(area).min(area.height);
    let transcript_height = area.height - composer_height;
    let composer = Rect::new(
        area.x,
        area.y + transcript_height,
        area.width,
        composer_height,
    );
    let transcript =
        (transcript_height > 0).then(|| Rect::new(area.x, area.y, area.width, transcript_height));

    ChatLayout {
        transcript,
        composer,
    }
}

pub fn welcome_layout(area: Rect) -> WelcomeLayout {
    if area.height == 0 || area.width == 0 {
        return WelcomeLayout {
            heading: None,
            composer: Rect::new(area.x, area.y, area.width, 0),
            hints: None,
        };
    }

    let width = area.width.min(MAX_WELCOME_WIDTH);
    let x = area.x + (area.width - width) / 2;

    let composer_height = composer_height(area);
    let heading_height = if area.height >= 9 { 2 } else { 0 };
    let hints_height = if area.height >= 7 { 2 } else { 0 };
    let total = heading_height + composer_height + hints_height;
    let y = area.y + (area.height.saturating_sub(total)) / 2;

    let heading = (heading_height > 0).then(|| Rect::new(x, y, width, heading_height));
    let composer_y = y + heading_height;
    let composer = Rect::new(x, composer_y, width, composer_height);
    let hints =
        (hints_height > 0).then(|| Rect::new(x, composer_y + composer_height, width, hints_height));

    WelcomeLayout {
        heading,
        composer,
        hints,
    }
}

pub fn draw_welcome(frame: &mut Frame, input: &str, suggestions: &[String]) {
    let layout = welcome_layout(frame.size());

    if let Some(heading) = layout.heading {
        let text = Text::from(vec![
            Line::from(Span::styled(
                "Alfred",
                Style::default().fg(ONEDARK_MAGENTA).bold(),
            )),
            Line::from(Span::styled(
                "What are we working on?",
                Style::default().fg(ONEDARK_FG),
            )),
        ]);
        frame.render_widget(
            Paragraph::new(text)
                .alignment(Alignment::Center)
                .style(Style::default().bg(ONEDARK_BG)),
            heading,
        );
    }

    draw_composer(frame, layout.composer, input, "Input");

    if let Some(hints) = layout.hints {
        frame.render_widget(
            Paragraph::new(Line::from(vec![
                Span::styled("Enter", Style::default().fg(ONEDARK_FG).bold()),
                Span::styled(" send  ·  ", Style::default().fg(ONEDARK_FG)),
                Span::styled("/skills", Style::default().fg(ONEDARK_FG).bold()),
                Span::styled(" browse  ·  ", Style::default().fg(ONEDARK_FG)),
                Span::styled("Esc / Ctrl+C", Style::default().fg(ONEDARK_FG).bold()),
                Span::styled(" exit", Style::default().fg(ONEDARK_FG)),
            ]))
            .alignment(Alignment::Center)
            .style(Style::default().bg(ONEDARK_BG)),
            hints,
        );
    }

    draw_suggestions(frame, layout.composer, suggestions);
}

pub fn draw_conversation(
    frame: &mut Frame,
    messages: &Text<'_>,
    input: &str,
    scroll: u16,
    suggestions: &[String],
    status: RunStatus,
    follow: bool,
) -> u16 {
    let layout = chat_layout(frame.size());
    let mut max_scroll = 0;

    if let Some(transcript) = layout.transcript {
        let paragraph = Paragraph::new(messages.clone())
            .block(
                Block::default()
                    .borders(Borders::ALL)
                    .title("Alfred")
                    .border_style(Style::default().fg(ONEDARK_BLUE)),
            )
            .style(Style::default().fg(ONEDARK_FG).bg(ONEDARK_BG))
            .wrap(Wrap { trim: false });
        let width = transcript.width.saturating_sub(2);
        let viewport = transcript.height.saturating_sub(2) as usize;
        max_scroll = paragraph
            .line_count(width)
            .saturating_sub(viewport)
            .min(u16::MAX as usize) as u16;
        let offset = if follow {
            max_scroll
        } else {
            scroll.min(max_scroll)
        };

        frame.render_widget(paragraph.scroll((offset, 0)), transcript);
    }

    let title = match status {
        RunStatus::Cancelling => "Input · cancelling…",
        RunStatus::Running => "Input · Esc to cancel",
        RunStatus::Idle => "Input",
    };
    draw_composer(frame, layout.composer, input, title);
    draw_suggestions(frame, layout.composer, suggestions);
    max_scroll
}

fn draw_suggestions(frame: &mut Frame, composer: Rect, suggestions: &[String]) {
    if suggestions.is_empty() || composer.y == 0 || composer.width < 12 {
        return;
    }

    let content_rows = (suggestions.len() as u16).min(6);
    let rows = (content_rows + 2).min(composer.y);
    if rows < 3 {
        return;
    }
    let visible_rows = rows - 2;

    let width = composer.width.min(72);
    let x = composer.x + (composer.width - width) / 2;
    let rect = Rect::new(x, composer.y - rows, width, rows);
    let lines = suggestions
        .iter()
        .take(visible_rows as usize)
        .map(|suggestion| {
            Line::from(Span::styled(
                suggestion.clone(),
                Style::default().fg(ONEDARK_FG).bg(ONEDARK_BG),
            ))
        })
        .collect::<Vec<_>>();

    frame.render_widget(Clear, rect);
    frame.render_widget(
        Paragraph::new(Text::from(lines))
            .block(
                Block::default()
                    .borders(Borders::ALL)
                    .border_style(Style::default().fg(ONEDARK_BLUE)),
            )
            .style(Style::default().bg(ONEDARK_BG)),
        rect,
    );
}

pub fn render_transcript(messages: &[Message]) -> Text<'static> {
    let mut lines = Vec::new();
    for message in messages {
        let (label, color) = match message.role {
            Role::User => ("You", ONEDARK_GREEN),
            Role::Assistant => ("Alfred", ONEDARK_MAGENTA),
            Role::System => continue,
            Role::Tool => ("Tool", ONEDARK_RED),
        };

        lines.push(Line::from(vec![Span::styled(
            format!("{label}: "),
            Style::default().fg(color).bold(),
        )]));

        lines.extend(crate::markdown::render_markdown(
            &message.content,
            Style::default().fg(ONEDARK_FG),
        ));
        lines.push(Line::from(""));
    }
    Text::from(lines)
}

fn composer_height(area: Rect) -> u16 {
    if area.width >= 8 && area.height >= 5 {
        3
    } else {
        1
    }
}

fn draw_composer(frame: &mut Frame, area: Rect, input: &str, title: &str) {
    if area.width == 0 || area.height == 0 {
        return;
    }

    let bordered = area.height >= 3 && area.width >= 6;
    let inner = if bordered {
        Rect::new(
            area.x + 1,
            area.y + 1,
            area.width.saturating_sub(2),
            area.height.saturating_sub(2),
        )
    } else {
        area
    };

    if inner.width == 0 || inner.height == 0 {
        return;
    }

    let text_width = inner.width.saturating_sub(INPUT_PREFIX.width() as u16);
    let tail = visible_tail(input, text_width as usize);
    let visible = &input[tail..];
    let content = format!("{INPUT_PREFIX}{visible}");

    let mut block = Block::default().style(Style::default().bg(ONEDARK_BG));
    if bordered {
        block = block
            .borders(Borders::ALL)
            .title(title)
            .border_style(Style::default().fg(ONEDARK_BLUE));
    }
    frame.render_widget(
        Paragraph::new(content)
            .block(block)
            .style(Style::default().fg(ONEDARK_GREEN).bg(ONEDARK_BG))
            .wrap(Wrap { trim: false }),
        area,
    );

    let visible_width = visible.width() as u16;
    let cursor_x = inner
        .x
        .saturating_add(INPUT_PREFIX.width() as u16)
        .saturating_add(visible_width)
        .min(inner.x + inner.width - 1);
    frame.set_cursor(cursor_x, inner.y);
}

/// Byte offset of the longest suffix of `input` that fits in `width` columns.
fn visible_tail(input: &str, width: usize) -> usize {
    if width == 0 {
        return input.len();
    }

    let mut used = 0;
    let mut start = input.len();
    for (idx, ch) in input.char_indices().rev() {
        let ch_width = ch.width().unwrap_or(0);
        if used + ch_width > width {
            break;
        }
        used += ch_width;
        start = idx;
    }
    start
}

#[cfg(test)]
mod tests {
    use super::*;
    use ratatui::backend::TestBackend;
    use ratatui::Terminal;

    fn message(role: Role, content: &str) -> Message {
        Message::new(role, content.to_string())
    }

    fn buffer_text(terminal: &Terminal<TestBackend>) -> String {
        let buffer = terminal.backend().buffer();
        buffer
            .content
            .iter()
            .map(|cell| cell.symbol())
            .collect::<Vec<_>>()
            .join("")
    }

    fn render_welcome(width: u16, height: u16, input: &str) -> Terminal<TestBackend> {
        let mut terminal = Terminal::new(TestBackend::new(width, height)).unwrap();
        terminal
            .draw(|frame| draw_welcome(frame, input, &[]))
            .unwrap();
        terminal
    }

    #[test]
    fn detects_first_visible_message() {
        assert!(!conversation_started(&[]));
        assert!(!conversation_started(&[message(Role::System, "prompt")]));
        assert!(conversation_started(&[
            message(Role::System, "prompt"),
            message(Role::User, "hello"),
        ]));
        assert!(conversation_started(&[
            message(Role::System, "prompt"),
            message(Role::Assistant, "Skills listed"),
        ]));
    }

    #[test]
    fn welcome_layout_centers_and_stacks_sections() {
        let area = Rect::new(0, 0, 120, 30);
        let layout = welcome_layout(area);

        let composer = layout.composer;
        assert_eq!(composer.width, MAX_WELCOME_WIDTH);
        assert_eq!(composer.x, 20);
        assert_eq!(composer.height, 3);

        let heading = layout.heading.expect("heading should fit");
        let hints = layout.hints.expect("hints should fit");
        assert_eq!(heading.y + heading.height, composer.y);
        assert_eq!(composer.y + composer.height, hints.y);
        assert!(heading.y > 0);
        assert!(hints.y + hints.height < area.height);
    }

    #[test]
    fn chat_layout_puts_composer_at_bottom() {
        let area = Rect::new(2, 3, 60, 20);
        let layout = chat_layout(area);
        let transcript = layout.transcript.expect("transcript should fit");

        assert_eq!(layout.composer.y, area.y + area.height - 3);
        assert_eq!(layout.composer.height, 3);
        assert_eq!(transcript.y, area.y);
        assert_eq!(transcript.y + transcript.height, layout.composer.y);
    }

    #[test]
    fn layouts_are_bounds_safe_on_small_terminals() {
        for (width, height) in [(0, 0), (1, 1), (5, 2), (20, 4), (80, 5)] {
            let area = Rect::new(0, 0, width, height);
            let chat = chat_layout(area);
            let welcome = welcome_layout(area);
            assert!(chat.composer.right() <= area.right());
            assert!(chat.composer.bottom() <= area.bottom());
            assert!(welcome.composer.right() <= area.right());
            assert!(welcome.composer.bottom() <= area.bottom());
        }
    }

    #[test]
    fn transcript_skips_system_prompt() {
        let messages = vec![
            message(Role::System, "secret system prompt"),
            message(Role::User, "hello there"),
        ];
        let text = render_transcript(&messages);
        let rendered: String = text
            .lines
            .iter()
            .flat_map(|line| line.spans.iter())
            .map(|span| span.content.as_ref())
            .collect();

        assert!(rendered.contains("hello there"));
        assert!(!rendered.contains("secret system prompt"));
    }

    #[test]
    fn welcome_renders_heading_and_hints() {
        let terminal = render_welcome(80, 20, "");
        let text = buffer_text(&terminal);
        assert!(text.contains("Alfred"));
        assert!(text.contains("What are we working on?"));
        assert!(text.contains("Enter"));
        assert!(text.contains("exit"));
    }

    #[test]
    fn conversation_renders_transcript_after_transition() {
        let messages = Text::from(vec![Line::from("first user message")]);
        let mut terminal = Terminal::new(TestBackend::new(60, 16)).unwrap();
        terminal
            .draw(|frame| {
                draw_conversation(frame, &messages, "typing", 0, &[], RunStatus::Idle, true);
            })
            .unwrap();

        let text = buffer_text(&terminal);
        assert!(text.contains("first user message"));
        assert!(text.contains("Input"));
        assert!(!text.contains("What are we working on?"));
    }

    #[test]
    fn long_input_keeps_tail_and_cursor_inside_composer() {
        let input = "äöü-abcdefghijklmnopqrstuvwxyz-0123456789";
        let terminal = render_welcome(24, 8, input);
        let text = buffer_text(&terminal);

        assert!(text.contains("0123456789"));
        assert!(!text.contains("äöü"));
    }

    #[test]
    fn zero_sized_terminal_does_not_panic() {
        let mut terminal = Terminal::new(TestBackend::new(0, 0)).unwrap();
        terminal
            .draw(|frame| draw_welcome(frame, "hello", &[]))
            .unwrap();
    }

    #[test]
    fn slash_suggestions_render_above_composer() {
        let mut terminal = Terminal::new(TestBackend::new(80, 20)).unwrap();
        terminal
            .draw(|frame| draw_welcome(frame, "/", &["/skills — list skills".to_string()]))
            .unwrap();

        let text = buffer_text(&terminal);
        assert!(text.contains("/skills"));
    }
}
