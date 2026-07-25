# Module 9: AI Agent & Workflow Orchestration — Đáp án phỏng vấn

> **Mục tiêu:** Nắm vững kiến trúc agent, workflow orchestration, LangGraph, và Temporal để tự tin trả lời mọi câu hỏi phỏng vấn Senior AI Engineer.

---

## 1. Agent Fundamentals

### Q: Agent là gì? Khác gì với Chain và simple LLM call?

**Trả lời mẫu:**

| Concept | Mô tả | Khi nào dùng |
|---------|-------|--------------|
| **Simple LLM call** | Gọi LLM một lần, nhận response, xong. Không có state, không có tool. | Summarization, translation, classification đơn giản |
| **Chain (LCEL)** | Chuỗi các bước định sẵn, chạy tuần tự hoặc song song. Flow cố định, biết trước. | RAG pipeline, multi-step prompt với flow không đổi |
| **Agent** | LLM tự quyết định hành động tiếp theo, sử dụng tools, lặp lại đến khi hoàn thành mục tiêu. Flow dynamic. | Task phức tạp cần reasoning, tool use, decision making |

**Key insight:** Agent = LLM + Tools + Loop + Stopping condition. LLM đóng vai "bộ não" quyết định khi nào dùng tool nào.

---

### Q: Giải thích ReAct loop? Thought → Action → Observation hoạt động thế nào?

**Trả lời mẫu:**

ReAct (Reasoning + Acting) là pattern cho phép LLM xen kẽ giữa suy nghĩ (reasoning) và hành động (acting):

```
Thought: Tôi cần tìm thông tin về dân số Việt Nam
Action: search_web(query="Vietnam population 2024")
Observation: Vietnam population is approximately 98 million as of 2024
Thought: Tôi đã có thông tin. Bây giờ cần tính GDP per capita
Action: calculator(expression="430_billion / 98_million")
Observation: 4387.75
Thought: Tôi đã có đủ thông tin để trả lời
Final Answer: GDP per capita của Việt Nam khoảng $4,388 USD
```

```python
from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain import hub

@tool
def search_web(query: str) -> str:
    """Search the web for information."""
    # Implementation here
    return f"Results for: {query}"

@tool
def calculator(expression: str) -> str:
    """Evaluate a mathematical expression."""
    try:
        result = eval(expression.replace("_", ""))
        return str(result)
    except Exception as e:
        return f"Error: {e}"

llm = ChatOpenAI(model="gpt-4o", temperature=0)
tools = [search_web, calculator]

# Pull ReAct prompt from LangChain hub
prompt = hub.pull("hwchase17/react")

agent = create_react_agent(llm, tools, prompt)
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    max_iterations=10,          # stopping condition
    handle_parsing_errors=True  # error recovery
)

result = agent_executor.invoke({
    "input": "GDP per capita của Việt Nam là bao nhiêu USD?"
})
```

**Lưu ý khi phỏng vấn:** ReAct tốt cho single-agent tasks. Với multi-step planning phức tạp hơn, dùng Plan-and-Execute.

---

### Q: Plan-and-Execute pattern là gì?

**Trả lời mẫu:**

Plan-and-Execute tách biệt hai LLM:
1. **Planner LLM**: Nhận goal → tạo ra list các bước (plan)
2. **Executor LLM**: Thực thi từng bước một, có thể re-plan nếu gặp vấn đề

```python
from langchain_experimental.plan_and_execute import (
    PlanAndExecute,
    load_agent_executor,
    load_chat_planner
)
from langchain_openai import ChatOpenAI

# Planner: model mạnh hơn để planning
planner = load_chat_planner(ChatOpenAI(model="gpt-4o", temperature=0))

# Executor: model nhanh hơn để thực thi
executor = load_agent_executor(
    ChatOpenAI(model="gpt-4o-mini", temperature=0),
    tools=tools,
    verbose=True
)

agent = PlanAndExecute(planner=planner, executor=executor, verbose=True)

result = agent.invoke({
    "input": "Research top 3 AI companies, compare their market cap, then write a summary"
})
```

**Trade-off:** Plan-and-Execute tốn nhiều LLM calls hơn ReAct nhưng xử lý tasks phức tạp tốt hơn vì có explicit planning step.

---

### Q: Tool/Function calling loop mechanics hoạt động thế nào?

**Trả lời mẫu:**

OpenAI Function Calling loop:

```python
import openai
import json
from typing import Any

client = openai.OpenAI()

# Define tools schema
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a city",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name"},
                    "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}
                },
                "required": ["city"]
            }
        }
    }
]

def get_weather(city: str, unit: str = "celsius") -> dict:
    """Actual implementation"""
    return {"city": city, "temperature": 28, "unit": unit, "condition": "sunny"}

def run_agent_loop(user_message: str) -> str:
    messages = [{"role": "user", "content": user_message}]

    while True:
        # Step 1: Call LLM
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )

        assistant_message = response.choices[0].message

        # Step 2: Check stopping condition
        if assistant_message.tool_calls is None:
            # No more tool calls → final answer
            return assistant_message.content

        # Step 3: Execute tool calls
        messages.append(assistant_message)  # Add assistant's tool call request

        for tool_call in assistant_message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)

            # Dispatch to actual function
            if function_name == "get_weather":
                result = get_weather(**function_args)
            else:
                result = {"error": f"Unknown function: {function_name}"}

            # Step 4: Add tool result back to messages
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result)
            })
        # Loop continues → LLM processes tool results

answer = run_agent_loop("Thời tiết Hà Nội và TP.HCM hôm nay thế nào?")
```

