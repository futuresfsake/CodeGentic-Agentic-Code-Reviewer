"""
==============================================================================
MODULE 2: TOOL SCHEMA DESIGN - FIELD DEFINITIONS & BEST PRACTICES
==============================================================================

OFFICIAL DOCUMENTATION:
  - Tool Use Overview:     https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview.md
  - Structured Outputs:    https://platform.claude.com/docs/en/build-with-claude/structured-outputs.md

==============================================================================
TOOL SCHEMAS = LLM-POWERED APPLICATION
==============================================================================

The moment you define tool schemas and wire them into Claude API calls,
your application becomes an LLM-powered application. The tool schema is
the bridge between Claude's intelligence and your application's capabilities.

Without tools: your app sends text to Claude, gets text back. That's just
a chatbot wrapper.

With tools: Claude can TAKE ACTIONS in your system - query databases, call
APIs, create records, send emails. Now Claude is the brain driving your
application's features.

The spectrum:

  Plain app          -> No LLM. Just code.
  Chatbot wrapper    -> LLM generates text. No tools.
  LLM-powered app    -> LLM + tools. Claude calls YOUR functions.
  Agent              -> LLM + tools + loop. Claude drives the workflow.

Tool schemas are the CONTRACT between the two sides:
  - Claude's side:   reads the schema to know what's available and how to call it
  - Your app's side: reads Claude's tool_use block and dispatches to real functions

That's why schema design matters - it's the core interface of any LLM-powered
application. A bad schema means Claude can't use your app's features correctly,
no matter how good the underlying functions are.

==============================================================================
WHAT IS TOOL USE?
==============================================================================

Tool use is the GENERAL ACT of Claude picking up and using any tool.

It doesn't mean one specific tool. It's the entire mechanism - Claude looks
at the tools available, decides which one (if any) fits the user's request,
and asks your code to run it. Just like a person in a workshop: they look
at the tools on the wall, pick the right one, use it, then maybe pick up
another one.

  "Tool use" = the capability of selecting and calling tools
  "A tool"   = one specific function you've defined (get_weather, etc.)
  "tool_use" = the API block type Claude returns when it picks a tool

So when we say "Claude does tool use", we mean Claude is doing the general
act of selecting from available tools and requesting to call them. It's not
one tool - it's the PATTERN of using tools.

==============================================================================
THE TOOL DEFINITION - FIXED STRUCTURE (API-DEFINED)
==============================================================================

The top-level structure is FIXED by the API. You cannot rename these fields,
reorder them, or invent your own. The API expects this exact shape:

  {
      "name":         REQUIRED  str   - identifier Claude uses to call it
      "description":  REQUIRED  str   - tells Claude WHEN and WHY to use it
      "input_schema": REQUIRED  dict  - JSON Schema defining the parameters

      "strict":                 bool  - optional, guarantees valid input
      "eager_input_streaming":  bool  - optional, streams large inputs
      "cache_control":          dict  - optional, for prompt caching
      "defer_loading":          bool  - optional, for tool search
  }

You CANNOT:
  - Rename "name" to "tool_name" or "function_name"
  - Rename "description" to "info" or "purpose"
  - Rename "input_schema" to "parameters" or "args"
  - Add custom top-level fields like "category" or "version"
  - Use anything other than "type": "object" at the input_schema root

You CAN freely customize:
  - The VALUE of "name" (any snake_case string, unique per request)
  - The VALUE of "description" (whatever helps Claude decide)
  - Everything INSIDE input_schema.properties (your parameters)

==============================================================================
"""

# =============================================================================
# FIELD 1: name
# =============================================================================
# Rules:
#   - Must be a string
#   - Must be unique within a single API request
#   - Convention: snake_case (get_weather, search_database, send_email)
#   - This is what Claude writes in its tool_use block to call the tool
#   - This is what your code matches on to dispatch to the right function

# GOOD names - clear, specific, action-oriented
good_names = [
    "get_weather",          # verb + noun
    "search_documents",     # verb + noun
    "create_calendar_event",# verb + noun
    "calculate_mortgage",   # verb + noun
]

