import os
import json
import re
import uuid
import logging
from typing import Dict, Any, List, Optional
import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("ai_service")
logging.basicConfig(level=logging.INFO)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
MODEL_STRING = "claude-sonnet-4-6"


def clean_and_extract_json(raw_text: str) -> Dict[str, Any]:
    """
    Extracts JSON from text, handling markdown code blocks (```json ... ```)
    or extraneous conversational text.
    """
    if not raw_text:
        raise ValueError("Empty response string")

    text = raw_text.strip()

    # 1. Check for markdown code fences
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if fence_match:
        text = fence_match.group(1).strip()

    # 2. Try direct JSON parsing
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 3. Try to locate outermost matching curly braces { ... } or brackets [ ... ]
    brace_match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
    if brace_match:
        try:
            return json.loads(brace_match.group(1))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse valid JSON from text: {raw_text[:200]}...")


async def call_claude_json(system_prompt: str, user_prompt: str, retry_count: int = 1) -> Dict[str, Any]:
    """
    Calls Anthropic Claude API via HTTPS requesting STRICT JSON output.
    Implements retry and fallback if parsing fails twice.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key or api_key == "your_anthropic_api_key_here":
        logger.warning("[AI SERVICE] No ANTHROPIC_API_KEY set or placeholder detected. Falling back to local intelligence generator.")
        raise ValueError("NO_API_KEY")

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    current_user_prompt = user_prompt

    for attempt in range(retry_count + 1):
        try:
            payload = {
                "model": MODEL_STRING,
                "max_tokens": 2048,
                "system": system_prompt + "\nIMPORTANT: Your response MUST be STRICT RAW JSON only. Do not include markdown codeblocks, preamble, explanations, or commentary.",
                "messages": [
                    {"role": "user", "content": current_user_prompt}
                ]
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(ANTHROPIC_API_URL, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()

            content_blocks = data.get("content", [])
            raw_text = "".join([block.get("text", "") for block in content_blocks if block.get("type") == "text"])

            parsed = clean_and_extract_json(raw_text)
            return parsed

        except Exception as e:
            logger.warning(f"[AI SERVICE] Attempt {attempt + 1} failed with error: {str(e)}")
            if attempt < retry_count:
                # Retry asking specifically for pure JSON
                current_user_prompt = f"{user_prompt}\n\nATTENTION: Your previous response was not valid JSON or could not be parsed. Please return ONLY a valid, parseable JSON object with no extra text or markdown formatting."
            else:
                logger.error("[AI SERVICE] All retry attempts failed to get valid JSON from Claude API.")
                raise e


# ==============================================================================
# FALLBACK GENERATORS (Robust fallback if no API key or Anthropic API is down)
# ==============================================================================

FALLBACK_QUIZ_BANK = {
    "sql": [
        {
            "id": "q1",
            "text": "Which SQL JOIN returns all rows from the left table, and matching rows from the right table?",
            "options": ["INNER JOIN", "LEFT JOIN", "RIGHT JOIN", "FULL OUTER JOIN"],
            "correct_answer": "LEFT JOIN",
            "topic_tag": "SQL: JOIN",
            "subtopic": "JOIN",
            "explanation": "A LEFT JOIN returns all records from the left table, and the matched records from the right table. If no match is found, NULL values are returned for right table columns."
        },
        {
            "id": "q2",
            "text": "How do you combine results from two tables where there is a match in BOTH tables?",
            "options": ["CROSS JOIN", "OUTER JOIN", "INNER JOIN", "UNION ALL"],
            "correct_answer": "INNER JOIN",
            "topic_tag": "SQL: JOIN",
            "subtopic": "JOIN",
            "explanation": "INNER JOIN creates a new result table by combining column values of two tables based upon the join-predicate matching in both tables."
        },
        {
            "id": "q3",
            "text": "Which clause is used to filter groups of records after an aggregate function has been applied?",
            "options": ["WHERE", "HAVING", "GROUP BY", "ORDER BY"],
            "correct_answer": "HAVING",
            "topic_tag": "SQL: Aggregation",
            "subtopic": "HAVING",
            "explanation": "HAVING was added to SQL because the WHERE keyword cannot be used with aggregate functions (like COUNT, SUM, AVG)."
        },
        {
            "id": "q4",
            "text": "What is the result of performing a FULL OUTER JOIN when rows do not match between tables?",
            "options": ["Matched rows only", "Empty set", "Matched rows plus NULLs for non-matching sides", "An error"],
            "correct_answer": "Matched rows plus NULLs for non-matching sides",
            "topic_tag": "SQL: JOIN",
            "subtopic": "JOIN",
            "explanation": "FULL OUTER JOIN returns all records when there is a match in either left or right table records, filling missing records with NULL."
        }
    ],
    "python": [
        {
            "id": "q1",
            "text": "In Python, which built-in data type is mutable and ordered?",
            "options": ["Tuple", "List", "Set", "Frozenset"],
            "correct_answer": "List",
            "topic_tag": "Python: Data Structures",
            "subtopic": "Data Structures",
            "explanation": "Lists are mutable and maintain insertion order, unlike sets (unordered, unique) or tuples (immutable)."
        },
        {
            "id": "q2",
            "text": "What keyword is used to define an asynchronous generator or coroutine in modern Python?",
            "options": ["def async", "async def", "coroutine", "thread def"],
            "correct_answer": "async def",
            "topic_tag": "Python: AsyncIO",
            "subtopic": "AsyncIO",
            "explanation": "In Python 3.5+, 'async def' is the syntax used to define native coroutines."
        },
        {
            "id": "q3",
            "text": "What does the 'is' operator test for in Python?",
            "options": ["Value equality", "Object identity in memory", "Type matching", "Subset inclusion"],
            "correct_answer": "Object identity in memory",
            "topic_tag": "Python: Fundamentals",
            "subtopic": "Memory & Variables",
            "explanation": "The 'is' operator checks if two variables refer to the exact same object in memory, while '==' compares values."
        },
        {
            "id": "q4",
            "text": "Which structure is best for O(1) average-time key-value lookups?",
            "options": ["List", "Tuple", "Dict", "Linked List"],
            "correct_answer": "Dict",
            "topic_tag": "Python: Data Structures",
            "subtopic": "Dictionaries",
            "explanation": "Python dictionaries are implemented as hash tables, providing average O(1) time complexity for lookups."
        }
    ],
    "fastapi": [
        {
            "id": "q1",
            "text": "FastAPI uses which Python library for data validation and schema declaration?",
            "options": ["Marshmallow", "Pydantic", "Cerberus", "Schema"],
            "correct_answer": "Pydantic",
            "topic_tag": "FastAPI: Validation",
            "subtopic": "Pydantic",
            "explanation": "FastAPI leverages Pydantic for data parsing, type hints validation, and automatic OpenAPI schema generation."
        },
        {
            "id": "q2",
            "text": "What standard ASGI web server is commonly used to run FastAPI applications in production and development?",
            "options": ["Gunicorn", "Uvicorn", "Apache", "Nginx"],
            "correct_answer": "Uvicorn",
            "topic_tag": "FastAPI: Deployment",
            "subtopic": "ASGI",
            "explanation": "Uvicorn is a lightning-fast ASGI server implementation for Python, standard for FastAPI."
        },
        {
            "id": "q3",
            "text": "How do you declare dependency injection in a FastAPI route handler function?",
            "options": ["Depends()", "Inject()", "Provide()", "Dependency()"],
            "correct_answer": "Depends()",
            "topic_tag": "FastAPI: Dependency Injection",
            "subtopic": "Depends",
            "explanation": "FastAPI provides the 'Depends' class to declare sub-dependencies and database sessions seamlessly."
        },
        {
            "id": "q4",
            "text": "Which interactive API documentation is auto-generated by FastAPI out of the box at /docs?",
            "options": ["Postman", "Swagger UI", "GraphQL Playground", "Insomnia"],
            "correct_answer": "Swagger UI",
            "topic_tag": "FastAPI: Docs",
            "subtopic": "OpenAPI",
            "explanation": "FastAPI automatically serves interactive Swagger UI documentation at the /docs route."
        }
    ],
    "html/css": [
        {
            "id": "q1",
            "text": "Which CSS layout module is designed for one-dimensional layouts (row OR column)?",
            "options": ["CSS Grid", "Flexbox", "Table Layout", "Float"],
            "correct_answer": "Flexbox",
            "topic_tag": "HTML/CSS: Layout",
            "subtopic": "Flexbox",
            "explanation": "Flexbox is designed for one-dimensional layouts (either a row or a column), whereas CSS Grid is designed for two-dimensional layouts."
        },
        {
            "id": "q2",
            "text": "Which HTML5 semantic tag should be used to define the primary content of the document?",
            "options": ["<article>", "<section>", "<main>", "<div>"],
            "correct_answer": "<main>",
            "topic_tag": "HTML/CSS: Semantics",
            "subtopic": "Semantic HTML",
            "explanation": "The <main> tag specifies the main content of a document, which must be unique to the document."
        },
        {
            "id": "q3",
            "text": "In CSS specificity, which of the following has the highest priority?",
            "options": ["Element tag selector", "Class selector", "ID selector", "Universal selector"],
            "correct_answer": "ID selector",
            "topic_tag": "HTML/CSS: Specificity",
            "subtopic": "Specificity",
            "explanation": "An ID selector (#id) has a specificity value higher than classes (.class) and elements (div, p)."
        },
        {
            "id": "q4",
            "text": "What does the 'rem' unit in CSS relate to?",
            "options": ["Font size of the immediate parent element", "Font size of the root element (html)", "Viewport width", "Screen DPI"],
            "correct_answer": "Font size of the root element (html)",
            "topic_tag": "HTML/CSS: Typography & Units",
            "subtopic": "Units",
            "explanation": "'rem' stands for 'root em' and is relative to the font-size of the root <html> element."
        }
    ]
}


# ==============================================================================
# AGENT IMPLEMENTATIONS
# ==============================================================================

async def generate_assessment_quiz(topic: str) -> Dict[str, Any]:
    """
    Assessment Agent: Generates 4 MCQ questions for a topic.
    Returns: { "quiz_id": string, "questions": [ { id, text, options, topic_tag } ], "server_data": [...] }
    """
    system_prompt = (
        "You are an expert technical interviewer and assessment designer. "
        "Create an assessment of exactly 4 multiple-choice questions for the requested topic. "
        "Each question must have 4 clear options, one correct answer, a topic tag, subtopic, and an explanation. "
        "Return STRICT JSON with the schema: "
        '{"questions": [{"id": "q1", "text": "...", "options": ["...", "...", "...", "..."], "correct_answer": "...", "topic_tag": "...", "subtopic": "...", "explanation": "..."}]}'
    )
    user_prompt = f"Generate 4 multiple-choice assessment questions for the topic: '{topic}'."

    quiz_id = str(uuid.uuid4())
    questions = []

    try:
        data = await call_claude_json(system_prompt, user_prompt, retry_count=1)
        questions = data.get("questions", [])
        if len(questions) != 4:
            raise ValueError(f"Expected 4 questions, got {len(questions)}")
    except Exception as e:
        logger.info(f"[ASSESSMENT AGENT] Using curated high-yield questions for topic '{topic}' due to: {e}")
        key = topic.strip().lower()
        if key in FALLBACK_QUIZ_BANK:
            questions = FALLBACK_QUIZ_BANK[key]
        else:
            # Generic technical topic fallback
            questions = [
                {
                    "id": f"q{i}",
                    "text": f"Which principle is essential when working with {topic} (Concept {i})?",
                    "options": [
                        f"Standard best-practice modular implementation of {topic}",
                        f"Deprecated legacy workaround for {topic}",
                        "Bypassing runtime validation",
                        "Ignoring exception handling"
                    ],
                    "correct_answer": f"Standard best-practice modular implementation of {topic}",
                    "topic_tag": f"{topic}: Core Concept {i}",
                    "subtopic": f"{topic} Fundamentals",
                    "explanation": f"Understanding core standard practices in {topic} ensures maintainable and performant architecture."
                }
                for i in range(1, 5)
            ]

    # Ensure consistent question format
    client_questions = []
    server_questions = []

    for i, q in enumerate(questions):
        qid = q.get("id") or f"q{i+1}"
        client_questions.append({
            "id": qid,
            "text": q.get("text"),
            "options": q.get("options", []),
            "topic_tag": q.get("topic_tag", topic)
        })
        server_questions.append({
            "id": qid,
            "text": q.get("text"),
            "options": q.get("options", []),
            "correct_answer": q.get("correct_answer"),
            "topic_tag": q.get("topic_tag", topic),
            "subtopic": q.get("subtopic") or q.get("topic_tag") or topic,
            "explanation": q.get("explanation", "Review the official documentation for this concept.")
        })

    return {
        "quiz_id": quiz_id,
        "questions": client_questions,
        "server_data": server_questions
    }


async def generate_roadmap_plan(
    student_skills: Dict[str, int],
    weak_subtopics: List[str],
    reinforce_topics: List[str]
) -> List[Dict[str, Any]]:
    """
    Planner Agent: Creates a personalized 4-week roadmap based on skill scores and weaknesses.
    Conditional rule: If needs_reinforcement is flagged for any topic, Week 1 MUST prioritize it.
    """
    reinforce_str = ", ".join(reinforce_topics) if reinforce_topics else "None"
    weak_str = ", ".join(weak_subtopics) if weak_subtopics else "None"
    skills_summary = ", ".join([f"{k}: {v}%" for k, v in student_skills.items()])

    # Real backend conditional check and terminal logging
    if reinforce_topics:
        print(f"[PLANNER AGENT] Reinforcement required for: {reinforce_topics}. Prioritizing in Week 1.")
        logger.info(f"[PLANNER AGENT] Reinforcement required for: {reinforce_topics}. Prioritizing in Week 1.")
    else:
        print("[PLANNER AGENT] No urgent reinforcement needed. Constructing balanced 4-week progression.")
        logger.info("[PLANNER AGENT] No urgent reinforcement needed. Constructing balanced 4-week progression.")

    system_prompt = (
        "You are an expert curriculum designer and AI Learning Planner. "
        "Create a personalized, high-impact 4-week learning roadmap for a software engineering student.\n"
        "RULES:\n"
        "1. Check if any subtopics scored below 50% or need reinforcement. "
        "IF ANY NEED REINFORCEMENT, WEEK 1 MUST EXPLICITLY FOCUS ON REINFORCING THOSE WEAK SUBTOPICS before introducing new complex topics.\n"
        "2. The roadmap must have exactly 4 weeks (week 1 to week 4).\n"
        "3. Each week must have: 'week' (integer 1-4), 'topics' (array of strings), and 'reason' (string explaining the pedagogical justification).\n"
        "Return STRICT JSON with the schema:\n"
        '{"weeks": [{"week": 1, "topics": ["..."], "reason": "..."}, {"week": 2, "topics": ["..."], "reason": "..."}, {"week": 3, "topics": ["..."], "reason": "..."}, {"week": 4, "topics": ["..."], "reason": "..."}]}'
    )

    context_prompt = (
        f"Student Current Skill Levels: {skills_summary}\n"
        f"Recent Weak Subtopics: {weak_str}\n"
    )

    if reinforce_topics:
        context_prompt += (
            f"CRITICAL: The following subtopics scored below 50% and need reinforcement before moving on: [{reinforce_str}]. "
            "Prioritize these in Week 1."
        )
    else:
        context_prompt += "No subtopics are currently flagged for urgent reinforcement. Focus on progressive advancement."

    try:
        data = await call_claude_json(system_prompt, context_prompt, retry_count=1)
        weeks = data.get("weeks", [])
        if len(weeks) == 4:
            return weeks
    except Exception as e:
        logger.info(f"[PLANNER AGENT] Generating tailored pedagogical plan via engine due to: {e}")

    # Pedagogical plan conforming strictly to requirements
    if reinforce_topics:
        week1_topics = [f"{t} Intensive Reinforcement & Practice" for t in reinforce_topics]
        week1_topics.append("Hands-on Problem Solving & Debugging")
        week1_reason = f"The following subtopics scored below 50% and need reinforcement before moving on: [{reinforce_str}]. Prioritizing these in Week 1."
    else:
        # User passed all diagnostics! Identify their strongest topics
        top_skills = sorted(student_skills.items(), key=lambda x: x[1], reverse=True)
        best_topic = top_skills[0][0] if top_skills else "Full-Stack"
        
        if "SQL" in best_topic:
            week1_topics = [
                "Advanced SQL & Database Optimization (Window Functions, Indexing)",
                "Complex Multi-Table Analytical Queries & Transactions"
            ]
            week1_reason = "You passed core diagnostics with strong proficiency! Advancing directly to high-throughput data modeling, query optimization, and indexing."
        elif "Python" in best_topic:
            week1_topics = [
                "Advanced Python & Concurrency (AsyncIO, Generators, Decorators)",
                "Clean Architecture & Design Patterns"
            ]
            week1_reason = "You demonstrated strong Python proficiency! Advancing directly to asynchronous programming and scalable system architecture."
        elif "FastAPI" in best_topic:
            week1_topics = [
                "FastAPI Production Microservices & Dependency Injection",
                "Advanced Pydantic V2 Schemas & Middleware"
            ]
            week1_reason = "Core backend concepts validated! Diving directly into production-grade API architecture and enterprise dependency patterns."
        else:
            week1_topics = [
                "Full-Stack Architecture & Modern Component Design",
                "End-to-End Type Safety & State Orchestration"
            ]
            week1_reason = "Foundational proficiencies validated across your stack! Advancing to production integration and system optimization."

    return [
        {
            "week": 1,
            "topics": week1_topics,
            "reason": week1_reason
        },
        {
            "week": 2,
            "topics": ["FastAPI REST APIs & Dependency Injection", "Pydantic Schema Data Validation"],
            "reason": "Expanding into high-performance web APIs and modern request handling."
        },
        {
            "week": 3,
            "topics": ["Relational Database Modeling with SQLAlchemy", "Complex Queries, Joins & Performance Tuning"],
            "reason": "Mastering persistent data layers and robust backend transaction management."
        },
        {
            "week": 4,
            "topics": ["Full-Stack Integration & Responsive UI", "Deployment, Error Handling & Production Readiness"],
            "reason": "Unifying frontend interface with backend microservices for a cohesive end-to-end project."
        }
    ]


async def answer_student_doubt(question: str) -> Dict[str, Any]:
    """
    Ask a Doubt Agent: Provides an explanation and detects a suggested topic to practice.
    Returns: { "answer": string, "suggested_topic": string | null }
    """
    system_prompt = (
        "You are an encouraging, expert senior engineer and coding mentor. "
        "Answer the student's question clearly, concisely, and helpfully with code examples where useful. "
        "Also identify if this doubt relates to a specific practice topic (e.g., 'SQL', 'Python', 'FastAPI', 'HTML/CSS', or a subtopic like 'JOIN', 'AsyncIO', 'Flexbox'). "
        "Return STRICT JSON with the schema: "
        '{"answer": "Your detailed explanation...", "suggested_topic": "TopicName or null"}'
    )
    user_prompt = f"Student Question: {question}"

    try:
        data = await call_claude_json(system_prompt, user_prompt, retry_count=1)
        answer = data.get("answer", "")
        suggested_topic = data.get("suggested_topic")
        if answer:
            return {
                "answer": answer,
                "suggested_topic": suggested_topic
            }
    except Exception as e:
        logger.info(f"[DOUBT AGENT] Using local contextual knowledge base for question due to: {e}")

    # Fallback explanation generator
    q_lower = question.lower()
    suggested = None

    if "join" in q_lower or "sql" in q_lower or "table" in q_lower or "query" in q_lower:
        suggested = "SQL"
        answer = (
            "### Understanding SQL JOINs\n\n"
            "SQL JOINs combine columns from one or more tables based on a related column between them:\n\n"
            "1. **INNER JOIN**: Returns only rows that match in *both* tables.\n"
            "   ```sql\n"
            "   SELECT users.name, orders.id \n"
            "   FROM users \n"
            "   INNER JOIN orders ON users.id = orders.user_id;\n"
            "   ```\n"
            "2. **LEFT JOIN**: Returns *all* rows from the left table, plus matched rows from the right table. If no match exists, NULL values appear.\n"
            "3. **RIGHT JOIN**: Returns *all* rows from the right table, plus matches from the left.\n"
            "4. **FULL OUTER JOIN**: Returns all records when there is a match in either table."
        )
    elif "async" in q_lower or "await" in q_lower or "coroutine" in q_lower or "python" in q_lower:
        suggested = "Python"
        answer = (
            "### Python Asynchronous Programming (`async` / `await`)\n\n"
            "In Python, asynchronous programming allows non-blocking I/O operations:\n\n"
            "- `async def`: Defines a coroutine function.\n"
            "- `await`: Pauses execution of the coroutine until the awaited awaitable completes, allowing other tasks to run on the event loop.\n\n"
            "```python\n"
            "import asyncio\n\n"
            "async def fetch_data():\n"
            "    await asyncio.sleep(1) # Simulates network request\n"
            "    return {'status': 200}\n"
            "```"
        )
    elif "fastapi" in q_lower or "route" in q_lower or "endpoint" in q_lower:
        suggested = "FastAPI"
        answer = (
            "### FastAPI Essentials\n\n"
            "FastAPI is a modern web framework for Python built on Starlette and Pydantic.\n\n"
            "- Automatic data validation via type hints and Pydantic models.\n"
            "- Native async request handlers (`async def`).\n"
            "- Auto-generated OpenAPI / Swagger UI at `/docs`."
        )
    elif "flexbox" in q_lower or "css" in q_lower or "html" in q_lower:
        suggested = "HTML/CSS"
        answer = (
            "### CSS Flexbox Overview\n\n"
            "Flexbox is a one-dimensional layout model for aligning and distributing space among items in a container.\n\n"
            "- `display: flex;` activates flex context.\n"
            "- `justify-content`: aligns items along the main axis (e.g. `center`, `space-between`).\n"
            "- `align-items`: aligns items along the cross axis (e.g. `center`, `stretch`)."
        )
    else:
        suggested = "Python"
        answer = (
            f"Here is an explanation regarding your question: '{question}'.\n\n"
            "In software engineering, breaking down the problem into modular components, checking inputs with rigorous validation, "
            "and writing automated test cases provides both clarity and long-term maintainability."
        )

    return {
        "answer": answer,
        "suggested_topic": suggested
    }
