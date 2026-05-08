use std::process::Command;

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GitWorkspaceStatus {
    pub clean: bool,
    pub summary: String,
}

#[derive(Debug, Default)]
pub struct GitTool;

impl GitTool {
    pub fn status(&self, cwd: &str) -> anyhow::Result<GitWorkspaceStatus> {
        let output = Command::new("git")
            .arg("status")
            .arg("--porcelain")
            .current_dir(cwd)
            .output()?;
        let summary = String::from_utf8_lossy(&output.stdout).trim().to_string();
        Ok(GitWorkspaceStatus {
            clean: summary.is_empty(),
            summary,
        })
    }

    pub fn diff(&self, cwd: &str) -> anyhow::Result<String> {
        let output = Command::new("git")
            .arg("diff")
            .current_dir(cwd)
            .output()?;
        Ok(String::from_utf8_lossy(&output.stdout).to_string())
    }
}