# BAD names - vague, unclear what they do
bad_names = [
    "tool1",          # meaningless
    "do_stuff",       # too vague
    "helper",         # what does it help with?
    "process_data",   # what kind of data? what processing?
]


# =============================================================================
# FIELD 2: description
# =============================================================================
# This is the MOST IMPORTANT field. The description is how Claude decides
# WHETHER to use the tool. A bad description = wrong tool selection.
#
# Think of it as instructions to Claude: "Use this tool when ___"
#
# Rules:
#   - Must be a string
#   - Should explain WHEN to use the tool (the trigger)
#   - Should explain WHAT the tool does (the action)
#   - Should mention any constraints or prerequisites

# GOOD descriptions - tell Claude exactly when to use it
good_descriptions = {
    "get_weather": (
        "Get the current weather conditions for a specific city. "
        "Use this when the user asks about weather, temperature, "
        "or forecasts. Returns temperature, conditions, and humidity."
    ),
    "search_documents": (
        "Search the company knowledge base by keyword. Use this when "
        "the user asks a question that might be answered by internal "
        "documentation. Returns matching document titles and snippets."
    ),
    "calculate_mortgage": (
        "Calculate monthly mortgage payments given a loan amount, "
        "interest rate, and term. Use this for any home loan or "
        "mortgage calculation question."
    ),
}

# BAD descriptions - Claude won't know when to use these
bad_descriptions = {
    "get_weather": "Gets weather.",                # too short, no guidance
    "search_documents": "Searches for things.",    # what things? where?
    "calculate_mortgage": "Does calculations.",     # what kind? when?
}


# =============================================================================
# FIELD 3: input_schema
# =============================================================================
# A JSON Schema object that defines the parameters your tool accepts.
# Claude reads this to know what arguments to pass.
#
# Rules:
#   - Top level MUST be "type": "object"
#   - "properties" defines each parameter
#   - "required" lists mandatory parameters
#   - Each property should have "type" and "description"
#   - If strict: true, must have "additionalProperties": false
#     and ALL properties in "required"
#
# Supported JSON Schema types:
#   "string"  - text
#   "number"  - any number (int or float)
#   "integer" - whole numbers only
#   "boolean" - true/false
#   "array"   - list of items
#   "object"  - nested object
#   "null"    - null value
#
# Useful schema keywords:
#   "enum": [...]           - restrict to specific values
#   "description": "..."    - tells Claude what this parameter is for
#   "default": ...          - suggests a default value
#   "items": {...}          - schema for array elements
#   "minItems" / "maxItems" - array length constraints
#   "minimum" / "maximum"   - number range constraints
#   "pattern": "..."        - regex pattern for strings

# =============================================================================
# COMPLETE EXAMPLES - FROM SIMPLE TO COMPLEX
# =============================================================================

# --- SIMPLE: One required parameter ---
simple_tool = {
    "name": "get_stock_price",
    "description": "Get the current stock price for a ticker symbol. Use when the user asks about stock prices or market data.",
    "input_schema": {
        "type": "object",
        "properties": {
            "ticker": {
                "type": "string",
                "description": "Stock ticker symbol, e.g. 'AAPL', 'GOOGL'"
            }
        },
        "required": ["ticker"]
    }
}

# --- MEDIUM: Required + optional parameters with enum ---
medium_tool = {
    "name": "search_products",
    "description": "Search the product catalog by query. Use when the user wants to find, browse, or compare products.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search terms for the product"
            },
            "category": {
                "type": "string",
                "enum": ["electronics", "clothing", "home", "books"],
                "description": "Filter by product category"
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return (1-50)",
                "minimum": 1,
                "maximum": 50
            },
            "sort_by": {
                "type": "string",
                "enum": ["relevance", "price_low", "price_high", "rating"],
                "description": "Sort order for results. Defaults to relevance."
            }
        },
        "required": ["query"]
    }
}

