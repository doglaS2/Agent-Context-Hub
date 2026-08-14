# AgentContext Hub

Motor de **State Handover** agnóstico para agentes de IA — 100% local-first.

O AgentContext Hub transfere o estado de trabalho (intenção, arquivos modificados,
logs de conversa) entre agentes e IDEs — Claude Code, Cursor, VS Code, Antigravity —
sem depender de cloud, mantendo todos os dados na sua máquina.

- **Local-first / Privacy-by-Design:** tudo em SQLite local (`~/.agent-ctx/history.db`).
- **Agnóstico de modelo:** fala com os *hosts* (arquivos de estado/logs), nunca com LLMs.
- **Hub-and-Spoke:** um *Common Schema JSON* universal desacopla extractors de injectors.

## Instalação

```bash
python -m pip install -e ".[dev]"
```

## Uso

Inicialize o banco local:

```bash
agent-ctx init
```

Gere um handover a partir do estado de um agente:

```bash
agent-ctx extract \
  --source claude-code \
  --target cursor \
  --project C:/meu/projeto \
  --minutes 30
```

O comando `extract` lê o histórico local do agente de origem e salva um
`HandoverPayload` no banco. Para conferir sem persistir:

```bash
agent-ctx extract --source claude-code --target cursor --project C:/meu/projeto --dry-run
```

### Extratores disponíveis

| `--source` | Origem |
|---|---|
| `claude-code` | Transcripts JSONL de `~/.claude/projects/` (últimas 20 mensagens, ruído filtrado) |
| `cursor` | Prompts e resumo do composer via `state.vscdb` (`aiService.prompts`, `composer.composerData`) |
| `vscode` | Prompts de usuário das sessões de chat (`chatSessions/*.json`) |
| `antigravity` | Fallback — sem histórico estruturado (intenção = handover do projeto) |
| `generic` | Fallback do schema universal |

O scanner de arquivos recentes (janela de `--minutes`, padrão 15) ignora diretórios
como `.git`, `node_modules` e `.venv`, limita o volume de itens e descarta binários.

### Injetar um handover no destino

O comando `inject` carrega um handover já salvo no banco e escreve o estado
no ambiente do agente de destino:

```bash
agent-ctx inject --id <ID> --project C:/meu/projeto
```

O `resume` faz a operação completa numa só chamada — *extract → inject → salvar* —
transferindo contexto entre dois agentes:

```bash
agent-ctx resume --source claude-code --target cursor --project C:/meu/projeto
agent-ctx resume --source claude-code --target cursor --project C:/meu/projeto --dry-run
```

Com `--dry-run`, o contexto é extraído e injetado, mas **não** é persistido no banco.

### Injetores disponíveis

| `--target` | Destino |
|---|---|
| `claude-code` | Resumo markdown em `.claude/agent-context.md` (nunca sobrescreve `CLAUDE.md`) |
| demais agentes | `.agent-ctx/handover.json` no projeto (leitura universal) |

### Outros comandos

```bash
agent-ctx version              # versão instalada
agent-ctx add --file payload.json   # valida e salva um HandoverPayload de JSON
agent-ctx list [-n 20]         # lista handovers recentes
agent-ctx ui                   # inicia dashboard web local
agent-ctx --help               # ajuda geral
```

## Dashboard Web

O comando `agent-ctx ui` inicia um servidor FastAPI local para visualização
da timeline de handovers.

```bash
pip install "agent-ctx[ui]"
agent-ctx ui --open
```

O dashboard é 100% offline e vendoriza Tailwind CSS compilado (sem Node).
Para regerar o CSS após alterar o template:
`tailwindcss -i src/agent_ctx/ui/static/input.css -o src/agent_ctx/ui/static/tailwind.css --minify --content "src/agent_ctx/ui/templates/**/*.html"`

## Roadmap

| Fase | Escopo | Estado |
|---|---|---|
| 1 | Core + banco SQLite + CLI + Schema Universal (Pydantic) | ✅ entregue |
| 2 | Extractors (Claude Code, Cursor/VS Code, Antigravity) + file scanner + comando `extract` | ✅ entregue |
| 3 | Injectors (`.agent-ctx/handover.json`, `.claude/agent-context.md`) + `inject`/`resume` | ✅ entregue |
| 4 | Dashboard local (`agent-ctx ui`, FastAPI + Tailwind) | ✅ entregue |

## Desenvolvimento

```bash
python -m pip install -e ".[dev]"
pytest -q
ruff check .
agent-ctx --help
```

Arquitetura e roadmap detalhados na especificação técnica (PRD v3.0), documento de autoria confidencial que orienta este repositório.