**Key mechanics:**
- `finish_reason == "tool_calls"` → loop tiếp
- `finish_reason == "stop"` → kết thúc
- Tool results được append vào message history với `role: "tool"`

---

### Q: Agent stopping conditions và error recovery?

**Trả lời mẫu:**

```python
from langchain.agents import AgentExecutor
from langchain_core.exceptions import OutputParserException

# Stopping conditions
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    max_iterations=15,          # Hard limit: tránh infinite loop
    max_execution_time=60.0,    # Time limit: 60 seconds
    early_stopping_method="force",  # "force" = stop + return partial, "generate" = ask LLM to conclude
    handle_parsing_errors=True  # Auto-retry nếu LLM output không parse được
)

# Custom error recovery với retry logic
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def resilient_agent_call(input_text: str) -> str:
    try:
        result = await agent_executor.ainvoke({"input": input_text})
        return result["output"]
    except Exception as e:
        # Log error, possibly fallback to simpler agent
        print(f"Agent failed: {e}, retrying...")
        raise

# Fallback pattern
async def agent_with_fallback(input_text: str) -> str:
    try:
        return await resilient_agent_call(input_text)
    except Exception:
        # Fallback: simple LLM call without tools
        response = await llm.ainvoke(input_text)
        return response.content
```

---

## 2. Memory Systems

### Q: Các loại memory trong AI Agent là gì? So sánh và khi nào dùng loại nào?

**Trả lời mẫu:**

```
Memory Types:
├── In-Context (Short-term)
│   ├── Full conversation history
│   ├── Summary buffer
│   └── Token window (sliding)
└── External (Long-term)
    ├── Vector store (semantic)
    ├── Episodic (event-based)
    └── Entity (knowledge graph)
```

#### In-Context Memory

```python
from langchain.memory import (
    ConversationBufferMemory,
    ConversationSummaryBufferMemory,
    ConversationTokenBufferMemory
)
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini")

# 1. Full history - đơn giản nhất, tốn token nhất
full_memory = ConversationBufferMemory(
    return_messages=True,
    memory_key="chat_history"
)

# 2. Summary buffer - tóm tắt phần cũ, giữ phần gần đây
# Best for: long conversations
summary_memory = ConversationSummaryBufferMemory(
    llm=llm,
    max_token_limit=1000,  # Khi vượt quá → tóm tắt phần cũ
    return_messages=True,
    memory_key="chat_history"
)

# 3. Token window - chỉ giữ N tokens gần nhất
# Best for: cost-sensitive applications
token_memory = ConversationTokenBufferMemory(
    llm=llm,
    max_token_limit=2000,
    return_messages=True
)
```

#### External Memory với Vector Store

```python
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.memory import VectorStoreRetrieverMemory

# Setup vector store memory
embeddings = OpenAIEmbeddings()
vectorstore = Chroma(embedding_function=embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

vector_memory = VectorStoreRetrieverMemory(
    retriever=retriever,
    memory_key="relevant_history"
)

# Save important facts
vector_memory.save_context(
    {"input": "Tên tôi là Khoa, tôi làm AI Engineer tại startup"},
    {"output": "Đã ghi nhận: Khoa, AI Engineer"}
)

# Retrieve relevant context
relevant = vector_memory.load_memory_variables(
    {"prompt": "Công việc của tôi là gì?"}
)
print(relevant["relevant_history"])
# → Trả về: "Human: Tên tôi là Khoa, tôi làm AI Engineer..."
```

#### Memory Write Strategy

```python
# Khi nào lưu vào long-term memory?
class SmartMemoryManager:
    def __init__(self, vectorstore, importance_threshold: float = 0.7):
        self.vectorstore = vectorstore
        self.threshold = importance_threshold
        self.llm = ChatOpenAI(model="gpt-4o-mini")

    async def should_save(self, conversation_turn: str) -> bool:
        """Dùng LLM để đánh giá importance"""
        prompt = f"""Rate the importance of saving this for future reference (0-1):
        "{conversation_turn}"
        
        High importance: user preferences, key facts, decisions made
        Low importance: greetings, clarifying questions, filler
        
        Return ONLY a number between 0 and 1."""

        response = await self.llm.ainvoke(prompt)
        try:
            score = float(response.content.strip())
            return score >= self.threshold
        except ValueError:
            return False

    async def selective_save(self, user_input: str, ai_response: str):
        combined = f"User: {user_input}\nAI: {ai_response}"
        if await self.should_save(combined):
            self.vectorstore.add_texts([combined])
            return True
        return False
```

**Trade-offs khi phỏng vấn:**
- In-context: fast retrieval, limited by context window, costs scale linearly
- Vector store: scalable, slight latency for embedding lookup, semantic search
- Entity memory: best for tracking specific entities (users, products) over time

---

## 3. Multi-Agent Systems

### Q: Các pattern multi-agent phổ biến? Khi nào chọn single vs multi-agent?

**Trả lời mẫu:**

#### Orchestrator-Worker Pattern

```
Orchestrator (GPT-4o)
├── Research Worker (GPT-4o-mini + search tools)
├── Code Worker (GPT-4o + code execution)
└── Writer Worker (GPT-4o-mini + formatting tools)
```

