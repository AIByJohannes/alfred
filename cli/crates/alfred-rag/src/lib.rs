use async_trait::async_trait;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Chunk {
    pub id: String,
    pub text: String,
    pub metadata: serde_json::Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QueryResult {
    pub chunk_id: String,
    pub score: f32,
}

#[async_trait]
pub trait Embedder: Send + Sync {
    async fn embed(&self, text: &str) -> anyhow::Result<Vec<f32>>;
}

#[async_trait]
pub trait Index: Send + Sync {
    async fn add(&self, chunk: Chunk, embedding: Vec<f32>) -> anyhow::Result<()>;
    async fn query(&self, embedding: Vec<f32>, top_k: usize) -> anyhow::Result<Vec<QueryResult>>;
}

pub struct InMemoryIndex;

#[async_trait]
impl Index for InMemoryIndex {
    async fn add(&self, _chunk: Chunk, _embedding: Vec<f32>) -> anyhow::Result<()> {
        Ok(())
    }

    async fn query(&self, _embedding: Vec<f32>, _top_k: usize) -> anyhow::Result<Vec<QueryResult>> {
        Ok(Vec::new())
    }
}
