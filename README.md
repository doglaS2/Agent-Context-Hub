# AgentContext Hub

Motor de **State Handover** agnóstico para agentes de IA — 100% local-first.

O AgentContext Hub transfere o estado de trabalho (intenção, arquivos modificados,
logs de conversa) entre agentes e IDEs — Claude Code, Cursor, VS Code, Antigravity —
sem depender de cloud, mantendo todos os dados na sua máquina.

- **Local-first / Privacy-by-Design:** tudo em SQLite local (`~/.agent-ctx/history.db`).
- **Agnóstico de modelo:** fala com os *hosts* (arquivos de estado/logs), nunca com LLMs.
- **Hub-and-Spoke:** um *Common Schema JSON* universal desacopla extractors de injectors.

## Roadmap

| Fase | Escopo | Estado |
|---|---|---|
| 1 | Core + banco SQLite + CLI + Schema Universal (Pydantic) | 🚧 em construção |
| 2 | Extractors (Claude Code, Cursor/VS Code, Antigravity) + file scanner | pendente |
| 3 | Injectors + orquestrador | pendente |
| 4 | Dashboard local (`agent-ctx ui`, FastAPI + Tailwind) | pendente |

## Desenvolvimento

```bash
python -m pip install -e ".[dev]"
pytest -q
agent-ctx --help
```

Arquitetura e roadmap detalhados na especificação técnica (PRD v3.0), documento de autoria confidencial que orienta este repositório.