```python
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from typing import TypedDict, List

# Worker agents
research_agent = AgentExecutor(
    agent=create_react_agent(
        ChatOpenAI(model="gpt-4o-mini"),
        tools=[search_web, get_wikipedia],
        prompt=research_prompt
    ),
    tools=[search_web, get_wikipedia]
)

code_agent = AgentExecutor(
    agent=create_react_agent(
        ChatOpenAI(model="gpt-4o"),
        tools=[python_repl, read_file],
        prompt=code_prompt
    ),
    tools=[python_repl, read_file]
)

# Orchestrator decides which worker to use
orchestrator_llm = ChatOpenAI(model="gpt-4o")

async def orchestrate(task: str) -> str:
    # Orchestrator analyzes task
    plan_prompt = f"""Break down this task and assign to appropriate agents:
    Task: {task}
    Available agents: research_agent, code_agent, writer_agent
    
    Return JSON: [{{"agent": "name", "subtask": "description"}}]"""
    
    plan_response = await orchestrator_llm.ainvoke(plan_prompt)
    plan = json.loads(plan_response.content)
    
    results = {}
    for step in plan:
        agent_map = {
            "research_agent": research_agent,
            "code_agent": code_agent,
        }
        agent = agent_map[step["agent"]]
        result = await agent.ainvoke({"input": step["subtask"]})
        results[step["agent"]] = result["output"]
    
    # Synthesize results
    synthesis = await orchestrator_llm.ainvoke(
        f"Synthesize these results into final answer:\n{json.dumps(results)}"
    )
    return synthesis.content
```

#### Supervisor Pattern (LangGraph)

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, List
import operator

class SupervisorState(TypedDict):
    messages: Annotated[List, operator.add]
    next_agent: str
    final_answer: str

def supervisor_node(state: SupervisorState) -> dict:
    """Supervisor decides which agent runs next"""
    last_message = state["messages"][-1]
    
    # Supervisor LLM decides routing
    decision = supervisor_llm.invoke(
        f"Based on: {last_message}\nWhich agent should handle this? "
        f"Options: researcher, coder, writer, FINISH"
    )
    
    return {"next_agent": decision.content.strip()}

# Build supervisor graph
workflow = StateGraph(SupervisorState)
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("researcher", researcher_node)
workflow.add_node("coder", coder_node)

workflow.add_conditional_edges(
    "supervisor",
    lambda x: x["next_agent"],
    {
        "researcher": "researcher",
        "coder": "coder",
        "FINISH": END
    }
)
workflow.add_edge("researcher", "supervisor")
workflow.add_edge("coder", "supervisor")
workflow.set_entry_point("supervisor")
```

#### Single vs Multi-Agent Decision Criteria

| Tiêu chí | Single Agent | Multi-Agent |
|----------|--------------|-------------|
| Task complexity | Đơn giản, rõ ràng | Phức tạp, nhiều domain |
| Parallelism | Không cần | Cần chạy song song |
| Specialization | Generalist OK | Cần specialist tools |
| Latency budget | Tight | Flexible |
| Debugging | Dễ | Khó hơn, cần tracing |
| Cost | Thấp hơn | Cao hơn |

**Rule of thumb:** Bắt đầu với single agent. Chỉ chuyển sang multi-agent khi single agent consistently fails hoặc task rõ ràng cần parallel execution.

---

## 4. LangGraph (Chi tiết)

### Q: LangGraph là gì? StateGraph, nodes, edges hoạt động thế nào?

**Trả lời mẫu:**

LangGraph là framework để build stateful, multi-step LLM applications dưới dạng directed graph. Mỗi node là một function, edges định nghĩa flow.

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from typing import TypedDict, Annotated, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
import operator
import json

# 1. Define State - shared data giữa tất cả nodes
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]  # append-only
    tool_calls_made: int
    final_answer: str | None

# 2. Define LLM and tools
llm = ChatOpenAI(model="gpt-4o", temperature=0)
tools = [search_web, calculator, get_weather]
llm_with_tools = llm.bind_tools(tools)

# 3. Define Nodes (functions that transform state)
def agent_node(state: AgentState) -> dict:
    """LLM decides what to do next"""
    response = llm_with_tools.invoke(state["messages"])
    return {
        "messages": [response],
        "tool_calls_made": state["tool_calls_made"]
    }

def tool_node(state: AgentState) -> dict:
    """Execute tool calls from last message"""
    last_message = state["messages"][-1]
    tool_results = []
    
    for tool_call in last_message.tool_calls:
        tool_func = {t.name: t for t in tools}[tool_call["name"]]
        result = tool_func.invoke(tool_call["args"])
        
        from langchain_core.messages import ToolMessage
        tool_results.append(ToolMessage(
            content=str(result),
            tool_call_id=tool_call["id"]
        ))
    
    return {
        "messages": tool_results,
        "tool_calls_made": state["tool_calls_made"] + len(tool_results)
    }

# 4. Conditional routing function
def should_continue(state: AgentState) -> str:
    """Router: decide which node to go to next"""
    last_message = state["messages"][-1]
    
    # If LLM made tool calls → go to tool executor
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "use_tools"
    
    # If too many tool calls → force stop (guard against loops)
    if state["tool_calls_made"] >= 20:
        return "end"
    
    # Otherwise → final answer
    return "end"

# 5. Build the graph
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("agent", agent_node)
workflow.add_node("tools", tool_node)

# Set entry point
workflow.set_entry_point("agent")

# Add conditional edge FROM agent node
workflow.add_conditional_edges(
    "agent",           # from node
    should_continue,   # routing function
    {                  # mapping: return value → next node
        "use_tools": "tools",
        "end": END
    }
)

# After tools → always go back to agent
workflow.add_edge("tools", "agent")

# 6. Compile with checkpointing
memory = MemorySaver()
app = workflow.compile(checkpointer=memory)

# 7. Run
config = {"configurable": {"thread_id": "session-123"}}
result = app.invoke(
    {
        "messages": [HumanMessage(content="Thời tiết Hà Nội và tính 15% tip cho bill $85")],
        "tool_calls_made": 0,
        "final_answer": None
    },
    config=config
)

print(result["messages"][-1].content)
```

