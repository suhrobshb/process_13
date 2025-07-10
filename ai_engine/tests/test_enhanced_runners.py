"""
Tests for Enhanced Runners - Comprehensive coverage
=================================================

This test suite provides comprehensive coverage for the enhanced runners
including BrowserRunner, DesktopRunner, and LLMRunner.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path

# Import the runners to test
from ai_engine.enhanced_runners.browser_runner import BrowserRunner
from ai_engine.enhanced_runners.desktop_runner import DesktopRunner  
from ai_engine.enhanced_runners.llm_runner import LLMRunner, LLMFactory


class TestBrowserRunner:
    """Test suite for BrowserRunner"""
    
    @pytest.fixture
    def browser_params(self):
        """Sample parameters for browser runner"""
        return {
            "actions": [
                {"type": "goto", "url": "https://example.com"},
                {"type": "click", "selector": "#submit-btn"},
                {"type": "fill", "selector": "#email", "text": "test@example.com"}
            ],
            "browser_type": "chromium",
            "headless": True,
            "timeout": 30
        }
    
    @patch('ai_engine.enhanced_runners.browser_runner.sync_playwright')
    def test_browser_runner_initialization(self, mock_playwright, browser_params):
        """Test BrowserRunner initialization"""
        runner = BrowserRunner("test_step", browser_params)
        
        assert runner.step_id == "test_step"
        assert runner.actions == browser_params["actions"]
        assert runner.browser_type == "chromium"
        assert runner.headless == True
        assert runner.timeout == 30
    
    @patch('ai_engine.enhanced_runners.browser_runner.sync_playwright')
    def test_browser_runner_execution_success(self, mock_playwright, browser_params):
        """Test successful browser runner execution"""
        # Mock Playwright components
        mock_browser = Mock()
        mock_page = Mock()
        mock_browser.new_page.return_value = mock_page
        mock_playwright_instance = Mock()
        mock_playwright_instance.chromium.launch.return_value = mock_browser
        mock_playwright.return_value.__enter__.return_value = mock_playwright_instance
        
        runner = BrowserRunner("test_step", browser_params)
        result = runner.execute()
        
        assert result["success"] == True
        assert "results" in result
        assert "execution_time_seconds" in result
        
        # Verify browser interactions
        mock_browser.new_page.assert_called_once()
        mock_page.set_default_timeout.assert_called_once()
        mock_browser.close.assert_called_once()
    
    @patch('ai_engine.enhanced_runners.browser_runner.sync_playwright')
    def test_browser_action_execution(self, mock_playwright, browser_params):
        """Test individual browser action execution"""
        mock_browser = Mock()
        mock_page = Mock()
        mock_locator = Mock()
        mock_page.locator.return_value = mock_locator
        mock_browser.new_page.return_value = mock_page
        mock_playwright_instance = Mock()
        mock_playwright_instance.chromium.launch.return_value = mock_browser
        mock_playwright.return_value.__enter__.return_value = mock_playwright_instance
        
        runner = BrowserRunner("test_step", browser_params)
        result = runner.execute()
        
        # Verify specific actions were called
        mock_page.goto.assert_called_with("https://example.com", wait_until="load")
        mock_page.click.assert_called()
        mock_page.fill.assert_called()
    
    @patch('ai_engine.enhanced_runners.browser_runner.sync_playwright')
    def test_browser_runner_timeout_handling(self, mock_playwright):
        """Test browser runner timeout handling"""
        # Create params with very short timeout and many actions
        timeout_params = {
            "actions": [{"type": "wait", "duration": 60}] * 10,  # Long-running actions
            "timeout": 1  # Very short timeout
        }
        
        mock_browser = Mock()
        mock_page = Mock() 
        mock_browser.new_page.return_value = mock_page
        mock_playwright_instance = Mock()
        mock_playwright_instance.chromium.launch.return_value = mock_browser
        mock_playwright.return_value.__enter__.return_value = mock_playwright_instance
        
        runner = BrowserRunner("test_step", timeout_params)
        result = runner.execute()
        
        assert result["success"] == False
        assert "timeout" in result.get("error", "").lower()
    
    def test_browser_runner_without_playwright(self):
        """Test browser runner when Playwright is not available"""
        with patch('ai_engine.enhanced_runners.browser_runner.PLAYWRIGHT_AVAILABLE', False):
            with pytest.raises(ImportError, match="Browser automation is not available"):
                BrowserRunner("test_step", {"actions": []})


class TestDesktopRunner:
    """Test suite for DesktopRunner"""
    
    @pytest.fixture
    def desktop_params(self):
        """Sample parameters for desktop runner"""
        return {
            "actions": [
                {"type": "click", "x": 100, "y": 200},
                {"type": "type", "text": "Hello World"},
                {"type": "hotkey", "keys": ["ctrl", "s"]}
            ],
            "timeout": 60
        }
    
    @patch('ai_engine.enhanced_runners.desktop_runner.pyautogui')
    def test_desktop_runner_initialization(self, mock_pyautogui, desktop_params):
        """Test DesktopRunner initialization"""
        mock_pyautogui.size.return_value = (1920, 1080)
        
        runner = DesktopRunner("test_step", desktop_params)
        
        assert runner.step_id == "test_step"
        assert runner.actions == desktop_params["actions"]
        assert runner.timeout == 60
        assert runner.screen_size == (1920, 1080)
    
    @patch('ai_engine.enhanced_runners.desktop_runner.pyautogui')
    def test_desktop_runner_execution_success(self, mock_pyautogui, desktop_params):
        """Test successful desktop runner execution"""
        mock_pyautogui.size.return_value = (1920, 1080)
        
        runner = DesktopRunner("test_step", desktop_params)
        result = runner.execute()
        
        assert result["success"] == True
        assert "results" in result
        assert len(result["results"]) == 3  # Three actions
        
        # Verify PyAutoGUI calls
        mock_pyautogui.click.assert_called_with(x=100, y=200, clicks=1, interval=0.1, button='left')
        mock_pyautogui.write.assert_called_with('Hello World', interval=0.05)
        mock_pyautogui.hotkey.assert_called_with('ctrl', 's')
    
    @patch('ai_engine.enhanced_runners.desktop_runner.pyautogui')
    def test_desktop_action_types(self, mock_pyautogui):
        """Test different desktop action types"""
        mock_pyautogui.size.return_value = (1920, 1080)
        
        action_tests = [
            {"type": "move", "x": 300, "y": 400, "duration": 0.5},
            {"type": "drag", "x": 500, "y": 600, "duration": 1.0, "button": "left"},
            {"type": "scroll", "amount": 3, "x": 100, "y": 100},
            {"type": "press", "keys": ["enter"], "presses": 1},
        ]
        
        for action in action_tests:
            params = {"actions": [action]}
            runner = DesktopRunner("test_step", params)
            result = runner.execute()
            
            assert result["success"] == True
            assert len(result["results"]) == 1
    
    @patch('ai_engine.enhanced_runners.desktop_runner.pyautogui')
    def test_context_variable_substitution(self, mock_pyautogui):
        """Test context variable substitution in desktop actions"""
        mock_pyautogui.size.return_value = (1920, 1080)
        
        params = {
            "actions": [
                {"type": "type", "text": "Hello ${username}"},
                {"type": "hotkey", "keys": ["${modifier}", "s"]}
            ]
        }
        context = {"username": "Alice", "modifier": "ctrl"}
        
        runner = DesktopRunner("test_step", params)
        result = runner.execute(context)
        
        assert result["success"] == True
        mock_pyautogui.write.assert_called_with('Hello Alice', interval=0.05)
        mock_pyautogui.hotkey.assert_called_with('ctrl', 's')
    
    @patch('ai_engine.enhanced_runners.desktop_runner.pyautogui')
    def test_desktop_runner_error_handling(self, mock_pyautogui):
        """Test desktop runner error handling"""
        mock_pyautogui.size.return_value = (1920, 1080)
        mock_pyautogui.click.side_effect = Exception("PyAutoGUI error")
        
        params = {"actions": [{"type": "click", "x": 100, "y": 200}]}
        runner = DesktopRunner("test_step", params)
        result = runner.execute()
        
        assert result["success"] == False
        assert "PyAutoGUI error" in result["error"]
    
    def test_desktop_runner_without_pyautogui(self):
        """Test desktop runner when PyAutoGUI is not available"""
        with patch('ai_engine.enhanced_runners.desktop_runner.PYAUTOGUI_AVAILABLE', False):
            with pytest.raises(ImportError, match="Desktop automation is not available"):
                DesktopRunner("test_step", {"actions": []})


class TestLLMRunner:
    """Test suite for LLMRunner and LLMFactory"""
    
    @pytest.fixture
    def llm_params(self):
        """Sample parameters for LLM runner"""
        return {
            "provider": "openai",
            "model": "gpt-3.5-turbo",
            "prompt_template": "Summarize: {{ context.text }}",
            "llm_kwargs": {"temperature": 0.7, "max_tokens": 100}
        }
    
    def test_llm_runner_initialization(self, llm_params):
        """Test LLMRunner initialization"""
        runner = LLMRunner("test_step", llm_params)
        
        assert runner.step_id == "test_step"
        assert runner.provider_name == "openai"
        assert runner.model == "gpt-3.5-turbo"
        assert runner.llm_kwargs == {"temperature": 0.7, "max_tokens": 100}
    
    def test_llm_runner_missing_params(self):
        """Test LLMRunner with missing required parameters"""
        with pytest.raises(ValueError, match="requires 'provider', 'model', and 'prompt_template'"):
            LLMRunner("test_step", {"provider": "openai"})  # Missing model and template
    
    @patch('ai_engine.enhanced_runners.llm_runner.record_llm_request')
    @patch('ai_engine.enhanced_runners.llm_runner.record_llm_token_usage')
    def test_llm_runner_execution_success(self, mock_record_tokens, mock_record_request, llm_params):
        """Test successful LLM runner execution"""
        # Mock the provider
        mock_provider = Mock()
        mock_provider.generate.return_value = {
            "text": "This is a test response",
            "metadata": {
                "provider": "openai",
                "model": "gpt-3.5-turbo",
                "token_usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
            }
        }
        
        with patch.object(LLMFactory, 'create_provider', return_value=mock_provider):
            runner = LLMRunner("test_step", llm_params)
            context = {"text": "This is sample text to summarize"}
            result = runner.execute(context)
        
        assert result["success"] == True
        assert result["result"]["raw_text"] == "This is a test response"
        assert "execution_time_seconds" in result
        
        # Verify metrics were recorded
        mock_record_request.assert_called_once()
        mock_record_tokens.assert_called_once()
    
    def test_llm_runner_template_rendering(self, llm_params):
        """Test prompt template rendering"""
        runner = LLMRunner("test_step", llm_params)
        context = {"text": "Hello World"}
        
        rendered = runner._render_prompt(context)
        assert "Hello World" in rendered
    
    def test_llm_runner_structured_output_parsing(self, llm_params):
        """Test structured output parsing"""
        llm_params["output_schema"] = {"type": "object"}
        runner = LLMRunner("test_step", llm_params)
        
        # Test JSON in markdown
        json_text = '```json\n{"result": "success", "confidence": 0.95}\n```'
        parsed = runner._parse_structured_output(json_text)
        assert parsed == {"result": "success", "confidence": 0.95}
        
        # Test plain JSON
        plain_json = '{"result": "success"}'
        parsed = runner._parse_structured_output(plain_json)
        assert parsed == {"result": "success"}
        
        # Test invalid JSON
        invalid_json = 'not json at all'
        parsed = runner._parse_structured_output(invalid_json)
        assert parsed is None
    
    def test_llm_runner_error_handling(self, llm_params):
        """Test LLM runner error handling"""
        mock_provider = Mock()
        mock_provider.generate.side_effect = Exception("API Error")
        
        with patch.object(LLMFactory, 'create_provider', return_value=mock_provider):
            runner = LLMRunner("test_step", llm_params)
            result = runner.execute({"text": "test"})
        
        assert result["success"] == False
        assert "API Error" in result["error"]


class TestLLMFactory:
    """Test suite for LLMFactory"""
    
    @patch('ai_engine.enhanced_runners.llm_runner.OpenAI')
    def test_openai_provider_creation(self, mock_openai):
        """Test OpenAI provider creation"""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            provider = LLMFactory.create_provider("openai", "gpt-3.5-turbo")
            assert provider.model == "gpt-3.5-turbo"
            mock_openai.assert_called_with(api_key='test-key')
    
    @patch('ai_engine.enhanced_runners.llm_runner.Anthropic')
    def test_anthropic_provider_creation(self, mock_anthropic):
        """Test Anthropic provider creation"""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            provider = LLMFactory.create_provider("anthropic", "claude-3-sonnet")
            assert provider.model == "claude-3-sonnet"
            mock_anthropic.assert_called_with(api_key='test-key')
    
    @patch('ai_engine.enhanced_runners.llm_runner.requests')
    def test_ollama_provider_creation(self, mock_requests):
        """Test Ollama provider creation"""
        provider = LLMFactory.create_provider("ollama", "llama3")
        assert provider.model == "llama3"
        assert provider.endpoint == "http://localhost:11434/api/generate"
    
    def test_unsupported_provider(self):
        """Test unsupported provider handling"""
        with pytest.raises(ValueError, match="Unsupported LLM provider"):
            LLMFactory.create_provider("unsupported", "model")


class TestRunnerIntegration:
    """Integration tests for runners working together"""
    
    @patch('ai_engine.enhanced_runners.browser_runner.sync_playwright')
    @patch('ai_engine.enhanced_runners.desktop_runner.pyautogui')
    def test_mixed_runner_workflow(self, mock_pyautogui, mock_playwright):
        """Test a workflow using multiple runner types"""
        # Setup mocks
        mock_pyautogui.size.return_value = (1920, 1080)
        mock_browser = Mock()
        mock_page = Mock()
        mock_browser.new_page.return_value = mock_page
        mock_playwright_instance = Mock()
        mock_playwright_instance.chromium.launch.return_value = mock_browser
        mock_playwright.return_value.__enter__.return_value = mock_playwright_instance
        
        # Browser step
        browser_params = {
            "actions": [{"type": "goto", "url": "https://example.com"}]
        }
        browser_runner = BrowserRunner("browser_step", browser_params)
        browser_result = browser_runner.execute()
        
        # Desktop step
        desktop_params = {
            "actions": [{"type": "click", "x": 100, "y": 200}]
        }
        desktop_runner = DesktopRunner("desktop_step", desktop_params)
        desktop_result = desktop_runner.execute()
        
        # Both should succeed
        assert browser_result["success"] == True
        assert desktop_result["success"] == True
    
    def test_runner_performance_benchmarks(self):
        """Performance benchmarks for runners"""
        import time
        
        # Test initialization performance
        start_time = time.time()
        for i in range(100):
            runner = LLMRunner(f"test_step_{i}", {
                "provider": "openai",
                "model": "gpt-3.5-turbo", 
                "prompt_template": "Test prompt"
            })
        init_time = time.time() - start_time
        
        # Should initialize 100 runners in reasonable time
        assert init_time < 1.0, f"Runner initialization too slow: {init_time}s"


class TestRunnerErrorRecovery:
    """Test error recovery and resilience patterns"""
    
    @patch('ai_engine.enhanced_runners.desktop_runner.pyautogui')
    def test_desktop_runner_partial_failure_recovery(self, mock_pyautogui):
        """Test desktop runner continues after partial failures"""
        mock_pyautogui.size.return_value = (1920, 1080)
        
        # First action fails, second succeeds
        mock_pyautogui.click.side_effect = Exception("Click failed")
        
        params = {
            "actions": [
                {"type": "click", "x": 100, "y": 200, "stop_on_failure": False},
                {"type": "type", "text": "Hello"}
            ]
        }
        
        runner = DesktopRunner("test_step", params)
        result = runner.execute()
        
        # Should continue executing despite first failure
        assert len(result["results"]) == 2
        assert result["results"][0]["success"] == False
        assert result["results"][1]["success"] == True
        mock_pyautogui.write.assert_called_once()
    
    @patch('ai_engine.enhanced_runners.browser_runner.sync_playwright')
    def test_browser_runner_screenshot_on_error(self, mock_playwright):
        """Test browser runner takes screenshot on error"""
        mock_browser = Mock()
        mock_page = Mock()
        mock_page.click.side_effect = Exception("Element not found")
        mock_browser.new_page.return_value = mock_page
        mock_playwright_instance = Mock()
        mock_playwright_instance.chromium.launch.return_value = mock_browser
        mock_playwright.return_value.__enter__.return_value = mock_playwright_instance
        
        params = {
            "actions": [{"type": "click", "selector": "#missing-element"}]
        }
        
        runner = BrowserRunner("test_step", params)
        result = runner.execute()
        
        # Should attempt error screenshot
        mock_page.screenshot.assert_called()
        assert result["success"] == False


if __name__ == "__main__":
    # Run basic smoke tests
    print("Running Enhanced Runners smoke tests...")
    
    # Test that we can import all runners
    from ai_engine.enhanced_runners.browser_runner import BrowserRunner
    from ai_engine.enhanced_runners.desktop_runner import DesktopRunner
    from ai_engine.enhanced_runners.llm_runner import LLMRunner
    
    print("✅ All runner imports successful")
    
    # Test basic initialization
    try:
        llm_runner = LLMRunner("test", {
            "provider": "openai",
            "model": "gpt-3.5-turbo",
            "prompt_template": "Test"
        })
        print("✅ LLM runner initialization works")
    except Exception as e:
        print(f"❌ LLM runner initialization failed: {e}")
    
    print("✅ Enhanced runners smoke tests completed!")