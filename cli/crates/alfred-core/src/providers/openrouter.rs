use anyhow::{Context, Result};
use async_trait::async_trait;
use reqwest::Client;
use serde_json::json;

use crate::models::Message;
use crate::router::{AgentEvent, AgentRouter};

pub struct OpenRouterProvider {
    client: Client,
    api_key: String,
    model: String,
    base_url: String,
}

impl OpenRouterProvider {
    pub fn new(api_key: String, model: String) -> Self {
        Self {
            client: Client::new(),
            api_key,
            model,
            base_url: "https://openrouter.ai/api/v1".to_string(),
        }
    }
}

#[async_trait]
impl AgentRouter for OpenRouterProvider {
    async fn respond(&self, messages: &[Message]) -> Result<Vec<AgentEvent>> {
        let url = format!("{}/chat/completions", self.base_url);
        
        let request_body = json!({
            "model": self.model,
            "messages": messages,
        });

        let response = self.client
            .post(&url)
            .header("Authorization", format!("Bearer {}", self.api_key))
            // Optional headers for OpenRouter rankings
            .header("HTTP-Referer", "https://github.com/AIByJohannes/alfred-cli") 
            .header("X-Title", "Alfred CLI")
            .json(&request_body)
            .send()
            .await
            .context("Failed to send request to OpenRouter")?;

        if !response.status().is_success() {
            let error_text = response.text().await.unwrap_or_else(|_| "Unknown error".into());
            anyhow::bail!("OpenRouter API error: {}", error_text);
        }

        let response_json: serde_json::Value = response.json().await
            .context("Failed to parse OpenRouter response")?;

        parse_response(response_json)
    }
}

fn parse_response(json: serde_json::Value) -> Result<Vec<AgentEvent>> {
    let content = json["choices"][0]["message"]["content"]
        .as_str()
        .context("No content in response")?
        .to_string();

    Ok(vec![AgentEvent::MessageDelta(content)])
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn test_parse_response_success() {
        let response_json = json!({
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Hello there!"
                    }
                }
            ]
        });

        let events = parse_response(response_json).unwrap();
        assert_eq!(events.len(), 1);
        if let AgentEvent::MessageDelta(content) = &events[0] {
            assert_eq!(content, "Hello there!");
        } else {
            panic!("Expected MessageDelta event");
        }
    }

    #[test]
    fn test_parse_response_missing_content() {
        let response_json = json!({
            "choices": [
                {
                    "message": {
                        "role": "assistant"
                    }
                }
            ]
        });

        let result = parse_response(response_json);
        assert!(result.is_err());
    }
}
