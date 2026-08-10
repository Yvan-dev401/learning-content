# Personal Assistant Agent

A basic personal assistant agent demonstrating the fundamental concepts of agent creation with the OpenAI Agents SDK.

## 🎯 What This Demonstrates

- **Basic Agent Definition**: Creating a simple agent with name and instructions
- **Model Configuration**: Using the default GPT-4o model
- **Simple Instructions**: Basic conversational capabilities

## 🚀 Quick Start

1. **Install OpenAI Agents SDK**:
   ```bash
   pip install openai-agents
   ```

2. **Set up environment**:
   ```bash
   cp ../env.example .env
   # Edit .env and add your OpenAI API key
   ```

2. **Run the agent**:
   ```python
   from agents import Runner
   from agent import root_agent
   
   result = Runner.run_sync(root_agent, "Hello, introduce yourself!")
   print(result.final_output)
   ```

## 💡 Key Concepts

- **Agent Definition**: The `Agent()` class with basic parameters
- **Instructions**: Natural language instructions that guide agent behavior
- **Model Selection**: Default model usage (gpt-4o)

## 🔗 Next Steps

This agent demonstrates the absolute basics. For more advanced features, see:
- [Execution Demo Agent](@apppage/ai-agent-framework-crash-course/openai-sdk-crash-course/1-starter-agent) - Different execution methods
- [Tutorial 2: Structured Output](@apppage/ai-agent-framework-crash-course/openai-sdk-crash-course/2-structured-output-agent) - Pydantic schema outputs
- [Tutorial 3: Tool Using Agent](@apppage/ai-agent-framework-crash-course/openai-sdk-crash-course/3-tool-using-agent) - Adding tools and functions
