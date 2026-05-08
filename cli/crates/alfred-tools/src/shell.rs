use std::process::Command;

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ShellCommand {
    pub program: String,
    pub args: Vec<String>,
    pub cwd: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CommandOutput {
    pub status: i32,
    pub stdout: String,
    pub stderr: String,
}

#[derive(Debug, Default)]
pub struct ShellTool;

impl ShellTool {
    pub fn run(&self, command: ShellCommand) -> anyhow::Result<CommandOutput> {
        let mut cmd = Command::new(command.program);
        cmd.args(command.args);
        if let Some(cwd) = command.cwd {
            cmd.current_dir(cwd);
        }
        let output = cmd.output()?;
        Ok(CommandOutput {
            status: output.status.code().unwrap_or(-1),
            stdout: String::from_utf8_lossy(&output.stdout).to_string(),
            stderr: String::from_utf8_lossy(&output.stderr).to_string(),
        })
    }
}
