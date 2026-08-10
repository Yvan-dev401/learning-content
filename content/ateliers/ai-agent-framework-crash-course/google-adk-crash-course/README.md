# 🚀 Google ADK Crash Course

A comprehensive tutorial series for learning Google's Agent Development Kit (ADK) from basics to advanced concepts. This crash course is designed to take you from zero to hero in building AI agents with Google ADK.

> **📌 Note: This course has been updated for the new Gemini 3 Flash model!**  
> All tutorials in this course use the **Gemini 3 Flash** model (e.g., `gemini-3-flash-preview`). 

## 📚 What is Google ADK?

Google ADK (Agent Development Kit) is a flexible and modular framework for **developing and deploying AI agents**. It's optimized for Gemini and the Google ecosystem but is **model-agnostic** and **deployment-agnostic**, making it compatible with other frameworks.

### Key Features:
- **Flexible Orchestration**: Define workflows using workflow agents or LLM-driven dynamic routing
- **Multi-Agent Architecture**: Build modular applications with multiple specialized agents
- **Rich Tool Ecosystem**: Use pre-built tools, create custom functions, or integrate 3rd-party libraries
- **Deployment Ready**: Containerize and deploy agents anywhere
- **Built-in Evaluation**: Assess agent performance systematically
- **Safety and Security**: Built-in patterns for trustworthy agents

## 🎯 Learning Path

This crash course covers the essential concepts of Google ADK through hands-on tutorials:

### 📚 **Tutorials**

1. **[1_starter_agent](@apppage/ai-agent-framework-crash-course/google-adk-crash-course/1-starter-agent)** - Your first ADK agent
   - Basic agent creation
   - Understanding the ADK workflow
   - Simple text processing

2. **[2_model_agnostic_agent](@apppage/ai-agent-framework-crash-course/google-adk-crash-course/2-model-agnostic-agent)** - Model-agnostic agent development
   - **[2.1 OpenAI Agent](@apppage/ai-agent-framework-crash-course/google-adk-crash-course/2-model-agnostic-agent)** - OpenAI integration
   - **[2.2 Anthropic Claude Agent](@apppage/ai-agent-framework-crash-course/google-adk-crash-course/2-model-agnostic-agent)** - Claude integration

3. **[3_structured_output_agent](@apppage/ai-agent-framework-crash-course/google-adk-crash-course/3-structured-output-agent)** - Type-safe responses
   - **[3.1 Customer Support Ticket Agent](@apppage/ai-agent-framework-crash-course/google-adk-crash-course/3-structured-output-agent-3-1-customer-support-ticket-agent)** - Pydantic schemas
   - **[3.2 Email Agent](@apppage/ai-agent-framework-crash-course/google-adk-crash-course/3-structured-output-agent-3-2-email-agent)** - Structured data validation

4. **[4_tool_using_agent](@apppage/ai-agent-framework-crash-course/google-adk-crash-course/4-tool-using-agent)** - Agent with tools
   - **[4.1 Built-in Tools](@apppage/ai-agent-framework-crash-course/google-adk-crash-course/4-tool-using-agent-4-1-builtin-tools)** - Search, Code Execution
   - **[4.2 Function Tools](@apppage/ai-agent-framework-crash-course/google-adk-crash-course/4-tool-using-agent-4-2-function-tools)** - Custom Python functions
   - **[4.3 Third-party Tools](@apppage/ai-agent-framework-crash-course/google-adk-crash-course/4-tool-using-agent-4-3-thirdparty-tools)** - LangChain, CrewAI
   - **[4.4 MCP Tools](@apppage/ai-agent-framework-crash-course/google-adk-crash-course/4-tool-using-agent-4-4-mcp-tools)** - MCP tools integration

5. **[5_memory_agent](@apppage/ai-agent-framework-crash-course/google-adk-crash-course/5-memory-agent)** - Memory and session management
   - **[5.1 In-Memory Conversation](@apppage/ai-agent-framework-crash-course/google-adk-crash-course/5-memory-agent-5-1-in-memory-conversation-agent)** - Basic session management
   - **[5.2 Persistent Conversation](@apppage/ai-agent-framework-crash-course/google-adk-crash-course/5-memory-agent-5-2-persistent-conversation-agent)** - Database storage with SQLite

