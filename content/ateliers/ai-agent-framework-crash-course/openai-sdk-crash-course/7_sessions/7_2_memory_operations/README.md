# Memory Operations

Demonstrates advanced session memory operations including item manipulation, conversation corrections, and session management.

## 🎯 What This Demonstrates

- **get_items()**: Retrieving conversation history programmatically
- **add_items()**: Manually adding conversation items
- **pop_item()**: Removing and correcting conversation turns
- **clear_session()**: Resetting conversation history

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

3. **Run the agent**:
   ```python
   import asyncio
   from agent import basic_memory_operations, conversation_corrections
   
   # Test memory operations
   asyncio.run(basic_memory_operations())
   
   # Test conversation corrections
   asyncio.run(conversation_corrections())
   ```

## 💡 Key Concepts

- **Memory Inspection**: Understanding conversation structure
- **Manual Item Management**: Adding custom conversation entries
- **Conversation Corrections**: Undoing and modifying interactions
- **Session Cleanup**: Clearing conversation history

## 🧪 Available Operations

### Basic Memory Operations
- Retrieving conversation items
- Adding custom conversation entries
- Inspecting session contents

### Conversation Corrections
- Using `pop_item()` to undo responses
- Correcting user questions
- Modifying conversation flow

### Session Management
- Clearing conversation history
- Starting fresh conversations
- Managing session lifecycle

### Memory Inspection
- Analyzing conversation structure
- Limiting retrieved items
- Understanding memory patterns

## 🔗 Next Steps

- [Basic Sessions](@apppage/ai-agent-framework-crash-course/openai-sdk-crash-course/7-sessions-7-1-basic-sessions) - Session fundamentals
- [Multi Sessions](@apppage/ai-agent-framework-crash-course/openai-sdk-crash-course/7-sessions-7-3-multi-sessions) - Multiple conversation management
