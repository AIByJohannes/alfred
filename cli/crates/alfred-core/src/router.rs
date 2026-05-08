use async_trait::async_trait;
use serde::{Deserialize, Serialize};

use crate::models::Message;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolCall {
    pub name: String,
    pub arguments: serde_json::Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolResult {
    pub name: String,
    pub output: serde_json::Value,
    pub is_error: bool,
}

#[derive(Debug, Clone)]
pub enum AgentEvent {
    MessageDelta(String),
    ToolRequest(ToolCall),
    ToolResult(ToolResult),
    Done,
}

#[async_trait]
pub trait AgentRouter: Send + Sync {
    async fn respond(&self, messages: &[Message]) -> anyhow::Result<Vec<AgentEvent>>;
}