6. **[6_callbacks](@apppage/ai-agent-framework-crash-course/google-adk-crash-course/6-callbacks)** - Callback patterns and monitoring
   - **[6.1 Agent Lifecycle Callbacks](@apppage/ai-agent-framework-crash-course/google-adk-crash-course/6-callbacks-6-1-agent-lifecycle-callbacks)** - Monitor agent creation and cleanup
   - **[6.2 LLM Interaction Callbacks](@apppage/ai-agent-framework-crash-course/google-adk-crash-course/6-callbacks-6-2-llm-interaction-callbacks)** - Track model requests and responses
   - **[6.3 Tool Execution Callbacks](@apppage/ai-agent-framework-crash-course/google-adk-crash-course/6-callbacks-6-3-tool-execution-callbacks)** - Monitor tool calls and results

7. **[7_plugins](@apppage/ai-agent-framework-crash-course/google-adk-crash-course/7-plugins)** - Plugin system for cross-cutting concerns
   - Global callback management
   - Request/response modification
   - Error handling and logging
   - Usage analytics and monitoring

8. **[8_simple_multi_agent](@apppage/ai-agent-framework-crash-course/google-adk-crash-course/8-simple-multi-agent)** - Multi-agent orchestration
   - **[8.1 Multi-Agent Researcher](@apppage/ai-agent-framework-crash-course/google-adk-crash-course/8-simple-multi-agent)** - Research pipeline with specialized agents
   - Coordinator agent with sub-agents
   - Sequential workflow: Research → Summarize → Critique
   - Web search integration and comprehensive analysis

9. **9_multi_agent_patterns** - Multi-Agent Patterns
   - **[9.1 Sequential Agent](@apppage/ai-agent-framework-crash-course/google-adk-crash-course/9-multi-agent-patterns-9-1-sequential-agent)** — Deterministic pipeline of sub-agents (e.g., Draft → Critique → Improve)
   - **[9.2 Loop Agent](@apppage/ai-agent-framework-crash-course/google-adk-crash-course/9-multi-agent-patterns-9-2-loop-agent)** — Iterative refinement with an explicit stop condition (max iterations or an exit tool). A tweet crafting loop demonstrates the pattern. 
   - **[9.3 Parallel Agent](@apppage/ai-agent-framework-crash-course/google-adk-crash-course/9-multi-agent-patterns-9-3-parallel-agent)** — Execute multiple sub-agents concurrently and merge results.

## 🛠️ Prerequisites

Before starting this crash course, ensure you have:

- **Python 3.11+** installed
- **Google AI API Key** from [Google AI Studio](https://aistudio.google.com/)
- Basic understanding of Python and APIs

## 📖 How to Use This Course

Each tutorial follows a consistent structure:

- **README.md**: Concept explanation and learning objectives
- **Python file**: Contains the agent implementation and Streamlit app
- **requirements.txt**: Dependencies for the tutorial

### Learning Approach:
1. **Read the README** to understand the concept
2. **Examine the code** to see the implementation
3. **Run the example** to see it in action
4. **Experiment** by modifying the code
5. **Move to the next tutorial** when ready

## 🎯 Tutorial Features

Each tutorial includes:
- ✅ **Clear concept explanation**
- ✅ **Minimal, working code examples**
- ✅ **Real-world use cases**
- ✅ **Step-by-step instructions**
- ✅ **Best practices and tips**

## 📚 Additional Resources

- [Google ADK Documentation](https://google.github.io/adk-docs/)
- [Google AI Studio](https://aistudio.google.com/)
- [Gemini API Reference](https://ai.google.dev/docs)
- [Pydantic Documentation](https://docs.pydantic.dev/)

## 🤝 Contributing

Feel free to contribute improvements, bug fixes, or additional tutorials. Each tutorial should:
- Be self-contained and runnable
- Include clear documentation
- Follow the established structure
- Use minimal, understandable code
