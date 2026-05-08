use std::path::PathBuf;
use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use tokio::fs;

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct Config {
    pub openrouter_api_key: Option<String>,
}

impl Config {
    pub async fn load() -> Result<Self> {
        let config_path = get_config_path()?;
        if !config_path.exists() {
            return Ok(Self::default());
        }

        let content = fs::read_to_string(&config_path)
            .await
            .context("Failed to read config file")?;
        
        let config: Config = toml::from_str(&content)
            .context("Failed to parse config file")?;

        Ok(config)
    }

    pub async fn save(&self) -> Result<()> {
        let config_path = get_config_path()?;
        if let Some(parent) = config_path.parent() {
            fs::create_dir_all(parent)
                .await
                .context("Failed to create config directory")?;
        }

        let content = toml::to_string(self)
            .context("Failed to serialize config")?;

        fs::write(&config_path, content)
            .await
            .context("Failed to write config file")?;

        Ok(())
    }
}

fn get_config_path() -> Result<PathBuf> {
    let home = dirs::home_dir().context("Could not determine home directory")?;
    Ok(home.join(".config").join("alfred").join("config.toml"))
}

pub fn get_prompts_dir() -> Result<PathBuf> {
    let home = dirs::home_dir().context("Could not determine home directory")?;
    Ok(home.join(".config").join("alfred").join("prompts"))
}

pub async fn load_system_prompt() -> Option<String> {
    if let Ok(prompts_dir) = get_prompts_dir() {
        let soul_path = prompts_dir.join("SOUL.md");
        if soul_path.exists() {
             return fs::read_to_string(soul_path).await.ok();
        }
    }
    None
}
