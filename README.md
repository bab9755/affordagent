# 🛍️ AffordAgent

An AI-powered shopping assistant that identifies items from images and finds the best prices online.

## What it does

Give AffordAgent an image of any item—a pair of sneakers, a piece of furniture, or electronics—and it will:

1. **Analyze the image** to identify the item, brand, colors, materials, and category
2. **Search the web** to find similar products available for purchase
3. **Return a curated list** of matching items with prices and direct links

## Example

```
📷 Input: Image of Adidas Samba sneakers

🔍 Output:
- Adidas Samba OG at Foot Locker — $100
- Adidas Samba OG Night Navy on eBay — $99.95
- Adidas Samba at Stadium Goods — $85
```

## Tech Stack

- **[LangGraph](https://github.com/langchain-ai/langgraph)** — Agent orchestration
- **[OpenRouter](https://openrouter.ai)** — LLM access (GPT-4o-mini)
- **[Tavily](https://tavily.com)** — Web search API
- **[Pydantic](https://docs.pydantic.dev)** — Data validation

## Setup

### Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) package manager

### Installation

```bash
# Clone the repo
git clone https://github.com/yourusername/affordagent.git
cd affordagent

# Install dependencies
uv sync
```

### Configuration

Create a `.env` file with your API keys:

```env
OPENROUTER_API_KEY=sk-or-v1-xxxxx
TAVILY_API_KEY=tvly-xxxxx
```

## Usage

```bash
uv run main.py
```

You'll be prompted to enter an image URL. Press Enter to use a demo image, or paste any image URL.

## How it works

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Image URL  │ ──▶ │  Analyze Image   │ ──▶ │  Web Search     │
└─────────────┘     │  (Vision LLM)    │     │  (Tavily)       │
                    └──────────────────┘     └─────────────────┘
                             │                        │
                             ▼                        ▼
                    ┌──────────────────┐     ┌─────────────────┐
                    │  Item Details:   │     │  Candidates:    │
                    │  - Category      │     │  - URLs         │
                    │  - Brand         │     │  - Prices       │
                    │  - Colors        │     │  - Descriptions │
                    └──────────────────┘     └─────────────────┘
```

## Roadmap

- [ ] Support for more item categories
- [ ] Price comparison across multiple retailers
- [ ] Browser extension for instant price checks
- [ ] Image upload (not just URLs)
- [ ] Price alerts and tracking

## License

MIT

