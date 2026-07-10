use std::sync::Arc;

use async_trait::async_trait;
use cersei::mcp::{McpManager, McpServerConfig};
use cersei::tools::{PermissionLevel, Tool, ToolCategory, ToolContext, ToolResult};
use serde_json::{json, Value};

pub async fn connect_tool(configs: &[McpServerConfig]) -> Option<Box<dyn Tool>> {
    if configs.is_empty() {
        return None;
    }

    let manager = McpManager::connect(configs).await.ok()?;
    let definitions = manager.tool_definitions().await;
    if definitions.is_empty() {
        return None;
    }

    let tool_names = definitions.into_iter().map(|tool| tool.name).collect();
    Some(Box::new(McpCallTool {
        manager: Arc::new(manager),
        tool_names,
    }))
}

struct McpCallTool {
    manager: Arc<McpManager>,
    tool_names: Vec<String>,
}

#[async_trait]
impl Tool for McpCallTool {
    fn name(&self) -> &str {
        "mcp_call"
    }

    fn description(&self) -> &str {
        "Call a tool exposed by a configured Model Context Protocol server."
    }

    fn input_schema(&self) -> Value {
        json!({
            "type": "object",
            "properties": {
                "name": { "type": "string", "enum": self.tool_names },
                "arguments": { "type": "object" }
            },
            "required": ["name"]
        })
    }

    fn permission_level(&self) -> PermissionLevel {
        PermissionLevel::Execute
    }

    fn category(&self) -> ToolCategory {
        ToolCategory::Mcp
    }

    async fn execute(&self, input: Value, _ctx: &ToolContext) -> ToolResult {
        let Some(name) = input.get("name").and_then(Value::as_str) else {
            return ToolResult::error("mcp_call requires a tool name");
        };
        let arguments = input.get("arguments").cloned();
        match self.manager.call_tool(name, arguments).await {
            Ok(output) => ToolResult::success(output),
            Err(error) => ToolResult::error(error.to_string()),
        }
    }
}
