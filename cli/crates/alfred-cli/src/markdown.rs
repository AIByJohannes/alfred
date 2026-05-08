use ratatui::style::{Color, Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui_core::layout::HorizontalAlignment;
use ratatui_core::style::{Color as CoreColor, Modifier as CoreModifier, Style as CoreStyle};
use tui_markdown::{from_str_with_options, Options, StyleSheet};

#[derive(Clone)]
struct OneDarkStyleSheet {
    base: CoreStyle,
}

impl StyleSheet for OneDarkStyleSheet {
    fn heading(&self, level: u8) -> CoreStyle {
        let mut style = self.base.add_modifier(CoreModifier::BOLD);
        if level == 1 {
            style = style.add_modifier(CoreModifier::UNDERLINED);
        }
        style
    }

    fn code(&self) -> CoreStyle {
        self.base.fg(CoreColor::Yellow)
    }

    fn link(&self) -> CoreStyle {
        self.base
            .fg(CoreColor::Blue)
            .add_modifier(CoreModifier::UNDERLINED)
    }

    fn blockquote(&self) -> CoreStyle {
        self.base.fg(CoreColor::Cyan)
    }

    fn heading_meta(&self) -> CoreStyle {
        self.base.add_modifier(CoreModifier::DIM)
    }

    fn metadata_block(&self) -> CoreStyle {
        self.base.fg(CoreColor::LightYellow)
    }
}

pub fn render_markdown(text: &str, base_style: Style) -> Vec<Line<'static>> {
    let core_base = to_core_style(base_style);
    let options = Options::new(OneDarkStyleSheet { base: core_base });
    let mut rendered = from_str_with_options(text, &options);

    for line in rendered.lines.iter_mut() {
        line.style = core_base.patch(line.style);
    }

    rendered
        .lines
        .into_iter()
        .map(|line| Line {
            spans: line
                .spans
                .into_iter()
                .map(|span| Span::styled(span.content.into_owned(), to_ratatui_style(span.style)))
                .collect(),
            style: to_ratatui_style(line.style),
            alignment: line.alignment.map(to_ratatui_alignment),
        })
        .collect()
}

fn to_core_style(style: Style) -> CoreStyle {
    CoreStyle {
        fg: style.fg.map(to_core_color),
        bg: style.bg.map(to_core_color),
        add_modifier: to_core_modifier(style.add_modifier),
        sub_modifier: to_core_modifier(style.sub_modifier),
    }
}

fn to_ratatui_style(style: CoreStyle) -> Style {
    Style {
        fg: style.fg.map(to_ratatui_color),
        bg: style.bg.map(to_ratatui_color),
        underline_color: None,
        add_modifier: to_ratatui_modifier(style.add_modifier),
        sub_modifier: to_ratatui_modifier(style.sub_modifier),
    }
}

fn to_core_color(color: Color) -> CoreColor {
    match color {
        Color::Reset => CoreColor::Reset,
        Color::Black => CoreColor::Black,
        Color::Red => CoreColor::Red,
        Color::Green => CoreColor::Green,
        Color::Yellow => CoreColor::Yellow,
        Color::Blue => CoreColor::Blue,
        Color::Magenta => CoreColor::Magenta,
        Color::Cyan => CoreColor::Cyan,
        Color::Gray => CoreColor::Gray,
        Color::DarkGray => CoreColor::DarkGray,
        Color::LightRed => CoreColor::LightRed,
        Color::LightGreen => CoreColor::LightGreen,
        Color::LightYellow => CoreColor::LightYellow,
        Color::LightBlue => CoreColor::LightBlue,
        Color::LightMagenta => CoreColor::LightMagenta,
        Color::LightCyan => CoreColor::LightCyan,
        Color::White => CoreColor::White,
        Color::Rgb(r, g, b) => CoreColor::Rgb(r, g, b),
        Color::Indexed(index) => CoreColor::Indexed(index),
    }
}

fn to_ratatui_color(color: CoreColor) -> Color {
    match color {
        CoreColor::Reset => Color::Reset,
        CoreColor::Black => Color::Black,
        CoreColor::Red => Color::Red,
        CoreColor::Green => Color::Green,
        CoreColor::Yellow => Color::Yellow,
        CoreColor::Blue => Color::Blue,
        CoreColor::Magenta => Color::Magenta,
        CoreColor::Cyan => Color::Cyan,
        CoreColor::Gray => Color::Gray,
        CoreColor::DarkGray => Color::DarkGray,
        CoreColor::LightRed => Color::LightRed,
        CoreColor::LightGreen => Color::LightGreen,
        CoreColor::LightYellow => Color::LightYellow,
        CoreColor::LightBlue => Color::LightBlue,
        CoreColor::LightMagenta => Color::LightMagenta,
        CoreColor::LightCyan => Color::LightCyan,
        CoreColor::White => Color::White,
        CoreColor::Rgb(r, g, b) => Color::Rgb(r, g, b),
        CoreColor::Indexed(index) => Color::Indexed(index),
    }
}

fn to_core_modifier(modifier: Modifier) -> CoreModifier {
    CoreModifier::from_bits_truncate(modifier.bits())
}

fn to_ratatui_modifier(modifier: CoreModifier) -> Modifier {
    Modifier::from_bits_truncate(modifier.bits())
}

fn to_ratatui_alignment(alignment: HorizontalAlignment) -> ratatui::layout::Alignment {
    match alignment {
        HorizontalAlignment::Left => ratatui::layout::Alignment::Left,
        HorizontalAlignment::Center => ratatui::layout::Alignment::Center,
        HorizontalAlignment::Right => ratatui::layout::Alignment::Right,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn lines_to_strings(lines: &[Line<'static>]) -> Vec<String> {
        lines
            .iter()
            .map(|line| {
                line.spans
                    .iter()
                    .map(|span| span.content.as_ref())
                    .collect::<String>()
            })
            .collect()
    }

    #[test]
    fn render_markdown_renders_blocks() {
        let input = "Hello\n\n- first\n- second\n\n```rust\nlet x = 1;\n```\n";
        let lines = render_markdown(input, Style::default());
        let rendered = lines_to_strings(&lines);

        assert!(rendered.iter().any(|line| line.contains("Hello")));
        assert!(rendered.iter().any(|line| line.contains("- first")));
        assert!(rendered.iter().any(|line| line.contains("- second")));
        assert!(rendered.iter().any(|line| line.contains("```rust")));
        assert!(rendered.iter().any(|line| line.contains("let x = 1;")));
        assert!(rendered.iter().any(|line| line.contains("```")));
    }

    #[test]
    fn render_markdown_renders_inline_code() {
        let input = "Use `inline` code";
        let lines = render_markdown(input, Style::default());
        let rendered = lines_to_strings(&lines);

        assert!(rendered.iter().any(|line| line.contains("inline")));
    }
}
