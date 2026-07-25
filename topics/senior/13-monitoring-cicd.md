# Module 13: Monitoring, CI/CD — AWS + Terraform + Datadog

> Stack: AWS (ECS Fargate, Lambda, SQS, S3) + Terraform IaC + Datadog APM/Metrics/Logs

---

## PHẦN 1: Datadog Core

---

### Q1: Cài Datadog Agent trên ECS Fargate — sidecar pattern

**Trả lời:**

Trên ECS Fargate, không có host-level agent. Mỗi task definition cần có Datadog Agent container chạy song song (sidecar pattern).

```json
{
  "family": "ai-service-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "ai-service",
      "image": "123456789.dkr.ecr.us-east-1.amazonaws.com/ai-service:latest",
      "portMappings": [{"containerPort": 8000, "protocol": "tcp"}],
      "environment": [
        {"name": "DD_AGENT_HOST", "value": "127.0.0.1"},
        {"name": "DD_TRACE_AGENT_PORT", "value": "8126"},
        {"name": "DD_ENV", "value": "production"},
        {"name": "DD_SERVICE", "value": "ai-service"},
        {"name": "DD_VERSION", "value": "1.2.0"}
      ],
      "secrets": [
        {
          "name": "OPENAI_API_KEY",
          "valueFrom": "arn:aws:ssm:us-east-1:123456789:parameter/prod/openai-api-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awsfirelens",
        "options": {
          "Name": "datadog",
          "Host": "http-intake.logs.datadoghq.com",
          "TLS": "on",
          "dd_service": "ai-service",
          "dd_source": "python",
          "dd_tags": "env:production",
          "provider": "ecs"
        }
      },
      "dependsOn": [
        {"containerName": "datadog-agent", "condition": "HEALTHY"}
      ]
    },
    {
      "name": "datadog-agent",
      "image": "public.ecr.aws/datadog/agent:latest",
      "portMappings": [
        {"containerPort": 8126, "protocol": "tcp"},
        {"containerPort": 8125, "protocol": "udp"}
      ],
      "environment": [
        {"name": "DD_APM_ENABLED", "value": "true"},
        {"name": "DD_APM_NON_LOCAL_TRAFFIC", "value": "true"},
        {"name": "DD_DOGSTATSD_NON_LOCAL_TRAFFIC", "value": "true"},
        {"name": "ECS_FARGATE", "value": "true"},
        {"name": "DD_LOGS_ENABLED", "value": "true"},
        {"name": "DD_LOGS_CONFIG_CONTAINER_COLLECT_ALL", "value": "true"}
      ],
      "secrets": [
        {
          "name": "DD_API_KEY",
          "valueFrom": "arn:aws:ssm:us-east-1:123456789:parameter/datadog/api-key"
        }
      ],
      "healthCheck": {
        "command": ["CMD-SHELL", "agent health"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 15
      },
      "cpu": 128,
      "memory": 256
    },
    {
      "name": "log-router",
      "image": "public.ecr.aws/aws-observability/aws-for-fluent-bit:stable",
      "firelensConfiguration": {
        "type": "fluentbit"
      },
      "cpu": 64,
      "memory": 128
    }
  ]
}
```

---

### Q2: APM / Distributed Tracing voi ddtrace

**Trả lời:**

**Auto-instrumentation cho FastAPI, Celery, SQLAlchemy, Redis, httpx:**

```python
# main.py - must be FIRST import!
import ddtrace
ddtrace.patch_all()  # Auto-instrument all supported libraries

# OR selective patching:
from ddtrace import patch
patch(
    fastapi=True,
    celery=True,
    sqlalchemy=True,
    redis=True,
    httpx=True,
    requests=True
)

from fastapi import FastAPI
app = FastAPI()
```

**Custom spans cho LLM operations:**
```python
from ddtrace import tracer
from ddtrace.ext import SpanTypes
import anthropic
import time

client = anthropic.AsyncAnthropic()

async def call_llm_with_tracing(
    prompt: str,
    model: str = "claude-haiku-3-5",
    user_id: str = "unknown"
) -> str:
    """LLM call voi custom Datadog trace span."""

    with tracer.trace(
        "llm.completion",
        service="ai-service",
        resource=f"messages.create:{model}",
        span_type=SpanTypes.HTTP
    ) as span:
        # Set custom tags - visible in Datadog trace timeline
        span.set_tag("llm.model", model)
        span.set_tag("llm.provider", "anthropic")
        span.set_tag("user.id", user_id)
        span.set_tag("llm.prompt_length", len(prompt))

        start = time.perf_counter()

        try:
            response = await client.messages.create(
                model=model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )

            elapsed_ms = (time.perf_counter() - start) * 1000
            output_text = response.content[0].text

            span.set_tag("llm.input_tokens", response.usage.input_tokens)
            span.set_tag("llm.output_tokens", response.usage.output_tokens)
            span.set_tag("llm.latency_ms", round(elapsed_ms, 2))

            # Calculate and track cost
            input_cost = response.usage.input_tokens * 0.80 / 1_000_000
            output_cost = response.usage.output_tokens * 4.00 / 1_000_000
            span.set_tag("llm.cost_usd", round(input_cost + output_cost, 6))

            return output_text

        except Exception as e:
            span.set_tag("error", True)
            span.set_tag("error.message", str(e))
            span.set_tag("error.type", type(e).__name__)
            raise

# Nested spans for RAG pipeline tracing
async def rag_query_with_tracing(query: str) -> str:
    """Full RAG pipeline with distributed tracing."""

    with tracer.trace("rag.query", resource=query[:100]) as parent_span:
        parent_span.set_tag("rag.query_length", len(query))

        # Step 1: Embedding
        with tracer.trace("rag.embed") as embed_span:
            embedding = await get_embedding(query)
            embed_span.set_tag("embedding.model", "text-embedding-3-small")

        # Step 2: Vector search
        with tracer.trace("rag.vector_search") as search_span:
            chunks = await vector_search(embedding, top_k=5)
            search_span.set_tag("rag.chunks_retrieved", len(chunks))
            search_span.set_tag("rag.top_score", chunks[0]["score"] if chunks else 0)

        # Step 3: LLM with context
        context = "\n".join([c["text"] for c in chunks])
        augmented_prompt = f"Context:\n{context}\n\nQuestion: {query}"

        with tracer.trace("rag.llm_call") as llm_span:
            response = await call_llm_with_tracing(augmented_prompt)
            llm_span.set_tag("rag.context_tokens", len(context) // 4)

        return response
```