---

### Q: Human-in-the-loop trong LangGraph - interrupt_before và interrupt_after?

**Trả lời mẫu:**

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# Build graph với interrupt points
workflow = StateGraph(AgentState)
workflow.add_node("agent", agent_node)
workflow.add_node("tools", tool_node)
workflow.add_node("human_review", human_review_node)
workflow.set_entry_point("agent")
# ... edges ...

memory = MemorySaver()

# interrupt_before: pause TRƯỚC KHI node chạy
# Use case: user muốn approve tool call trước khi execute
app_with_interrupt = workflow.compile(
    checkpointer=memory,
    interrupt_before=["tools"]  # Pause before executing tools
)

config = {"configurable": {"thread_id": "approval-flow-1"}}

# Run đến interrupt point
result = app_with_interrupt.invoke(
    {"messages": [HumanMessage(content="Xóa tất cả records trong database")]},
    config=config
)
# → Pauses before "tools" node

# Inspect what's about to happen
state = app_with_interrupt.get_state(config)
print("Pending tool calls:", state.values["messages"][-1].tool_calls)
# Output: [{"name": "delete_database", "args": {...}}]

# User approves (resume) hoặc rejects
user_decision = input("Approve? (y/n): ")

if user_decision == "y":
    # Resume from checkpoint
    final_result = app_with_interrupt.invoke(None, config=config)
else:
    # Modify state before resuming
    app_with_interrupt.update_state(
        config,
        {"messages": [HumanMessage(content="Cancelled by user")]}
    )

# interrupt_after: pause SAU KHI node chạy
# Use case: review kết quả tool trước khi LLM xử lý tiếp
app_after_interrupt = workflow.compile(
    checkpointer=memory,
    interrupt_after=["tools"]  # Pause after tool execution
)
```

---

### Q: Checkpointing trong LangGraph - MemorySaver vs SqliteSaver?

**Trả lời mẫu:**

```python
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.postgres import PostgresSaver

# 1. MemorySaver - In-memory, chỉ dùng cho dev/testing
# Mất data khi restart
memory_saver = MemorySaver()

# 2. SqliteSaver - Persistent, single-server
# Tốt cho: development, single-node production
with SqliteSaver.from_conn_string("checkpoints.db") as sqlite_saver:
    app = workflow.compile(checkpointer=sqlite_saver)
    
    config = {"configurable": {"thread_id": "user-123-session-456"}}
    
    # First run
    result1 = app.invoke(
        {"messages": [HumanMessage(content="Xin chào")]},
        config=config
    )
    
    # Second run - tự động load history từ SQLite
    result2 = app.invoke(
        {"messages": [HumanMessage(content="Tôi vừa nói gì?")]},
        config=config
    )
    # Agent nhớ lại "Xin chào" từ lần trước

# 3. PostgresSaver - Distributed, production-grade
# Tốt cho: multi-instance deployments
import psycopg
with PostgresSaver.from_conn_string("postgresql://...") as pg_saver:
    pg_saver.setup()  # Create tables
    app = workflow.compile(checkpointer=pg_saver)

# Thread management
def list_sessions(saver, user_id: str):
    """List all sessions for a user"""
    # Each thread_id = one conversation session
    config_prefix = {"configurable": {"thread_id": f"{user_id}-"}}
    return list(saver.list(config_prefix))
```

**Checkpoint use cases:**
1. **Resume interrupted workflows** - agent crash giữa chừng
2. **Multi-turn conversations** - nhớ context qua nhiều messages
3. **Time-travel debugging** - replay from any checkpoint
4. **Human-in-the-loop** - pause, get approval, resume

---

### Q: So sánh LangGraph vs LangChain LCEL vs Temporal?

**Trả lời mẫu:**

| Feature | LangChain LCEL | LangGraph | Temporal |
|---------|---------------|-----------|----------|
| **Use case** | Linear/branching pipelines | Stateful agent graphs | Long-running business workflows |
| **State management** | Không có built-in | TypedDict state | Workflow history, event sourcing |
| **Durability** | Không | Checkpointing (pluggable) | Built-in, fault-tolerant |
| **Human-in-loop** | Manual | interrupt_before/after | Signal/Query/Update |
| **Error recovery** | try/except | Conditional edges + retry | Retry policies, compensation |
| **Cycle support** | Không | Có (key differentiator) | Có |
| **Scale** | Single process | Single process (+ Redis) | Distributed, enterprise |
| **Observability** | LangSmith | LangSmith | Temporal UI, traces |
| **Long-running** | Không phù hợp | Không phù hợp | Designed for this |
| **Learning curve** | Thấp | Trung bình | Cao |
| **Best for** | RAG, simple agents | Complex agents, chatbots | Order processing, AI pipelines với SLA |

**Khi nào dùng gì:**
- **LCEL**: RAG pipeline, document processing, không cần state phức tạp
- **LangGraph**: Chatbot với memory, multi-agent với approval flow, research agents
- **Temporal**: Workflow chạy nhiều ngày/tuần, cần audit trail, business-critical với retry/compensation

---

## 5. Temporal (Chuyên sâu)

### Q: Workflow vs Activity design principles trong Temporal?

**Trả lời mẫu:**

**Nguyên tắc vàng:** Workflow là coordinator (không có side effects), Activity là executor (có side effects).

```python
from temporalio import workflow, activity
from temporalio.client import Client
from temporalio.worker import Worker
from datetime import timedelta
import asyncio

