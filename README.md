<div align="center">

# 🎓 **ScholarScope MCP** 🎓

_Academic MCP Server_

</div>


## **About**

The **ScholarScope MCP Server** is a custom [Model Context Protocol](https://modelcontextprotocol.io/) server built with **FastMCP** for powerful academic research tasks.  
It integrates with the [OpenAlex API](https://openalex.org/) to search for **papers, authors, institutions**, retrieve **citations**, and even **fetch full text** using [Jina](https://jina.ai/) where available.

🔍 Perfect for building intelligent research assistants that can:  
- Search academic literature by keywords, author, or institution  
- Explore related works and citations  
- Retrieve full-text papers directly when possible  

[![Python](https://img.shields.io/badge/Python-3.13+-blue?style=for-the-badge&logo=python)](https://www.python.org/)  
[![FastMCP](https://img.shields.io/badge/Backend-FastMCP-orange?style=for-the-badge&logo=modelcontextprotocol)](https://github.com/modelcontextprotocol/fastmcp)  
![License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)  

---

## 🚀 **Installation**

1. **Clone the repository**  
   ```bash
   git clone https://github.com/ErikNguyen20/ScholarScope-MCP.git
   cd ScholarScope-MCP
   ```

2. **Install [uv](https://docs.astral.sh/uv/)** (if you don’t already have it)  
   ```bash
   pip install uv
   ```

3. **Install dependencies**  
   ```bash
   uv sync
   ```

4. **Set up environment variables**  
   Create a `.env` file in the project root:  
   ```env
   OPENALEX_MAILTO=your_email@example.com
   ```

---

## 🧪 **Run with MCP Inspector**

You can use the official MCP Inspector to test your server locally:

```bash
npx @modelcontextprotocol/inspector uv run \
  --directory "/path/to/mcp_server" \
  --with fastmcp \
  fastmcp run src/server.py
```
> [!Note]
> Replace `/path/to/mcp_server` with the path to your local project root.

---

## 💬 **Connect to Claude Desktop**

1. Open your Claude Desktop configuration file (usually `claude_desktop_config.json`).  
2. Add your MCP server configuration:

```json
{
  "mcpServers": {
    "Tool Example": {
      "command": "uv",
      "args": [
        "run",
        "--directory", "/path/to/mcp_server",
        "fastmcp",
        "run",
        "src/server.py"
      ]
    }
  }
}
```

> [!Note]
> Ensure the `/path/to/mcp_server` matches your local directory structure.  
> Restart Claude Desktop after updating the config.

---

## 🧭 **Features**

- 🔍 Search papers by keyword, title, author, or institution  
- 📊 Sort results by relevance, citations, or publication date  
- 📚 Retrieve related works and citations for any paper  
- 📄 Fetch full text from preferred sources when available  
- ⚡ Built with FastMCP for fast startup and modular tools  

---