**Trace context propagation across services:**
```python
from ddtrace.propagation.http import HTTPPropagator

# Outbound request: inject trace context into headers
async def call_downstream_service(url: str, data: dict) -> dict:
    headers = {}
    HTTPPropagator.inject(tracer.current_span().context, headers)
    # Injects: x-datadog-trace-id, x-datadog-parent-id, x-datadog-sampling-priority

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data, headers=headers)
        return response.json()

# Inbound: ddtrace FastAPI integration reads x-datadog-trace-id automatically
```

---

### Q3: Metrics voi DogStatsD — AI-specific metrics

**Trả lời:**

**4 Metric Types explained:**
```
COUNT:     Number of occurrences, resets each flush interval
           Use for: requests, errors, cache hits
           Example: statsd.increment("llm.requests")

GAUGE:     Current value at a point in time, does NOT reset
           Use for: queue depth, active connections, index size
           Example: statsd.gauge("sqs.queue.depth", 1523)

HISTOGRAM: Distribution of values -> auto-computes p50/p75/p95/p99/max/avg
           Use for: latency, token counts, response sizes
           Example: statsd.histogram("llm.latency.ms", 342.5)

RATE:      Usually computed by Datadog from COUNT over time (events/sec)
           Can also be: statsd.increment then query as .as_rate()
```

**AI-Specific Custom Metrics Implementation:**
```python
from datadog import statsd
import time
import functools

ENV = "production"

class AIMetrics:
    """Centralized metrics tracking for AI service."""

    @staticmethod
    def track_llm_request(
        model: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        success: bool,
        cache_hit: bool = False,
        user_id: str | None = None
    ):
        tags = [
            f"model:{model}",
            f"env:{ENV}",
            f"cache_hit:{str(cache_hit).lower()}",
        ]
        if user_id:
            tags.append(f"user_id:{user_id}")

        # Request count (COUNT)
        statsd.increment("llm.requests.total", tags=tags)

        if success:
            # Latency distribution (HISTOGRAM -> p50/p95/p99)
            statsd.histogram("llm.latency.ms", latency_ms, tags=tags)

            # Token usage (HISTOGRAM)
            statsd.histogram("llm.tokens.input", input_tokens, tags=tags)
            statsd.histogram("llm.tokens.output", output_tokens, tags=tags)
            statsd.histogram("llm.tokens.total", input_tokens + output_tokens, tags=tags)

            # Cost tracking (HISTOGRAM for per-request, GAUGE for running total)
            cost = _calculate_cost(model, input_tokens, output_tokens)
            statsd.histogram("llm.cost.usd", cost, tags=tags)
        else:
            statsd.increment("llm.errors.total", tags=tags)

    @staticmethod
    def track_rag_query(
        query_latency_ms: float,
        embed_latency_ms: float,
        search_latency_ms: float,
        chunks_retrieved: int,
        cache_hit: bool,
        top_similarity_score: float
    ):
        tags = [f"env:{ENV}", f"cache_hit:{str(cache_hit).lower()}"]

        statsd.histogram("rag.query.latency.ms", query_latency_ms, tags=tags)
        statsd.histogram("rag.embed.latency.ms", embed_latency_ms, tags=tags)
        statsd.histogram("rag.search.latency.ms", search_latency_ms, tags=tags)
        statsd.histogram("rag.chunks_retrieved", chunks_retrieved, tags=tags)
        statsd.histogram("rag.similarity.top_score", top_similarity_score, tags=tags)

        if cache_hit:
            statsd.increment("rag.cache.hits", tags=tags)
        else:
            statsd.increment("rag.cache.misses", tags=tags)

    @staticmethod
    def update_queue_metrics(queue_depth: int, processing_count: int, dlq_depth: int):
        statsd.gauge("jobs.queue.depth", queue_depth, tags=[f"env:{ENV}"])
        statsd.gauge("jobs.processing.count", processing_count, tags=[f"env:{ENV}"])
        statsd.gauge("jobs.dlq.depth", dlq_depth, tags=[f"env:{ENV}"])

    @staticmethod
    def track_vector_index(total_vectors: int, index_name: str):
        statsd.gauge("rag.vector_index.size", total_vectors,
                     tags=[f"index:{index_name}", f"env:{ENV}"])

def _calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    costs = {
        "claude-haiku-3-5": (0.80, 4.00),
        "claude-sonnet-4-5": (3.00, 15.00),
        "gpt-4o-mini": (0.15, 0.60),
        "gpt-4o": (2.50, 10.00),
    }
    input_rate, output_rate = costs.get(model, (1.0, 5.0))
    return (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000

# Decorator for automatic LLM tracking
def track_llm(model: str):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.perf_counter()
            success = True
            input_tokens = 0
            output_tokens = 0
            try:
                result = await func(*args, **kwargs)
                if hasattr(result, 'usage'):
                    input_tokens = result.usage.input_tokens
                    output_tokens = result.usage.output_tokens
                return result
            except Exception:
                success = False
                raise
            finally:
                latency_ms = (time.perf_counter() - start) * 1000
                AIMetrics.track_llm_request(
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    latency_ms=latency_ms,
                    success=success
                )
        return wrapper
    return decorator
```

---

### Q4: Structured Logging tuong quan voi Datadog trace_id

**Trả lời:**