# === ACTIVITIES: Có side effects ===
# - Gọi API bên ngoài
# - Đọc/ghi database
# - Gửi email
# - File I/O

@activity.defn
async def call_openai_api(prompt: str, model: str) -> str:
    """Activity: gọi OpenAI API - có side effect"""
    import openai
    client = openai.AsyncOpenAI()
    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

@activity.defn
async def save_result_to_db(session_id: str, result: str) -> bool:
    """Activity: ghi vào database"""
    # DB write logic
    return True

@activity.defn
async def send_notification(user_email: str, message: str) -> None:
    """Activity: gửi email"""
    # Email sending logic
    pass

# === WORKFLOW: Pure coordinator ===
# - Chỉ call activities
# - Deterministic (same input → same execution path)
# - KHÔNG được: gọi API trực tiếp, random(), time.time(), global state

@workflow.defn
class AIResearchWorkflow:
    @workflow.run
    async def run(self, topic: str, user_email: str) -> str:
        workflow_id = workflow.info().workflow_id
        
        # Step 1: Research phase
        research_result = await workflow.execute_activity(
            call_openai_api,
            args=[f"Research about: {topic}", "gpt-4o"],
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(
                maximum_attempts=3,
                initial_interval=timedelta(seconds=2),
                backoff_coefficient=2.0
            )
        )
        
        # Step 2: Save result
        await workflow.execute_activity(
            save_result_to_db,
            args=[workflow_id, research_result],
            start_to_close_timeout=timedelta(seconds=30)
        )
        
        # Step 3: Notify user
        await workflow.execute_activity(
            send_notification,
            args=[user_email, f"Research complete: {research_result[:100]}..."],
            start_to_close_timeout=timedelta(seconds=10)
        )
        
        return research_result
```

**Determinism rules cho Workflow code:**
- KHÔNG dùng `datetime.now()` → dùng `workflow.now()`
- KHÔNG dùng `random.random()` → không random trong workflow
- KHÔNG dùng `asyncio.sleep()` → dùng `await workflow.sleep()`
- KHÔNG import libraries với side effects ở top-level

---

### Q: Heartbeat cho long-running activities - tại sao cần và cách implement?

**Trả lời mẫu:**

Heartbeat cho phép Temporal biết activity vẫn đang chạy (không bị stuck). Nếu heartbeat timeout → Temporal có thể reschedule activity trên worker khác.

```python
from temporalio import activity
from temporalio.client import Client
import asyncio

@activity.defn
async def process_large_dataset(dataset_id: str, total_records: int) -> dict:
    """Long-running activity với heartbeat"""
    
    records_processed = 0
    
    # Check if this is a retry - có thể resume từ chỗ dừng
    heartbeat_details = activity.info().heartbeat_details
    if heartbeat_details:
        # Resume từ checkpoint
        records_processed = heartbeat_details[0]
        print(f"Resuming from record {records_processed}")
    
    # Process records in batches
    batch_size = 100
    
    while records_processed < total_records:
        # Check for cancellation
        activity.heartbeat(records_processed)  # Send heartbeat với progress
        
        # Do actual work
        end = min(records_processed + batch_size, total_records)
        await process_batch(dataset_id, records_processed, end)
        
        records_processed = end
        
        # Heartbeat sau mỗi batch
        # Nếu worker crash, Temporal biết đã xử lý đến đây
        activity.heartbeat(records_processed)
        
        # Yield để không block event loop
        await asyncio.sleep(0)
    
    return {"processed": records_processed, "dataset_id": dataset_id}

async def process_batch(dataset_id: str, start: int, end: int):
    """Simulate batch processing"""
    await asyncio.sleep(0.1)  # Actual processing
    print(f"Processed records {start}-{end}")

# Trong workflow, set heartbeat_timeout
@workflow.defn
class DataProcessingWorkflow:
    @workflow.run
    async def run(self, dataset_id: str, total_records: int) -> dict:
        return await workflow.execute_activity(
            process_large_dataset,
            args=[dataset_id, total_records],
            start_to_close_timeout=timedelta(hours=2),
            heartbeat_timeout=timedelta(minutes=5),  # Nếu không heartbeat 5 phút → activity failed
        )
```

**Rule of thumb:** Set `heartbeat_timeout` = 2-3x thời gian xử lý một batch. Heartbeat sau mỗi logical unit of work.

---

### Q: Timeout types trong Temporal - 4 loại khác nhau thế nào?

**Trả lời mẫu:**

```
Timeline của một Activity execution:

Schedule  →  Start  →  [Heartbeats]  →  Close
    |_______________|______________________|
    ScheduleToClose (tổng thời gian tối đa)
                 |________________________|
                 StartToClose (time to run)
    |_____________|
    ScheduleToStart (queue wait time)
                          |....|
                          HeartbeatTimeout (between heartbeats)
```

```python
from temporalio import workflow
from temporalio.common import RetryPolicy
from datetime import timedelta

