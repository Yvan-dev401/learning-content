# Basic Sessions

Demonstrates fundamental session memory management with SQLiteSession for automatic conversation history.

## 🎯 What This Demonstrates

- **In-Memory Sessions**: Temporary session storage for development
- **Persistent Sessions**: File-based session storage for production
- **Multi-Turn Conversations**: Automatic context preservation
- **Session Memory**: Eliminating manual `.to_input_list()` handling

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
   from agent import in_memory_session_example, persistent_session_example
   
   # Test in-memory sessions
   asyncio.run(in_memory_session_example())
   
   # Test persistent sessions
   asyncio.run(persistent_session_example())
   ```

## 💡 Key Concepts

- **SQLiteSession**: Automatic conversation memory management
- **In-Memory vs Persistent**: Choose storage based on use case
- **Session IDs**: Organizing conversations by unique identifiers
- **Automatic Context**: No manual conversation threading required

## 🧪 Available Examples

### In-Memory Sessions
- Temporary conversation storage
- Lost when process ends
- Perfect for development and testing

### Persistent Sessions
- File-based conversation storage
- Survives application restarts
- Essential for production applications

### Multi-Turn Conversations
- Extended conversation flows
- Automatic context preservation
- Natural conversation progression

## 🔗 Next Steps

- [Memory Operations](@apppage/ai-agent-framework-crash-course/openai-sdk-crash-course/7-sessions-7-2-memory-operations) - Advanced memory manipulation
- [Multi Sessions](@apppage/ai-agent-framework-crash-course/openai-sdk-crash-course/7-sessions-7-3-multi-sessions) - Managing multiple conversations