```python
import logging
import json
import sys
from datetime import datetime, timezone
from contextvars import ContextVar
import uuid
from ddtrace import tracer

# Context variables for request-scoped data (thread-safe in async)
request_id_var: ContextVar[str] = ContextVar("request_id", default="")
user_id_var: ContextVar[str] = ContextVar("user_id", default="")

class DatadogJSONFormatter(logging.Formatter):
    """
    JSON log formatter that:
    1. Injects Datadog trace_id/span_id for log-trace correlation
    2. Includes request_id from context var
    3. Formats all extra fields as top-level JSON keys
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": "ai-service",
            "env": "production",
            "version": "1.2.0",
            # Request context
            "request_id": request_id_var.get(""),
            "user_id": user_id_var.get(""),
        }

        # Datadog trace correlation - this links logs to APM traces!
        span = tracer.current_span()
        if span:
            log_entry["dd"] = {
                "trace_id": str(span.trace_id),
                "span_id": str(span.span_id),
                "env": "production",
                "service": "ai-service",
                "version": "1.2.0"
            }

        # Include extra fields from logger.info(..., extra={...})
        standard_keys = {
            "message", "msg", "args", "levelname", "name", "pathname",
            "filename", "lineno", "funcName", "created", "msecs",
            "relativeCreated", "thread", "threadName", "processName",
            "process", "levelno", "exc_info", "exc_text", "stack_info"
        }
        for key, value in record.__dict__.items():
            if key not in standard_keys:
                log_entry[key] = value

        # Exception details
        if record.exc_info:
            log_entry["error"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]),
                "stack_trace": self.formatException(record.exc_info)
            }

        return json.dumps(log_entry, default=str)

def setup_logging(log_level: str = "INFO"):
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(DatadogJSONFormatter())

    logging.root.setLevel(log_level)
    logging.root.handlers = [handler]

    # Reduce noise
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

# FastAPI middleware to inject request context
from starlette.middleware.base import BaseHTTPMiddleware

class LogContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        req_token = request_id_var.set(request_id)

        user_id = getattr(request.state, "user_id", "anonymous")
        user_token = user_id_var.set(user_id)

        try:
            return await call_next(request)
        finally:
            request_id_var.reset(req_token)
            user_id_var.reset(user_token)

# Usage - context vars auto-injected into every log line
logger = logging.getLogger(__name__)

async def process_document(job_id: str, document: str):
    logger.info("Starting document processing", extra={"job_id": job_id})
    try:
        result = await call_llm(document)
        logger.info(
            "Document processing completed",
            extra={
                "job_id": job_id,
                "input_tokens": 500,
                "output_tokens": 200,
                "latency_ms": 1250.5,
                "model": "claude-haiku-3-5"
            }
        )
        return result
    except Exception:
        logger.error("Document processing failed",
                     extra={"job_id": job_id}, exc_info=True)
        raise

# Output JSON (sent to Datadog via Firelens):
# {
#   "timestamp": "2026-05-20T10:30:00Z",
#   "level": "INFO",
#   "message": "Document processing completed",
#   "dd": {"trace_id": "1234567890", "span_id": "9876543210"},
#   "request_id": "req-abc123",
#   "job_id": "job-xyz456",
#   "input_tokens": 500,
#   "latency_ms": 1250.5
# }
```

---

### Q5: Datadog Monitors & Alerts cho AI systems

**Trả lời:**

**Terraform cho Datadog monitors:**
```hcl
# terraform/modules/datadog-monitors/main.tf

resource "datadog_monitor" "llm_error_rate" {
  name    = "[AI Service] High LLM Error Rate"
  type    = "metric alert"
  message = <<-EOT
    LLM error rate exceeded 5% threshold.
    Current value: {{value}}%

    Runbook: https://wiki.company.com/runbooks/llm-errors
    @slack-alerts-channel @pagerduty-on-call
  EOT

  # Rate of errors / rate of total requests * 100
  query = "sum(last_5m):sum:llm.errors.total{env:production}.as_rate() / sum:llm.requests.total{env:production}.as_rate() * 100 > 5"

  monitor_thresholds {
    warning  = 2.0
    critical = 5.0
  }

  notify_no_data    = false
  renotify_interval = 60
  tags = ["service:ai-service", "env:production", "team:ml-platform"]
}

resource "datadog_monitor" "llm_latency_anomaly" {
  name    = "[AI Service] LLM Latency Anomaly Detected"
  type    = "metric alert"
  message = "LLM P95 latency is anomalous. Check for model API issues. @slack-alerts-channel"

  # Anomaly detection: 3 standard deviations from baseline
  query = "avg(last_30m):anomalies(avg:llm.latency.ms.p95{env:production}, 'basic', 3, direction='above') >= 1"

  tags = ["service:ai-service", "env:production"]
}

resource "datadog_monitor" "daily_llm_cost" {
  name    = "[AI Service] Daily LLM Cost Budget Alert"
  type    = "metric alert"
  message = "Daily LLM cost exceeded budget threshold. @slack-finance-alerts @pagerduty-on-call"

  # Sum of cost over 24h rolling window
  query = "sum(last_1d):sum:llm.cost.usd{env:production}.rollup(sum, 86400) > 500"

  monitor_thresholds {
    warning  = 400.0
    critical = 500.0
  }
}

resource "datadog_monitor" "sqs_queue_depth" {
  name    = "[AI Service] SQS Job Queue Depth High"
  type    = "metric alert"
  message = "LLM job queue is backing up. Consider scaling workers. @slack-alerts-channel"

  query = "avg(last_10m):avg:jobs.queue.depth{env:production} > 1000"

  monitor_thresholds {
    warning  = 500
    critical = 1000
  }
}

resource "datadog_monitor" "rag_cache_hit_rate_low" {
  name    = "[AI Service] RAG Cache Hit Rate Low"
  type    = "metric alert"
  message = "Semantic cache hit rate below 30%. Check cache TTL and query patterns. @slack-alerts-channel"

  # cache_hits / (cache_hits + cache_misses) * 100
  query = "avg(last_15m):(sum:rag.cache.hits{env:production}.as_rate() / (sum:rag.cache.hits{env:production}.as_rate() + sum:rag.cache.misses{env:production}.as_rate())) * 100 < 30"

  monitor_thresholds {
    warning  = 40.0
    critical = 30.0
  }
}

# Composite monitor: High error rate AND high latency (degraded service)
resource "datadog_monitor" "service_degradation" {
  name    = "[AI Service] Service Degradation Detected"
  type    = "composite"
  message = "Both error rate and latency are elevated. Possible service outage. @pagerduty-on-call"

  query = "${datadog_monitor.llm_error_rate.id} && ${datadog_monitor.llm_latency_anomaly.id}"
}

# Dashboard
resource "datadog_dashboard" "ai_service" {
  title       = "AI Service - Production Overview"
  description = "Key metrics for LLM service performance, cost, and reliability"
  layout_type = "ordered"

  widget {
    timeseries_definition {
      title = "LLM Request Rate & Error Rate"
      request {
        q            = "sum:llm.requests.total{env:production}.as_rate()"
        display_type = "bars"
        style { palette = "blue" }
      }
      request {
        q            = "sum:llm.errors.total{env:production}.as_rate()"
        display_type = "line"
        style { palette = "red" }
      }
    }
  }

  widget {
    timeseries_definition {
      title = "LLM Latency P50/P95/P99"
      request {
        q            = "avg:llm.latency.ms.p50{env:production} by {model}"
        display_type = "line"
      }
      request {
        q            = "avg:llm.latency.ms.p95{env:production} by {model}"
        display_type = "line"
      }
      request {
        q            = "avg:llm.latency.ms.p99{env:production} by {model}"
        display_type = "line"
      }
    }
  }

  widget {
    query_value_definition {
      title   = "Daily LLM Cost (USD)"
      request {
        q          = "sum:llm.cost.usd{env:production}.rollup(sum, 86400)"
        aggregator = "last"
      }
      precision = 2
    }
  }

  widget {
    timeseries_definition {
      title = "Token Usage by Model"
      request {
        q            = "sum:llm.tokens.total{env:production} by {model}.as_rate()"
        display_type = "area"
      }
    }
  }

  widget {
    timeseries_definition {
      title = "RAG Cache Hit Rate %"
      request {
        q = "sum:rag.cache.hits{env:production}.as_rate() / (sum:rag.cache.hits{env:production}.as_rate() + sum:rag.cache.misses{env:production}.as_rate()) * 100"
        display_type = "line"
      }
    }
  }
}
```