@workflow.defn
class TimeoutExampleWorkflow:
    @workflow.run
    async def run(self) -> str:
        
        # 1. ScheduleToClose: tổng thời gian từ lúc schedule đến close
        # Bao gồm: queue wait + execution + ALL retries
        # Use case: hard deadline cho toàn bộ activity
        result = await workflow.execute_activity(
            my_activity,
            schedule_to_close_timeout=timedelta(hours=1)  # Activity MUST complete within 1 hour total
        )
        
        # 2. StartToClose: thời gian execute (không tính queue wait)
        # Bao gồm: một lần attempt execution
        # Use case: limit how long a single attempt can run
        result = await workflow.execute_activity(
            my_activity,
            start_to_close_timeout=timedelta(minutes=10)  # One attempt max 10 minutes
        )
        
        # 3. ScheduleToStart: thời gian trong queue (chờ worker available)
        # Use case: detect worker shortage, queue backup
        result = await workflow.execute_activity(
            my_activity,
            schedule_to_start_timeout=timedelta(minutes=2),  # Nếu không có worker sau 2 phút → fail
            start_to_close_timeout=timedelta(minutes=10)
        )
        
        # 4. HeartbeatTimeout: max time between heartbeats
        # Use case: detect stuck long-running activities
        result = await workflow.execute_activity(
            process_large_dataset,
            start_to_close_timeout=timedelta(hours=4),
            heartbeat_timeout=timedelta(minutes=10)  # Phải heartbeat mỗi 10 phút
        )
        
        # Best practice: dùng start_to_close_timeout là minimum requirement
        result = await workflow.execute_activity(
            api_call_activity,
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(
                maximum_attempts=3,
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(seconds=30),
                backoff_coefficient=2.0,
                non_retryable_error_types=["ValueError", "AuthError"]
            )
        )
        
        return result
```

---

### Q: Signal vs Query vs Update trong Temporal - khác nhau thế nào?

**Trả lời mẫu:**

| | Signal | Query | Update |
|--|--------|-------|--------|
| **Hướng** | Client → Workflow | Client ← Workflow | Client ↔ Workflow |
| **Blocking** | Fire-and-forget | Synchronous read | Synchronous (wait for ack) |
| **Side effects** | Có (workflow state thay đổi) | Không (read-only) | Có |
| **Response** | Không | Có (immediate) | Có (after processing) |
| **Use case** | Cancel, pause, inject data | Check status, get progress | Validated mutation |

```python
from temporalio import workflow, activity
from temporalio.client import Client
import asyncio
from typing import Optional

@workflow.defn
class LongRunningAIWorkflow:
    def __init__(self):
        self._paused = False
        self._cancelled = False
        self._progress = 0
        self._results = []
    
    # === SIGNAL: Fire-and-forget, thay đổi state ===
    @workflow.signal
    async def pause(self):
        """Client signals workflow to pause"""
        self._paused = True
        workflow.logger.info("Workflow paused by signal")
    
    @workflow.signal
    async def resume(self):
        """Client signals workflow to resume"""
        self._paused = False
    
    @workflow.signal
    async def cancel_processing(self):
        """Graceful cancellation"""
        self._cancelled = True
    
    # === QUERY: Read-only, synchronous ===
    @workflow.query
    def get_progress(self) -> dict:
        """Client queries current progress - no side effects"""
        return {
            "progress": self._progress,
            "paused": self._paused,
            "results_count": len(self._results)
        }
    
    @workflow.query
    def get_status(self) -> str:
        if self._cancelled:
            return "cancelled"
        if self._paused:
            return "paused"
        return "running"
    
    # === UPDATE (Temporal >= 1.20): Validated mutation với response ===
    @workflow.update
    async def add_item(self, item: str) -> str:
        """Client sends update, workflow validates and responds"""
        if self._cancelled:
            raise ValueError("Cannot add items to cancelled workflow")
        self._results.append(item)
        return f"Item added. Total: {len(self._results)}"
    
    @add_item.validator
    def validate_add_item(self, item: str) -> None:
        """Validation runs before update is applied"""
        if not item or len(item) > 1000:
            raise ValueError(f"Invalid item length: {len(item)}")
    
    @workflow.run
    async def run(self, items: list[str]) -> list[str]:
        for item in items:
            # Check for cancellation
            if self._cancelled:
                break
            
            # Handle pause - wait until resumed
            while self._paused:
                await workflow.wait_condition(lambda: not self._paused, timeout=timedelta(hours=1))
            
            # Process item
            result = await workflow.execute_activity(
                call_openai_api,
                args=[item, "gpt-4o-mini"],
                start_to_close_timeout=timedelta(minutes=2)
            )
            self._results.append(result)
            self._progress += 1
        
        return self._results

# === Client usage ===
async def client_example():
    client = await Client.connect("localhost:7233")
    
    # Start workflow
    handle = await client.start_workflow(
        LongRunningAIWorkflow.run,
        args=[["item1", "item2", "item3"]],
        id="ai-workflow-001",
        task_queue="ai-queue"
    )
    
    # Query progress (non-blocking)
    progress = await handle.query(LongRunningAIWorkflow.get_progress)
    print(f"Progress: {progress}")
    
    # Signal to pause (fire-and-forget)
    await handle.signal(LongRunningAIWorkflow.pause)
    
    # Update: add item and wait for confirmation
    response = await handle.execute_update(
        LongRunningAIWorkflow.add_item,
        "new_item"
    )
    print(f"Update response: {response}")
    
    # Resume
    await handle.signal(LongRunningAIWorkflow.resume)
    
    # Wait for completion
    result = await handle.result()
    return result
