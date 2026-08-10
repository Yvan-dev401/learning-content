# Advanced Handoffs

Demonstrates advanced handoff configuration including callbacks, structured inputs, and custom tool naming.

## 🎯 What This Demonstrates

- **Custom Handoff Configuration**: Using the `handoff()` function
- **Callback Functions**: Executing code when handoffs are triggered
- **Structured Input Data**: Passing specific data with handoffs
- **Tool Customization**: Custom tool names and descriptions

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
   from agent import main
   
   # Test advanced handoffs
   asyncio.run(main())
   ```

## 💡 Key Concepts

- **handoff() Function**: Custom handoff configuration
- **Callback Execution**: on_handoff functions for tracking
- **Structured Input**: Pydantic models for handoff data
- **Tool Overrides**: Custom tool names and descriptions

## 🧪 Advanced Features

### Escalation with Structured Data
```python
class EscalationData(BaseModel):
    reason: str
    priority: str
    customer_id: str

escalation_handoff = handoff(
    agent=escalation_agent,
    tool_name_override="escalate_to_manager",
    input_type=EscalationData
)
```

### Callback Functions
```python
async def on_escalation_handoff(ctx, input_data):
    print(f"🚨 ESCALATION: {input_data.reason}")
    # Log to monitoring system
    # Send notifications
    # Update tickets
```

### Custom Tool Configuration
- **tool_name_override**: Custom tool names
- **tool_description_override**: Custom tool descriptions
- **input_filter**: Control what context transfers
- **is_enabled**: Dynamic handoff enabling/disabling

## 💻 Advanced Patterns

### Escalation Handoff
- Angry customer scenarios
- High-value refund requests
- Complex technical issues

### Callback Integration
- Logging and monitoring
- Notification systems
- Metric tracking

### Input Filtering
- Context cleaning
- Sensitive data removal
- Conversation sanitization

## 🔗 Next Steps

- [Basic Handoffs](@apppage/ai-agent-framework-crash-course/openai-sdk-crash-course/8-handoffs-delegation-8-1-basic-handoffs) - Handoff fundamentals
- [Tutorial 9: Multi-Agent Orchestration](@apppage/ai-agent-framework-crash-course/openai-sdk-crash-course/9-multi-agent-orchestration) - Complex workflows