---

### Q6: Datadog LLM Observability (LLMObs)

**Trả lời:**

```python
# ddtrace >= 2.x includes LLM Observability
from ddtrace.llmobs import LLMObs
from ddtrace.llmobs.decorators import llm, workflow, task, agent

# Enable LLM Observability
LLMObs.enable(
    ml_app="ai-document-service",
    api_key=DD_API_KEY,
    site="datadoghq.com",
    agentless_enabled=True  # Or False if using Datadog Agent sidecar
)

# Decorator: automatic input/output/token tracking
@llm(
    model_provider="anthropic",
    model_name="claude-haiku-3-5",
    name="summarize_document"
)
def summarize_document(document: str) -> str:
    response = anthropic_client.messages.create(
        model="claude-haiku-3-5",
        max_tokens=500,
        messages=[{"role": "user", "content": f"Summarize: {document}"}]
    )
    return response.content[0].text

# Workflow decorator for multi-step RAG
@workflow(name="rag_pipeline")
async def rag_pipeline(query: str) -> str:
    embedding = await embed_query(query)
    chunks = await search_vectors(embedding)
    answer = await generate_answer(query, chunks)
    return answer

# Manual annotation for custom metadata
from ddtrace.llmobs import LLMObs

async def call_with_metadata(prompt: str, context: str) -> str:
    with LLMObs.llm(
        model_provider="openai",
        model_name="gpt-4o-mini",
        name="rag_completion"
    ) as span:
        LLMObs.annotate(
            span=span,
            input_data=[
                {"role": "system", "content": f"Context: {context}"},
                {"role": "user", "content": prompt}
            ]
        )

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"Context: {context}"},
                {"role": "user", "content": prompt}
            ]
        )
        output = response.choices[0].message.content

        LLMObs.annotate(
            span=span,
            output_data=[{"role": "assistant", "content": output}],
            metadata={
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
                "temperature": 0.7
            }
        )
        return output

# LLMObs Dashboard provides:
# - Full prompt/response history with search
# - Token usage breakdown by model, user, endpoint
# - Cost attribution (per user, per feature)
# - Latency trends per model
# - Error tracking with prompt context
# - Evaluation scores (if using evals)
```

---

## PHẦN 2: AWS Infrastructure

---

### Q7: ECS Fargate — task definition, service, auto scaling (Terraform)

**Trả lời:**

```hcl
# modules/ecs-service/main.tf

resource "aws_ecs_task_definition" "ai_service" {
  family                   = "ai-service-${var.env}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.cpu     # e.g. "1024" = 1 vCPU
  memory                   = var.memory  # e.g. "2048" = 2 GB

  execution_role_arn = aws_iam_role.ecs_execution.arn  # Pull ECR, read SSM
  task_role_arn      = aws_iam_role.ecs_task.arn        # App permissions

  container_definitions = jsonencode([
    {
      name      = "ai-service"
      image     = "${var.ecr_repo_url}:${var.image_tag}"
      essential = true

      portMappings = [{ containerPort = 8000, protocol = "tcp" }]

      environment = [
        { name = "ENV",        value = var.env },
        { name = "DD_ENV",     value = var.env },
        { name = "DD_SERVICE", value = "ai-service" },
        { name = "DD_AGENT_HOST", value = "127.0.0.1" }
      ]

      secrets = [
        {
          name      = "ANTHROPIC_API_KEY"
          valueFrom = "arn:aws:ssm:us-east-1:${var.account_id}:parameter/${var.env}/anthropic-api-key"
        },
        {
          name      = "DATABASE_URL"
          valueFrom = "arn:aws:ssm:us-east-1:${var.account_id}:parameter/${var.env}/database-url"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/ecs/ai-service-${var.env}"
          "awslogs-region"        = "us-east-1"
          "awslogs-stream-prefix" = "ecs"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    },
    # Datadog sidecar
    {
      name      = "datadog-agent"
      image     = "public.ecr.aws/datadog/agent:latest"
      essential = false
      cpu       = 128
      memory    = 256

      environment = [
        { name = "DD_APM_ENABLED",              value = "true" },
        { name = "DD_APM_NON_LOCAL_TRAFFIC",    value = "true" },
        { name = "DD_DOGSTATSD_NON_LOCAL_TRAFFIC", value = "true" },
        { name = "ECS_FARGATE",                 value = "true" }
      ]

      secrets = [{
        name      = "DD_API_KEY"
        valueFrom = "arn:aws:ssm:us-east-1:${var.account_id}:parameter/datadog/api-key"
      }]
    }
  ])

  tags = { Environment = var.env, Service = "ai-service" }
}

# ECS Service with ALB and rolling deployment
resource "aws_ecs_service" "ai_service" {
  name            = "ai-service-${var.env}"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.ai_service.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  # Rolling update: keep 50% minimum healthy, allow 200% during deploy
  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200
  health_check_grace_period_seconds  = 60

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.ai_service.arn
    container_name   = "ai-service"
    container_port   = 8000
  }

  lifecycle {
    ignore_changes = [desired_count]  # Managed by auto-scaling policies
  }
}

# Auto Scaling - CPU based
resource "aws_appautoscaling_target" "ai_service" {
  max_capacity       = 20
  min_capacity       = 2
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.ai_service.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "cpu_scale" {
  name               = "cpu-tracking-${var.env}"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ai_service.resource_id
  scalable_dimension = aws_appautoscaling_target.ai_service.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ai_service.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value       = 70.0  # Target 70% CPU
    scale_in_cooldown  = 300   # 5 min before scale-in
    scale_out_cooldown = 60    # 1 min before scale-out (fast!)

    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
  }
}

# Auto Scaling - SQS Queue Depth (for LLM workers)
resource "aws_appautoscaling_policy" "queue_depth_scaling" {
  name               = "queue-depth-${var.env}"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.worker.resource_id
  scalable_dimension = aws_appautoscaling_target.worker.scalable_dimension
  service_namespace  = aws_appautoscaling_target.worker.service_namespace

  target_tracking_scaling_policy_configuration {
    # Target: 10 messages per worker instance
    target_value = 10.0

    customized_metric_specification {
      metric_name = "ApproximateNumberOfMessagesVisible"
      namespace   = "AWS/SQS"
      statistic   = "Average"
      dimensions {
        name  = "QueueName"
        value = aws_sqs_queue.llm_jobs.name
      }
    }
  }
}
```