```

---

### Q: Saga pattern trong Temporal cho distributed transactions?

**Trả lời mẫu:**

Saga là pattern để manage distributed transactions bằng cách define compensation actions (undo) cho mỗi step.

```python
from temporalio import workflow, activity
from temporalio.common import RetryPolicy
from datetime import timedelta
from dataclasses import dataclass

@dataclass
class BookingResult:
    booking_id: str
    success: bool

# Activities: forward + compensation
@activity.defn
async def reserve_hotel(hotel_id: str, nights: int) -> BookingResult:
    """Forward action"""
    # Call hotel API
    return BookingResult(booking_id=f"hotel-{hotel_id}-{nights}", success=True)

@activity.defn
async def cancel_hotel_reservation(booking_id: str) -> None:
    """Compensation action"""
    # Cancel hotel booking
    print(f"Compensating: cancelled hotel {booking_id}")

@activity.defn
async def book_flight(origin: str, dest: str) -> BookingResult:
    """Forward action"""
    return BookingResult(booking_id=f"flight-{origin}-{dest}", success=True)

@activity.defn
async def cancel_flight(booking_id: str) -> None:
    """Compensation action"""
    print(f"Compensating: cancelled flight {booking_id}")

@activity.defn
async def charge_credit_card(amount: float, booking_ids: list) -> str:
    """Forward action"""
    return f"charge-{amount}"

@activity.defn
async def refund_credit_card(charge_id: str) -> None:
    """Compensation action"""
    print(f"Compensating: refunded {charge_id}")

# Saga Workflow
@workflow.defn
class TravelBookingSaga:
    @workflow.run
    async def run(self, hotel_id: str, origin: str, dest: str, amount: float) -> str:
        compensations = []  # Stack of compensation actions (LIFO)
        
        try:
            # Step 1: Reserve hotel
            hotel_result = await workflow.execute_activity(
                reserve_hotel,
                args=[hotel_id, 3],
                start_to_close_timeout=timedelta(seconds=30)
            )
            compensations.append((cancel_hotel_reservation, [hotel_result.booking_id]))
            
            # Step 2: Book flight
            flight_result = await workflow.execute_activity(
                book_flight,
                args=[origin, dest],
                start_to_close_timeout=timedelta(seconds=30)
            )
            compensations.append((cancel_flight, [flight_result.booking_id]))
            
            # Step 3: Charge credit card
            all_bookings = [hotel_result.booking_id, flight_result.booking_id]
            charge_id = await workflow.execute_activity(
                charge_credit_card,
                args=[amount, all_bookings],
                start_to_close_timeout=timedelta(seconds=30)
            )
            compensations.append((refund_credit_card, [charge_id]))
            
            return f"Booking complete! Hotel: {hotel_result.booking_id}, Flight: {flight_result.booking_id}"
        
        except Exception as e:
            workflow.logger.error(f"Booking failed: {e}. Running compensations...")
            
            # Execute compensations in REVERSE order
            for comp_activity, comp_args in reversed(compensations):
                try:
                    await workflow.execute_activity(
                        comp_activity,
                        args=comp_args,
                        start_to_close_timeout=timedelta(seconds=30),
                        retry_policy=RetryPolicy(maximum_attempts=5)  # Retry compensations harder
                    )
                except Exception as comp_error:
                    # Log but don't fail - compensation failure needs manual intervention
                    workflow.logger.error(f"Compensation failed for {comp_activity}: {comp_error}")
            
            raise  # Re-raise original error
```

---

### Q: Temporal vs Celery - khi nào dùng cái nào?

**Trả lời mẫu:**

| Feature | Celery | Temporal |
|---------|--------|----------|
| **Architecture** | Task queue (Redis/RabbitMQ broker) | Durable execution engine |
| **State** | Stateless tasks, state trong Redis | Full workflow history, event sourcing |
| **Retry** | Basic retry với countdown | Sophisticated retry policies, non-retryable errors |
| **Long-running** | Không phù hợp (worker timeout) | Designed for days/weeks/months |
| **Workflows** | Chains, chords (limited) | Full workflow graphs, signals, queries |
| **Visibility** | Flower (basic) | Temporal UI (detailed timeline) |
| **Testing** | pytest mock | Temporal test framework |
| **Setup** | Đơn giản, Redis là đủ | Phức tạp hơn (Temporal server) |
| **Cost** | Thấp (Redis) | Cao hơn (infrastructure) |
| **Community** | Lớn, mature | Đang phát triển nhanh |

```python
# === Dùng Celery khi: ===
# - Background tasks đơn giản (send email, resize image)
# - Tasks ngắn < 30 phút
# - Team đã biết Celery
# - Budget/infra constraints

# Celery example
from celery import Celery
app = Celery('tasks', broker='redis://localhost:6379')

@app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_welcome_email(self, user_id: int):
    try:
        user = get_user(user_id)
        send_email(user.email, "Welcome!")
    except ConnectionError as exc:
        raise self.retry(exc=exc)

# === Dùng Temporal khi: ===
# - Workflows dài: AI processing pipeline, order fulfillment
# - Cần human-in-the-loop approval
# - Cần audit trail / compliance
# - Complex retry/compensation (Saga)
# - Task chạy nhiều ngày (scheduled workflows)

