use tokio::sync::mpsc;
use tokio_util::sync::CancellationToken;

use crate::models::Message;
use crate::router::{AgentEvent, AgentRouter};

#[derive(Debug, Clone)]
pub struct SessionConfig {
    pub max_events: usize,
}

impl Default for SessionConfig {
    fn default() -> Self {
        Self { max_events: 128 }
    }
}

#[derive(Debug)]
pub enum SessionEvent {
    Agent(AgentEvent),
    Cancelled,
}

pub struct AgentSession<R: AgentRouter> {
    router: R,
    config: SessionConfig,
    cancel: CancellationToken,
}

impl<R: AgentRouter> AgentSession<R> {
    pub fn new(router: R, config: SessionConfig) -> Self {
        Self {
            router,
            config,
            cancel: CancellationToken::new(),
        }
    }

    pub fn cancel_token(&self) -> CancellationToken {
        self.cancel.clone()
    }

    pub async fn run(
        &self,
        messages: Vec<Message>,
        sink: mpsc::Sender<SessionEvent>,
    ) -> anyhow::Result<()> {
        let events = self.router.respond(&messages).await?;
        for event in events.into_iter().take(self.config.max_events) {
            if self.cancel.is_cancelled() {
                let _ = sink.send(SessionEvent::Cancelled).await;
                return Ok(());
            }
            if sink.send(SessionEvent::Agent(event)).await.is_err() {
                break;
            }
        }
        Ok(())
    }
}
