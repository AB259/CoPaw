# -*- coding: utf-8 -*-
"""Unit tests for skills_manager trigger detection."""
import pytest

from copaw.agents.skills_manager import (
    SkillTriggerRule,
    _parse_trigger_from_description,
)


class TestParseTriggerFromDescription:
    """Test _parse_trigger_from_description function."""

    def test_extract_tool_names_from_description(self):
        """Test extracting tool names directly mentioned in description."""
        description = "Use browser_use to navigate web pages"
        keywords, tool_hints = _parse_trigger_from_description(description)

        assert "browser_use" in tool_hints

    def test_extract_shell_tool(self):
        """Test extracting shell/execute_shell_command tool hints."""
        description = "Execute shell commands to run scripts"
        keywords, tool_hints = _parse_trigger_from_description(description)

        assert "execute_shell_command" in tool_hints

    def test_extract_file_tools(self):
        """Test extracting file-related tool hints."""
        description = "Read and write files, edit file content"
        keywords, tool_hints = _parse_trigger_from_description(description)

        assert "read_file" in tool_hints
        assert "write_file" in tool_hints
        assert "edit_file" in tool_hints

    def test_infer_browser_tool_from_domain(self):
        """Test inferring browser_use from domain terms."""
        description = "Navigate to web pages and click buttons"
        keywords, tool_hints = _parse_trigger_from_description(description)

        assert "browser_use" in tool_hints

    def test_infer_file_tool_from_extensions(self):
        """Test inferring file tools from file extensions."""
        description = "Process PDF and Excel files"
        keywords, tool_hints = _parse_trigger_from_description(description)

        assert "read_file" in tool_hints
        # "excel" is detected as domain keyword (lowercase description)
        assert "excel" in keywords
        # Note: "PDF" uppercase is not matched by extension regex,
        # but "pdf" domain still maps to read_file tool

    def test_extract_chinese_keywords(self):
        """Test extracting Chinese domain terms."""
        description = "处理网页和文件操作"
        keywords, tool_hints = _parse_trigger_from_description(description)

        # Chinese terms are extracted as 2-6 char sequences
        # Domain inference works for 网页 -> browser_use, 文件 -> read_file
        assert "browser_use" in tool_hints
        assert "read_file" in tool_hints
        # Verify some Chinese keywords were extracted
        assert len(keywords) > 0
        assert any("网页" in kw or "文件" in kw for kw in keywords)

    def test_filter_stop_words(self):
        """Test that stop words are filtered out."""
        description = "This is a test with some common words that should be filtered"
        keywords, tool_hints = _parse_trigger_from_description(description)

        # Stop words should not be in keywords
        assert "this" not in keywords
        assert "with" not in keywords
        assert "some" not in keywords
        assert "that" not in keywords
        assert "should" not in keywords

    def test_filter_chinese_stop_words(self):
        """Test that Chinese stop words are filtered out."""
        description = "这是一个测试，可以用来验证停用词过滤"
        keywords, tool_hints = _parse_trigger_from_description(description)

        # Chinese stop words should not be in keywords
        assert "这个" not in keywords
        assert "一个" not in keywords
        assert "可以" not in keywords

    def test_extract_file_extensions(self):
        """Test extracting file extensions as keywords."""
        description = "Process .py files and .md documents"
        keywords, tool_hints = _parse_trigger_from_description(description)

        assert "py" in keywords
        assert "md" in keywords

    def test_extract_quoted_strings(self):
        """Test extracting quoted strings as keywords."""
        description = 'Use "browser_use" tool for "web navigation"'
        keywords, tool_hints = _parse_trigger_from_description(description)

        assert "browser_use" in keywords
        assert "web navigation" in keywords

    def test_screenshot_tool_detection(self):
        """Test detecting screenshot-related tools."""
        description = "Take desktop screenshot for debugging"
        keywords, tool_hints = _parse_trigger_from_description(description)

        assert "desktop_screenshot" in tool_hints

    def test_chinese_command_keyword(self):
        """Test Chinese command/shell keyword detection."""
        description = "执行命令行操作"
        keywords, tool_hints = _parse_trigger_from_description(description)

        assert "execute_shell_command" in tool_hints
        # Verify some Chinese keywords were extracted
        assert len(keywords) > 0

    def test_empty_description(self):
        """Test handling empty description."""
        description = ""
        keywords, tool_hints = _parse_trigger_from_description(description)

        assert keywords == []
        assert tool_hints == []

    def test_description_with_only_stop_words(self):
        """Test description containing only stop words."""
        description = "the with from have will been were they their would could"
        keywords, tool_hints = _parse_trigger_from_description(description)

        # All English stop words should be filtered
        assert keywords == []

    def test_mixed_language_description(self):
        """Test mixed Chinese and English description."""
        description = "Use browser to open 网页 and click buttons"
        keywords, tool_hints = _parse_trigger_from_description(description)

        assert "browser_use" in tool_hints
        assert "网页" in keywords
        assert "buttons" in keywords