# Temporal example - xem phần trên
```

**Câu trả lời cho phỏng vấn:** "Tôi dùng Celery cho background tasks đơn giản như send email, process notifications trong startup hiện tại. Temporal tôi dùng cho AI processing pipelines dài phức tạp hơn, nơi cần retry granular và visibility tốt. Trade-off chính là infrastructure overhead của Temporal."

---

## 6. AI Workflow Evaluation

### Q: Metrics để evaluate AI agent performance?

**Trả lời mẫu:**

```python
from dataclasses import dataclass
from typing import List, Optional
import json

@dataclass
class AgentEvalResult:
    task_id: str
    task_completion_rate: float   # 0-1: did agent complete the task?
    tool_call_accuracy: float     # 0-1: were tool calls correct?
    steps_taken: int              # efficiency
    optimal_steps: int            # for efficiency ratio
    latency_ms: float
    total_tokens: int
    hallucination_detected: bool

def evaluate_agent_run(
    task: str,
    expected_output: str,
    actual_output: str,
    tool_calls_made: List[dict],
    expected_tool_calls: List[dict],
    metrics_client  # Langfuse/Phoenix client
) -> AgentEvalResult:
    
    # 1. Task Completion Rate
    # Use LLM-as-judge for semantic comparison
    judge_prompt = f"""
    Task: {task}
    Expected: {expected_output}
    Actual: {actual_output}
    
    Did the agent successfully complete the task? Score 0-1.
    Return JSON: {{"score": 0.8, "reason": "..."}}
    """
    judge_response = judge_llm.invoke(judge_prompt)
    completion_score = json.loads(judge_response.content)["score"]
    
    # 2. Tool Call Accuracy
    correct_tools = 0
    for actual, expected in zip(tool_calls_made, expected_tool_calls):
        if (actual["name"] == expected["name"] and 
            actual["args"] == expected["args"]):
            correct_tools += 1
    
    tool_accuracy = correct_tools / max(len(expected_tool_calls), 1)
    
    # 3. Log to Langfuse
    metrics_client.score(
        name="task_completion",
        value=completion_score,
        comment=f"Tool accuracy: {tool_accuracy}"
    )
    
    return AgentEvalResult(
        task_id="task-001",
        task_completion_rate=completion_score,
        tool_call_accuracy=tool_accuracy,
        steps_taken=len(tool_calls_made),
        optimal_steps=len(expected_tool_calls),
        latency_ms=0,  # filled in
        total_tokens=0,  # filled in
        hallucination_detected=False  # separate check
    )
```

#### Langfuse Tracing Integration

```python
from langfuse import Langfuse
from langfuse.callback import CallbackHandler
from langchain_openai import ChatOpenAI

# Initialize Langfuse
langfuse = Langfuse(
    public_key="pk-...",
    secret_key="sk-...",
    host="https://cloud.langfuse.com"
)

# Automatic tracing với LangChain
langfuse_handler = CallbackHandler()

llm = ChatOpenAI(model="gpt-4o")
agent_executor = AgentExecutor(agent=agent, tools=tools)

# Run với tracing
result = agent_executor.invoke(
    {"input": "user query"},
    config={"callbacks": [langfuse_handler]}
)

# Manual scoring sau evaluation
trace_id = langfuse_handler.get_trace_id()
langfuse.score(
    trace_id=trace_id,
    name="quality",
    value=0.85,
    comment="Tool calls were accurate but one unnecessary step"
)

# Custom trace
with langfuse.trace(name="ai_research_pipeline") as trace:
    with trace.span(name="retrieval") as span:
        docs = retriever.invoke("query")
        span.update(output={"doc_count": len(docs)})
    
    with trace.span(name="generation") as span:
        answer = llm.invoke(f"Based on: {docs}\nAnswer: ...")
        span.update(
            output={"answer": answer.content},
            metadata={"tokens": answer.usage_metadata}
        )
    
    trace.score(name="relevance", value=0.9)
```

**Key metrics dashboard nên track:**
1. **Task success rate** (theo task type, model, tools)
2. **Average steps per successful task** (efficiency)
3. **Tool call precision/recall** (đúng tool, đúng args)
4. **Latency P50/P95/P99** (UX impact)
5. **Token cost per task** (economic viability)
6. **Hallucination rate** (trust)
7. **Human intervention rate** (agent confidence calibration)

---

## Quick Reference: Câu hỏi phỏng vấn hay gặp

**Q: "Bạn sẽ debug một agent đang bị loop vô hạn thế nào?"**
- Bật verbose logging, xem LLM thought/action chain
- Check `max_iterations` có được set không
- Xem tool outputs có meaningful không (empty/error results có thể cause loop)
- Dùng Langfuse/LangSmith để trace từng bước
- Check prompt: system prompt có rõ stopping condition không

**Q: "Làm sao scale agent từ 10 users lên 10,000 users?"**
- Async execution (FastAPI + async agent calls)
- Queue-based: Celery/Temporal để handle spikes
- Cache: semantic cache cho common queries (GPTCache/Redis)
- Streaming responses để giảm perceived latency
- Rate limiting per user
- Horizontal scaling của worker processes

**Q: "Agent của bạn hallucinate. Bạn fix thế nào?"**
- Constrained output: JSON schema, Pydantic validation
- Grounding: RAG để anchor answers vào retrieved docs
- Self-consistency: sample multiple responses, vote
- Tool use: cho agent search/verify thay vì recall từ memory
- Confidence scoring: nếu score thấp → trigger human review

---

*File này được tạo: 2026-05-20 | Dành cho: Senior AI Engineer Interview Prep*
