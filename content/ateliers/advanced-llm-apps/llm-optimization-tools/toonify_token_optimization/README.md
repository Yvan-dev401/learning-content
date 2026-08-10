# 🎯 Toonify Token Optimization

Reduce LLM API costs by 30-60% using TOON (Token-Oriented Object Notation) format for structured data serialization.

## 📋 Overview

This app demonstrates how to use [Toonify](https://github.com/ScrapeGraphAI/toonify) to dramatically reduce token usage when passing structured data to Large Language Models. TOON format achieves CSV-like compactness while maintaining explicit structure and human readability.

### Key Benefits

- **💰 63.9% average token reduction** compared to JSON
- **🎯 Up to 73.4% savings** for optimal use cases (tabular data)
- **💵 Saves $2,147 per million API requests** at GPT-4 pricing
- **📖 Human-readable** format
- **⚡ Minimal overhead** (<1ms for typical payloads)

## 🚀 Features

- **JSON vs TOON Comparison**: See the size difference in action
- **Token Cost Calculator**: Calculate savings for your use cases
- **LLM Integration Example**: Pass optimized data to GPT/Claude
- **Real-world Examples**: Product catalogs, surveys, analytics data
- **Benchmarking**: Measure compression ratios for your data

## 📦 Installation

1. Install required dependencies:

```bash
pip install -r requirements.txt
```

2. Set up your API key (optional, for LLM integration demo):

```bash
export OPENAI_API_KEY='your-api-key-here'
```

## 💻 Usage

### Basic Example

Run the basic comparison demo:

```bash
python toonify_demo.py
```

### Interactive Demo

Run the interactive Streamlit app:

```bash
streamlit run toonify_app.py
```

## 📊 Format Comparison

### JSON (247 bytes)
```json
{
  "products": [
    {"id": 101, "name": "Laptop Pro", "price": 1299},
    {"id": 102, "name": "Magic Mouse", "price": 79},
    {"id": 103, "name": "USB-C Cable", "price": 19}
  ]
}
```

### TOON (98 bytes, 60% reduction)
```
products[3]{id,name,price}:
  101,Laptop Pro,1299
  102,Magic Mouse,79
  103,USB-C Cable,19
```

## 🎯 Best Use Cases

**Use TOON when:**
- ✅ Passing data to LLM APIs (reduce token costs)
- ✅ Working with uniform tabular data
- ✅ Context window is limited
- ✅ Human readability matters

**Use JSON when:**
- ❌ Maximum compatibility is required
- ❌ Data is highly irregular/nested
- ❌ Working with existing JSON-only tools

## 💡 Example: E-commerce Product Analysis

```python
from toonify import encode
import openai

# Your product data (could be hundreds of products)
products = [
    {"id": 1, "name": "Laptop", "price": 1299, "stock": 45},
    {"id": 2, "name": "Mouse", "price": 79, "stock": 120},
    # ... many more products
]

# Convert to TOON format (saves 60% tokens)
toon_data = encode(products)

# Send to LLM with reduced token cost
response = openai.chat.completions.create(
    model="gpt-4",
    messages=[{
        "role": "user",
        "content": f"Analyze this product data:\n{toon_data}"
    }]
)
```

## 📈 Performance

**Benchmarked across 50 real-world datasets:**
- 63.9% average size reduction vs JSON
- 54.1% average token reduction
- 98% of datasets achieve 40%+ savings
- Minimal overhead (<1ms encoding/decoding)

## 🔗 Resources

- **Toonify GitHub**: https://github.com/ScrapeGraphAI/toonify
- **PyPI**: https://pypi.org/project/toonify/
- **Documentation**: https://docs.scrapegraphai.com/services/toonify
- **Format Spec**: https://github.com/toon-format/toon

## 🤝 Contributing

Contributions are welcome! Feel free to:
- Report bugs
- Suggest new examples
- Add benchmarks
- Improve documentation

## 📄 License

This example is provided as-is for educational purposes.
Toonify library is licensed under MIT License.

## 🙏 Credits

Built with [Toonify](https://github.com/ScrapeGraphAI/toonify) by the ScrapeGraphAI team.