class TestSkillTriggerRule:
    """Test SkillTriggerRule model."""

    def test_create_trigger_rule(self):
        """Test creating a SkillTriggerRule instance."""
        rule = SkillTriggerRule(
            skill_name="test_skill",
            description="A test skill for PDF processing",
            keywords=["pdf", "process"],
            tool_hints=["read_file"],
        )

        assert rule.skill_name == "test_skill"
        assert rule.description == "A test skill for PDF processing"
        assert rule.keywords == ["pdf", "process"]
        assert rule.tool_hints == ["read_file"]

    def test_default_values(self):
        """Test default values for keywords and tool_hints."""
        rule = SkillTriggerRule(
            skill_name="minimal_skill",
            description="Minimal description",
        )

        assert rule.keywords == []
        assert rule.tool_hints == []


class TestNewSkillRecognition:
    """Test recognition of newly added skills based on description patterns."""

    def test_recognize_pdf_skill(self):
        """Test recognizing a PDF processing skill."""
        description = "Extract text from PDF files and convert to markdown"
        keywords, tool_hints = _parse_trigger_from_description(description)

        # Should detect file-related tools
        assert "read_file" in tool_hints
        # Should have relevant keywords
        assert "extract" in keywords or "markdown" in keywords

    def test_recognize_web_automation_skill(self):
        """Test recognizing a web automation skill."""
        description = "Automate browser interactions: navigate, click, fill forms"
        keywords, tool_hints = _parse_trigger_from_description(description)

        assert "browser_use" in tool_hints
        assert "browser" in keywords or "automate" in keywords

    def test_recognize_excel_skill(self):
        """Test recognizing an Excel processing skill."""
        description = "Process Excel spreadsheets and xlsx files"
        keywords, tool_hints = _parse_trigger_from_description(description)

        assert "read_file" in tool_hints
        assert "excel" in keywords or "xlsx" in keywords

    def test_recognize_terminal_skill(self):
        """Test recognizing a terminal/command skill."""
        description = "Execute terminal commands and run shell scripts"
        keywords, tool_hints = _parse_trigger_from_description(description)

        assert "execute_shell_command" in tool_hints
        assert "terminal" in keywords or "shell" in keywords or "scripts" in keywords

    def test_recognize_chinese_web_skill(self):
        """Test recognizing a Chinese web-related skill."""
        description = "打开网页并点击按钮，自动浏览网站"
        keywords, tool_hints = _parse_trigger_from_description(description)

        assert "browser_use" in tool_hints
        # Verify Chinese keywords were extracted
        assert len(keywords) > 0

    def test_recognize_document_skill(self):
        """Test recognizing a document processing skill."""
        description = "Process Word documents (docx) and PowerPoint presentations"
        keywords, tool_hints = _parse_trigger_from_description(description)

        assert "read_file" in tool_hints
        assert "docx" in keywords or "word" in keywords
        assert "powerpoint" in keywords or "presentations" in keywords

    def test_recognize_multi_tool_skill(self):
        """Test recognizing a skill with multiple tool hints."""
        description = "Read files, execute commands, and take screenshots"
        keywords, tool_hints = _parse_trigger_from_description(description)

        assert "read_file" in tool_hints
        assert "execute_shell_command" in tool_hints
        assert "desktop_screenshot" in tool_hints


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
