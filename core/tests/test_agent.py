import pytest
from unittest.mock import MagicMock, patch
from core.llm import LLMEngine

@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "fake-model")

@patch("core.llm.CodeAgent")
@patch("core.llm.OpenAIServerModel")
def test_llm_engine_initialization(mock_model, mock_agent, mock_env):
    engine = LLMEngine()
    
    mock_model.assert_called_once()
    mock_agent.assert_called_once()
    assert engine.model_id == "fake-model"

@patch("core.llm.CodeAgent")
@patch("core.llm.OpenAIServerModel")
def test_llm_engine_run(mock_model, mock_agent_class, mock_env):
    # Setup mock agent instance
    mock_agent_instance = MagicMock()
    mock_agent_instance.run.return_value = "Agent response"
    mock_agent_class.return_value = mock_agent_instance
    
    engine = LLMEngine()
    result = engine.run("Test prompt")
    
    mock_agent_instance.run.assert_called_once_with("Test prompt")
    assert result == "Agent response"

def test_llm_engine_missing_api_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    
    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY is not set"):
        LLMEngine()