---

### Q8: Lambda — cold start problem va solutions

**Trả lời:**

**Cold start timeline:**
```
Lambda Cold Start:
  Container init:  100-500ms  (AWS provisions Firecracker container)
  Runtime init:    100-500ms  (Python interpreter + stdlib)
  Package init:    200-2000ms (Your imports: anthropic, sqlalchemy, etc.)
  Handler init:    Variable   (Your module-level code: DB connect, etc.)
  Total cold:      500-5000ms

Warm invocation:  ~5ms

Triggers of cold start:
  - First invocation after deployment
  - Idle for ~15 minutes (container recycled)
  - Scale-out to new instance (concurrent spike)
```

```python
# lambda_handler.py

import os
import json
import time
import anthropic
import redis

# === GOOD: Module-level initialization (runs during cold start, reused when warm) ===
print(f"Cold start initializing: {time.time()}")

llm_client = anthropic.Anthropic(
    api_key=os.environ["ANTHROPIC_API_KEY"]
)

redis_client = redis.Redis(
    host=os.environ["REDIS_HOST"],
    port=6379,
    socket_connect_timeout=2,
    socket_timeout=5,
    decode_responses=True
)

print(f"Cold start complete: {time.time()}")

def handler(event: dict, context) -> dict:
    """
    Warm path - this runs fast after cold start.
    llm_client and redis_client are already initialized.
    """
    prompt = event.get("prompt", "")

    # Cache check
    cache_key = f"lambda:cache:{hash(prompt)}"
    cached = redis_client.get(cache_key)
    if cached:
        return {"statusCode": 200, "body": cached, "cached": True}

    # LLM call (client already initialized)
    response = llm_client.messages.create(
        model="claude-haiku-3-5",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )

    result = response.content[0].text
    redis_client.setex(cache_key, 300, result)

    return {
        "statusCode": 200,
        "body": json.dumps({"result": result}),
        "cached": False
    }
```

**Terraform: Provisioned Concurrency + Layers:**
```hcl
resource "aws_lambda_function" "ai_processor" {
  function_name = "ai-processor-${var.env}"
  role          = aws_iam_role.lambda_role.arn
  handler       = "handler.handler"
  runtime       = "python3.12"
  timeout       = 300    # 5 min max
  memory_size   = 1024   # More memory = proportional CPU = faster init

  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  # Lambda Layer: pre-built dependencies (avoid re-packaging)
  layers = [aws_lambda_layer_version.ai_deps.arn]

  environment {
    variables = {
      ENV              = var.env
      ANTHROPIC_API_KEY = data.aws_ssm_parameter.anthropic_key.value
      REDIS_HOST       = var.redis_endpoint
    }
  }

  vpc_config {
    subnet_ids         = var.private_subnet_ids
    security_group_ids = [aws_security_group.lambda.id]
  }
}

resource "aws_lambda_alias" "live" {
  name             = "live"
  function_name    = aws_lambda_function.ai_processor.function_name
  function_version = aws_lambda_function.ai_processor.version
}

# Provisioned Concurrency: keeps N instances initialized and warm
resource "aws_lambda_provisioned_concurrency_config" "ai_processor" {
  function_name                  = aws_lambda_function.ai_processor.function_name
  qualifier                      = aws_lambda_alias.live.name
  provisioned_concurrent_executions = 5

  # Cost example: 5 instances * 1GB * $0.015/GB-hr * 24hr = $1.80/day
  # Worth it for latency-sensitive endpoints
}

# Lambda Layer for heavy dependencies
resource "aws_lambda_layer_version" "ai_deps" {
  filename            = "layers/ai-deps.zip"
  layer_name          = "ai-dependencies"
  compatible_runtimes = ["python3.12"]
  description         = "anthropic, redis, httpx, and other AI dependencies"
}
```

**Lambda limitations and when to use ECS instead:**
```
Lambda Constraints:
  Max timeout:         15 minutes
  Max memory:          10 GB
  Payload size:        6 MB sync, 256 KB async (SQS)
  No streaming:        Response must be complete (except Lambda URLs)
  Cold start:          100ms-3s+ depending on package size

Use Lambda when:
  - Event-driven triggers (S3 upload -> process, API Gateway webhook)
  - Short-lived operations (< 5 minutes)
  - Variable load (pay-per-use economics make sense)
  - Simple document routing/classification

Use ECS Fargate when:
  - Long-running jobs (> 5 minutes)
  - Streaming LLM responses
  - Always-on API servers
  - Need full OS control / custom networking
```

---

### Q9: SQS configuration cho LLM job queues

**Trả lời:**

```hcl
# SQS FIFO Queue for ordered, deduplicated LLM jobs
resource "aws_sqs_queue" "llm_jobs" {
  name = "llm-jobs-${var.env}.fifo"

  fifo_queue                  = true
  content_based_deduplication = false  # We provide explicit deduplication IDs

  # CRITICAL: VisibilityTimeout MUST be > max LLM processing time
  # If LLM job can take up to 5 minutes, set to 6+ minutes
  # If timeout < processing time: job becomes visible again while still processing -> duplicate run!
  visibility_timeout_seconds = 360  # 6 minutes

  message_retention_seconds  = 86400  # 24 hours
  receive_wait_time_seconds  = 20     # Long polling: reduce empty receives & cost

  # Redrive to DLQ after 3 failures
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.llm_jobs_dlq.arn
    maxReceiveCount     = 3
  })

  tags = { Environment = var.env }
}

resource "aws_sqs_queue" "llm_jobs_dlq" {
  name                      = "llm-jobs-dlq-${var.env}.fifo"
  fifo_queue                = true
  message_retention_seconds = 604800  # 7 days for investigation
  tags                      = { Environment = var.env, Purpose = "dead-letter" }
}

# Alert when DLQ has messages
resource "aws_cloudwatch_metric_alarm" "dlq_not_empty" {
  alarm_name          = "llm-dlq-messages-${var.env}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "Messages arrived in DLQ - investigate failed LLM jobs"
  dimensions          = { QueueName = aws_sqs_queue.llm_jobs_dlq.name }
  alarm_actions       = [aws_sns_topic.alerts.arn]
}
```

