use std::path::Path;
use std::sync::Arc;

use async_trait::async_trait;
use cersei::types::{MemoryEntry, Message, Result, Role, SessionInfo};
use cersei_memory::graph::GraphMemory;
use cersei_memory::JsonlMemory;

/// Persists conversation transcripts and indexes recent turns into the graph store.
pub struct AlfredMemory {
    jsonl: JsonlMemory,
    graph: Arc<GraphMemory>,
}

impl AlfredMemory {
    pub fn open(db_path: &Path, sessions_dir: &Path) -> Result<Self> {
        if let Some(parent) = db_path.parent() {
            let _ = std::fs::create_dir_all(parent);
        }
        let _ = std::fs::create_dir_all(sessions_dir);

        let graph = Arc::new(GraphMemory::open(db_path)?);
        let jsonl = JsonlMemory::new(sessions_dir.to_path_buf());

        Ok(Self { jsonl, graph })
    }
}

#[async_trait]
impl cersei_memory::Memory for AlfredMemory {
    async fn store(&self, session_id: &str, messages: &[Message]) -> Result<()> {
        self.jsonl.store(session_id, messages).await?;

        if let Some(last_msg) = messages.last() {
            let content = last_msg.get_all_text();
            if !content.trim().is_empty() {
                let mem_type = match last_msg.role {
                    Role::User => cersei_memory::memdir::MemoryType::User,
                    _ => cersei_memory::memdir::MemoryType::Project,
                };
                let confidence = match last_msg.role {
                    Role::User => 0.9,
                    _ => 0.6,
                };
                let _ = self.graph.store_memory(&content, mem_type, confidence);
            }
        }

        Ok(())
    }

    async fn load(&self, session_id: &str) -> Result<Vec<Message>> {
        self.jsonl.load(session_id).await
    }

    async fn search(&self, query: &str, limit: usize) -> Result<Vec<MemoryEntry>> {
        let hits = self.graph.recall_top_k(query, limit);
        let mut entries = Vec::new();
        for (content, relevance) in hits {
            entries.push(MemoryEntry {
                content,
                relevance,
                source: "graph-db".to_string(),
            });
        }
        Ok(entries)
    }

    async fn sessions(&self) -> Result<Vec<SessionInfo>> {
        self.jsonl.sessions().await
    }

    async fn delete(&self, session_id: &str) -> Result<()> {
        self.jsonl.delete(session_id).await
    }
}