# --- COMPLEX: Nested objects and arrays ---
complex_tool = {
    "name": "create_calendar_event",
    "description": "Create a new calendar event. Use when the user wants to schedule a meeting, appointment, or reminder.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Event title"
            },
            "start_time": {
                "type": "string",
                "description": "Start time in ISO 8601 format, e.g. '2026-10-28T14:00:00Z'"
            },
            "end_time": {
                "type": "string",
                "description": "End time in ISO 8601 format"
            },
            "attendees": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "email": {"type": "string"},
                        "name": {"type": "string"}
                    },
                    "required": ["email"]
                },
                "description": "List of people to invite"
            },
            "location": {
                "type": "string",
                "description": "Event location or meeting link"
            },
            "recurrence": {
                "type": "object",
                "properties": {
                    "frequency": {
                        "type": "string",
                        "enum": ["daily", "weekly", "monthly"]
                    },
                    "count": {
                        "type": "integer",
                        "description": "Number of occurrences"
                    }
                },
                "description": "Optional recurrence pattern"
            }
        },
        "required": ["title", "start_time", "end_time"]
    }
}

# --- STRICT MODE: All properties required, no extras ---
strict_tool = {
    "name": "classify_intent",
    "description": "Classify the user's intent into a predefined category. Use this to route user requests to the correct handler.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "intent": {
                "type": "string",
                "enum": ["billing", "support", "sales", "general"],
                "description": "The classified intent category"
            },
            "confidence": {
                "type": "number",
                "description": "Confidence score from 0.0 to 1.0"
            },
            "reasoning": {
                "type": "string",
                "description": "Brief explanation of why this intent was chosen"
            }
        },
        "required": ["intent", "confidence", "reasoning"],
        "additionalProperties": False  # REQUIRED when strict: True
    }
}


# =============================================================================
# WHAT CLAUDE SEES vs WHAT YOUR CODE SEES
# =============================================================================
#
# When you send tools to the API, Claude sees the name, description, and
# input_schema. It uses these to decide:
#   1. Should I call a tool at all?        (reads descriptions)
#   2. Which tool should I call?            (matches descriptions to task)
#   3. What arguments should I pass?        (reads input_schema)
#
# Your code then sees the tool_use block:
#   {
#     "type": "tool_use",
#     "id": "toolu_abc123",              <-- unique ID, you need this
#     "name": "get_weather",             <-- which tool Claude picked
#     "input": {"city": "Tokyo"}         <-- arguments Claude chose
#   }
#
# You match on "name" to dispatch to the right function, pass "input"
# as the arguments, and return the result with the "id".


# =============================================================================
# SCHEMA DESIGN BEST PRACTICES
# =============================================================================
#
# 1. DESCRIPTIONS ARE INSTRUCTIONS
#    The description isn't just metadata. It's the primary way Claude
#    decides tool selection. Write it like you're telling someone:
#    "Use this when ___. It does ___. It returns ___."
#
# 2. PARAMETER DESCRIPTIONS MATTER TOO
#    Each property's description helps Claude fill in the right value.
#    "city" with description "City name, e.g. 'San Francisco'" is much
#    better than "city" with no description.
#
# 3. USE ENUMS FOR FIXED CHOICES
#    If a parameter only accepts specific values, use "enum".
#    Claude will always pick from the list instead of guessing.
#
# 4. MARK REQUIRED vs OPTIONAL CLEARLY
#    Only put truly mandatory params in "required". Optional params
#    let Claude skip them when not relevant.
#
# 5. USE STRICT MODE FOR RELIABILITY
#    When you need guaranteed valid input (classification, routing),
#    use strict: true. Trade-off: every property must be required.
#
# 6. KEEP SCHEMAS FOCUSED
#    One tool = one job. Don't make a "do_everything" tool.
#    Multiple focused tools > one giant flexible tool.
#
# 7. PROPERTY DESCRIPTIONS AS FORMATTING HINTS
#    "date in ISO 8601 format", "email address", "2-letter country code"
#    These hints help Claude format values correctly.
#
# =============================================================================

if __name__ == "__main__":
    import json

    print("=" * 60)
    print("Tool Schema Design Reference")
    print("=" * 60)

    all_tools = [simple_tool, medium_tool, complex_tool, strict_tool]
    for tool in all_tools:
        print(f"\n--- {tool['name']} ---")
        print(json.dumps(tool, indent=2))