**SQS Standard vs FIFO comparison:**
```
                Standard Queue       FIFO Queue
Throughput:     Unlimited            300 TPS (3,000 with batching)
Ordering:       Best-effort          Guaranteed per MessageGroupId
Delivery:       At-least-once        Exactly-once
Deduplication:  No                   Yes (via MessageDeduplicationId)
Use case:       High-throughput      LLM jobs, financial txns

For LLM jobs, FIFO recommended:
  - MessageGroupId = user_id (ensures per-user ordering, fair queuing)
  - MessageDeduplicationId = job_id (prevent job running twice if API retry)
  - At-most-once semantics avoid duplicate LLM costs

Visibility Timeout Bug (common interview question):
  Bug: VisibilityTimeout set too short (e.g. 30s, but LLM takes 3 min)
  Effect: Job becomes visible again mid-processing -> second worker picks it up
  Result: Duplicate processing, double cost, data corruption
  Fix: Set VisibilityTimeout = (max_processing_time * 1.5) minimum
```

---

## PHẦN 3: Terraform IaC

---

### Q10: Terraform workflow, state management, module structure

**Trả lời:**

**Standard workflow:**
```bash
# 1. Initialize: download providers, configure backend
terraform init

# 2. Preview changes (ALWAYS run before apply)
terraform plan \
  -var-file=environments/prod/terraform.tfvars \
  -out=tfplan

# 3. Review plan output carefully:
#   + resource: will CREATE
#   ~ resource: will MODIFY
#   - resource: will DESTROY

# 4. Apply (uses saved plan - what you reviewed is what gets applied)
terraform apply tfplan

# 5. Check specific resource
terraform state show aws_ecs_service.ai_service

# 6. Import existing resource into state
terraform import aws_sqs_queue.llm_jobs https://sqs.us-east-1.amazonaws.com/123/llm-jobs

# 7. Destroy specific resource (careful!)
terraform destroy -target=aws_ecs_service.ai_service_dev
```

**Module structure:**
```
terraform/
|-- modules/
|   |-- ecs-service/          # Reusable ECS service module
|   |   |-- main.tf           # ECS Task, Service, Security Groups
|   |   |-- iam.tf            # Execution role, task role
|   |   |-- alb.tf            # Target group, ALB rules
|   |   |-- autoscaling.tf    # AppAutoScaling policies
|   |   |-- variables.tf
|   |   `-- outputs.tf
|   |-- sqs-worker/           # SQS queue + worker ECS service
|   |   |-- main.tf
|   |   |-- variables.tf
|   |   `-- outputs.tf
|   |-- rds/                  # RDS PostgreSQL
|   |   |-- main.tf
|   |   |-- security.tf
|   |   |-- variables.tf
|   |   `-- outputs.tf
|   `-- datadog-monitors/     # Datadog monitors as code
|       |-- main.tf
|       `-- variables.tf
|-- environments/
|   |-- dev/
|   |   |-- main.tf           # Module instantiations for dev
|   |   |-- terraform.tfvars  # Dev-specific values
|   |   `-- backend.tf        # S3 state config for dev
|   `-- prod/
|       |-- main.tf           # Module instantiations for prod
|       |-- terraform.tfvars  # Prod-specific values (larger instance sizes, etc.)
|       `-- backend.tf        # S3 state config for prod
`-- global/
    |-- ecr.tf                # ECR repos (shared, create once)
    |-- iam-base.tf           # Base IAM roles (OIDC, etc.)
    `-- backend.tf
```

**S3 Backend + DynamoDB locking:**
```hcl
# environments/prod/backend.tf
terraform {
  backend "s3" {
    bucket         = "company-terraform-state-prod"
    key            = "ai-service/prod/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
    # DynamoDB lock prevents two engineers from applying simultaneously
    # Lock acquired before plan, released after apply
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    datadog = {
      source  = "DataDog/datadog"
      version = "~> 3.0"
    }
  }
}

# global/state-backend.tf (bootstrapped manually the first time)
resource "aws_s3_bucket" "terraform_state" {
  bucket = "company-terraform-state-prod"
}

resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.terraform_state.id
  versioning_configuration { status = "Enabled" }  # Never lose state history
}

resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.terraform_state.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

resource "aws_dynamodb_table" "terraform_lock" {
  name         = "terraform-state-lock"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"
  attribute {
    name = "LockID"
    type = "S"
  }
}
```

**Environment composition:**
```hcl
# environments/prod/main.tf
locals {
  env = "production"
}

module "ai_service" {
  source = "../../modules/ecs-service"

  env               = local.env
  ecr_repo_url      = data.terraform_remote_state.global.outputs.ecr_repo_url
  image_tag         = var.image_tag
  desired_count     = 3        # 3 tasks for prod
  cpu               = "2048"   # 2 vCPU
  memory            = "4096"   # 4 GB
  private_subnet_ids = module.vpc.private_subnet_ids
  account_id        = data.aws_caller_identity.current.account_id
}

module "llm_workers" {
  source = "../../modules/sqs-worker"

  env          = local.env
  queue_name   = "llm-jobs-production"
  worker_count = 5
  ecr_repo_url = data.terraform_remote_state.global.outputs.ecr_repo_url
  image_tag    = var.image_tag
}

module "datadog_monitors" {
  source = "../../modules/datadog-monitors"

  env         = local.env
  slack_channel = var.slack_alerts_channel
  pagerduty_id  = var.pagerduty_service_id
}

# Reference global state
data "terraform_remote_state" "global" {
  backend = "s3"
  config = {
    bucket = "company-terraform-state-prod"
    key    = "global/terraform.tfstate"
    region = "us-east-1"
  }
}

# environments/prod/terraform.tfvars
# image_tag = "abc1234"  (overridden by CI/CD)
# slack_alerts_channel = "prod-alerts"
```

---

## PHẦN 4: CI/CD voi GitHub Actions + AWS

---

### Q11: Full pipeline — PR to production with approval

**Trả lời:**

**Dockerfile multi-stage:**
```dockerfile
# Stage 1: Builder
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime (minimal image)
FROM python:3.12-slim AS runtime

WORKDIR /app

# Runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application
COPY src/ ./src/
COPY main.py .

# Security: non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**GitHub Actions pipeline:**
```yaml
# .github/workflows/deploy.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  AWS_REGION: us-east-1
  ECR_REPOSITORY: ai-service
  ECS_CLUSTER: main-cluster

permissions:
  contents: read
  id-token: write  # Required for OIDC

jobs:
  # ============ Job 1: Test ============
  test:
    name: Lint & Test
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: testdb
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"

      - name: Install deps
        run: pip install -r requirements.txt -r requirements-dev.txt

      - name: Lint
        run: |
          ruff check .
          mypy src/ --ignore-missing-imports

      - name: Test
        run: pytest tests/ -v --cov=src --cov-report=xml --cov-fail-under=80
        env:
          DATABASE_URL: postgresql://postgres:test@localhost/testdb

  # ============ Job 2: Build & Push ============
  build:
    name: Build Docker Image
    runs-on: ubuntu-latest
    needs: test
    if: github.event_name == 'push'
    outputs:
      image_tag: ${{ steps.tag.outputs.tag }}
      ecr_registry: ${{ steps.login.outputs.registry }}

    steps:
      - uses: actions/checkout@v4

      - name: Generate image tag
        id: tag
        run: echo "tag=$(git rev-parse --short HEAD)" >> $GITHUB_OUTPUT

      - name: Configure AWS credentials (OIDC - no long-lived keys!)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::${{ secrets.AWS_ACCOUNT_ID }}:role/github-actions-ecr
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to ECR
        id: login
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build and push
        env:
          REGISTRY: ${{ steps.login.outputs.registry }}
          TAG: ${{ steps.tag.outputs.tag }}
        run: |
          # Build with layer caching
          docker build \
            --cache-from $REGISTRY/$ECR_REPOSITORY:cache \
            --build-arg BUILDKIT_INLINE_CACHE=1 \
            -t $REGISTRY/$ECR_REPOSITORY:$TAG \
            -t $REGISTRY/$ECR_REPOSITORY:latest \
            .
          docker push $REGISTRY/$ECR_REPOSITORY:$TAG
          docker push $REGISTRY/$ECR_REPOSITORY:latest
          # Update build cache
          docker tag $REGISTRY/$ECR_REPOSITORY:$TAG $REGISTRY/$ECR_REPOSITORY:cache
          docker push $REGISTRY/$ECR_REPOSITORY:cache

  # ============ Job 3: Deploy Dev ============
  deploy-dev:
    name: Deploy to Dev
    runs-on: ubuntu-latest
    needs: build
    if: github.ref == 'refs/heads/develop'
    environment: dev

    steps:
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::${{ secrets.AWS_ACCOUNT_ID }}:role/github-actions-ecs-dev
          aws-region: ${{ env.AWS_REGION }}

      - name: Deploy to ECS dev
        run: |
          aws ecs update-service \
            --cluster ${{ env.ECS_CLUSTER }} \
            --service ai-service-dev \
            --force-new-deployment
          aws ecs wait services-stable \
            --cluster ${{ env.ECS_CLUSTER }} \
            --services ai-service-dev

      - name: Smoke test
        run: curl -f https://api-dev.company.com/health

  # ============ Job 4: Deploy Prod (manual approval) ============
  deploy-prod:
    name: Deploy to Production
    runs-on: ubuntu-latest
    needs: [build, deploy-dev]
    if: github.ref == 'refs/heads/main'
    environment:
      name: production  # Requires approval in GitHub Environment settings
      url: https://api.company.com

    steps:
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::${{ secrets.AWS_ACCOUNT_ID }}:role/github-actions-ecs-prod
          aws-region: ${{ env.AWS_REGION }}

      - name: Update task definition and deploy
        env:
          IMAGE_TAG: ${{ needs.build.outputs.image_tag }}
          REGISTRY: ${{ needs.build.outputs.ecr_registry }}
        run: |
          # Get current task definition
          TASK_DEF=$(aws ecs describe-task-definition \
            --task-definition ai-service-production \
            --query 'taskDefinition' --output json)

          # Update image tag in task definition
          NEW_TASK_DEF=$(echo $TASK_DEF | python3 -c "
          import json, sys
          td = json.load(sys.stdin)
          for cd in td['containerDefinitions']:
              if cd['name'] == 'ai-service':
                  cd['image'] = '$REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG'
          for f in ['taskDefinitionArn','revision','status','requiresAttributes','compatibilities','registeredAt','registeredBy']:
              td.pop(f, None)
          print(json.dumps(td))
          ")

          # Register new revision
          NEW_ARN=$(aws ecs register-task-definition \
            --cli-input-json "$NEW_TASK_DEF" \
            --query 'taskDefinition.taskDefinitionArn' \
            --output text)

          # Deploy
          aws ecs update-service \
            --cluster ${{ env.ECS_CLUSTER }} \
            --service ai-service-production \
            --task-definition $NEW_ARN

          aws ecs wait services-stable \
            --cluster ${{ env.ECS_CLUSTER }} \
            --services ai-service-production

      - name: Notify deployment
        if: always()
        run: |
          STATUS="${{ job.status }}"
          curl -X POST "${{ secrets.SLACK_WEBHOOK }}" \
            -H 'Content-type: application/json' \
            -d "{\"text\": \"Production deploy $STATUS: ai-service ${{ needs.build.outputs.image_tag }}\"}"
```

**OIDC IAM Role (no long-lived keys):**
```hcl
# terraform: OIDC provider for GitHub Actions
resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

resource "aws_iam_role" "github_actions_ecr" {
  name = "github-actions-ecr"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = aws_iam_openid_connect_provider.github.arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
        StringLike = {
          # Restrict to specific repo and branches
          "token.actions.githubusercontent.com:sub" = "repo:company/ai-service:ref:refs/heads/*"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "github_ecr" {
  role = aws_iam_role.github_actions_ecr.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload",
        "ecr:BatchGetImage"
      ]
      Resource = "*"
    }]
  })
}
```

---

### Q12: Rollback strategy

**Trả lời:**

```bash
# Strategy: Redeploy previous ECS task definition revision
# ECS keeps all revisions in history

# Get the previous task definition ARN
PREV_TASK_DEF=$(aws ecs describe-services \
  --cluster main-cluster \
  --services ai-service-production \
  --query 'services[0].deployments[1].taskDefinition' \
  --output text)

echo "Current: $(aws ecs describe-services --cluster main-cluster --services ai-service-production --query 'services[0].taskDefinition' --output text)"
echo "Rolling back to: $PREV_TASK_DEF"

# Rollback = deploy previous task definition
aws ecs update-service \
  --cluster main-cluster \
  --service ai-service-production \
  --task-definition $PREV_TASK_DEF

# Wait for rollback to complete
aws ecs wait services-stable \
  --cluster main-cluster \
  --services ai-service-production

echo "Rollback complete"
```

**GitHub Actions manual rollback:**
```yaml
# .github/workflows/rollback.yml
name: Emergency Rollback

on:
  workflow_dispatch:  # Manual trigger only
    inputs:
      confirm:
        description: "Type ROLLBACK to confirm"
        required: true

jobs:
  rollback:
    runs-on: ubuntu-latest
    if: github.event.inputs.confirm == 'ROLLBACK'
    environment: production

    steps:
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.PROD_DEPLOY_ROLE }}
          aws-region: us-east-1

      - name: Get previous task definition
        id: prev
        run: |
          PREV=$(aws ecs describe-services \
            --cluster main-cluster \
            --services ai-service-production \
            --query 'services[0].deployments[1].taskDefinition' \
            --output text)
          echo "task_def=$PREV" >> $GITHUB_OUTPUT

      - name: Rollback
        run: |
          aws ecs update-service \
            --cluster main-cluster \
            --service ai-service-production \
            --task-definition ${{ steps.prev.outputs.task_def }}
          aws ecs wait services-stable \
            --cluster main-cluster \
            --services ai-service-production
```

---

## PHẦN 5: Logging Strategy

---

### Q13: Log sampling, CloudWatch, Datadog Forwarder

**Trả lời:**

```python
import logging
import random
from functools import wraps

logger = logging.getLogger(__name__)

# Log level strategy
# DEBUG:    Local dev only, never in production
# INFO:     Business events (job started/completed, user actions)
# WARNING:  Unexpected but handled (retry, fallback, degraded mode)
# ERROR:    Failed operations that need investigation (no stack trace in message)
# CRITICAL: Service-level failures (DB down, all workers dead)

# Log sampling: don't log every health check hit
class SampledLogger:
    def __init__(self, base_logger: logging.Logger, sample_rate: float = 0.1):
        self._logger = base_logger
        self._rate = sample_rate

    def info(self, msg: str, **kwargs):
        if random.random() < self._rate:
            self._logger.info(msg, **kwargs)

# 1% sampling for GET /health (1000+ hits/min)
health_logger = SampledLogger(logger, sample_rate=0.01)
# 100% for errors
error_logger = logger  # Never sample errors

# What to log (and what NOT to log)
async def process_job(job_id: str, user_id: str):
    logger.info("Job started", extra={"job_id": job_id, "user_id": user_id})

    try:
        result = await do_work(job_id)
        logger.info(
            "Job completed",
            extra={
                "job_id": job_id,
                "user_id": user_id,
                "duration_ms": 1250,
                "output_tokens": 350,
                # DO NOT LOG: raw prompt content (PII), API keys, passwords
            }
        )
        return result
    except Exception:
        logger.error(
            "Job failed",
            extra={"job_id": job_id, "user_id": user_id},
            exc_info=True  # Include stack trace for errors
        )
        raise
```

**CloudWatch Logs to Datadog:**
```hcl
# CloudWatch Logs -> Datadog Lambda Forwarder
resource "aws_cloudwatch_log_group" "ai_service" {
  name              = "/ecs/ai-service-production"
  retention_in_days = 30  # Keep 30 days in CloudWatch, Datadog stores longer
}

# Subscribe CloudWatch to Datadog Forwarder Lambda
resource "aws_cloudwatch_log_subscription_filter" "datadog" {
  name            = "datadog-forwarder"
  log_group_name  = aws_cloudwatch_log_group.ai_service.name
  filter_pattern  = ""  # Forward all logs
  destination_arn = var.datadog_forwarder_lambda_arn
}

# Datadog Forwarder Lambda (deploy separately via Datadog's CloudFormation template)
# https://docs.datadoghq.com/logs/guide/forwarder/
```

---

## Quick Reference

```
MONITORING + CICD QUICK REFERENCE
=======================================================

Datadog on ECS Fargate:
  - Sidecar agent container in same task definition
  - DD_AGENT_HOST=127.0.0.1 (same awsvpc network)
  - APM: port 8126/tcp, DogStatsD: port 8125/udp
  - App dependsOn: datadog-agent HEALTHY

APM Setup:
  import ddtrace; ddtrace.patch_all()  # MUST be first import
  Custom span: with tracer.trace("llm.completion") as span:
  Tags: span.set_tag("llm.model", model)
  Trace propagation: HTTPPropagator.inject() for outbound

Metric Types:
  COUNT:     llm.requests, llm.errors (resets each flush)
  GAUGE:     queue.depth, index.size (current snapshot)
  HISTOGRAM: latency.ms, token.count -> auto p50/p95/p99/max
  RATE:      derived from COUNT (events/sec)

Key AI Metrics:
  llm.requests.total, llm.errors.total, llm.latency.ms
  llm.tokens.input/output, llm.cost.usd
  rag.cache.hits/misses, jobs.queue.depth, jobs.dlq.depth

Key Monitors:
  1. Error rate > 5% (threshold, 5min window)
  2. Latency anomaly (3 sigma, 30min baseline)
  3. Daily cost > $500 (rollup 24h)
  4. SQS depth > 1000 (scale alert)
  5. DLQ > 0 (immediate alert)

ECS Auto Scaling:
  CPU: TargetTracking 70% -> scale out fast (60s), scale in slow (300s)
  SQS: CustomMetric ApproximateNumberOfMessagesVisible, target 10/worker

Lambda:
  Module-level init: runs once on cold start, reused when warm
  Provisioned Concurrency: keeps N instances warm (cost: ~$1.80/day/GB)
  Max timeout: 15 min (use ECS for longer LLM jobs)

SQS:
  VisibilityTimeout > max_processing_time (360s for 5min LLM jobs)
  WaitTimeSeconds=20 (long polling, reduce empty receives)
  FIFO: MessageGroupId=user_id, MessageDeduplicationId=job_id
  MaxReceiveCount=3 -> DLQ

Terraform:
  State: S3 bucket (versioned, encrypted) + DynamoDB lock
  Module separation: modules/ + environments/ + global/
  Never commit terraform.tfstate to git!

CI/CD:
  OIDC for AWS: no long-lived keys, short-lived tokens
  Docker multi-stage: builder (deps) + runtime (minimal)
  ECR lifecycle: keep 10 tagged, expire untagged after 7 days
  Prod deployment: GitHub Environment with manual approval gate
  Rollback: update-service --task-definition <previous_revision_arn>

Logging:
  Always JSON structured
  Always include: request_id, trace_id, span_id, user_id
  Sampling: 1% for health checks, 10% for frequent ops, 100% for errors
  Never log: raw prompts/responses (PII risk), API keys, passwords
=======================================================
```
