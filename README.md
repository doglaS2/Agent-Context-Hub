# AgentContext Hub

Motor de **State Handover** agnóstico para agentes de IA — 100% local-first.

O AgentContext Hub transfere o estado de trabalho (intenção, arquivos modificados,
logs de conversa) entre agentes e IDEs — Claude Code, Cursor, VS Code, Antigravity —
sem depender de cloud, mantendo todos os dados na sua máquina.

- **Local-first / Privacy-by-Design:** tudo em SQLite local (`~/.agent-ctx/history.db`).
- **Agnóstico de modelo:** fala com os *hosts* (arquivos de estado/logs), com sumarização multi-provider (Anthropic, OpenAI, Gemini, Ollama, Local).
- **Hub-and-Spoke:** um *Common Schema JSON* universal desacopla extractors de injectors.

⚙️ **Como funciona a arquitetura:**

• **Extractors & Local Parsers:** Vasculham diretamente os logs de sessão do terminal (ex: `~/.claude`) e fazem queries nos bancos SQLite locais das IDEs (`state.vscdb`) para extrair intenção e histórico de chat.

• **File Scanner por mtime:** Percorre o projeto capturando diffs e arquivos alterados nos últimos minutos via metadados do sistema operacional, sem depender de commits no Git.

• **Semantic Summarizer (Multi-Provider + Fallback Local):** Processa opcionalmente os diffs brutos de código gerando resumos semânticos focados em impacto funcional e intenção. Suporta múltiplos provedores de LLM (`anthropic`, `openai`, `gemini`, `ollama`, `local`) via variáveis de ambiente ou flags CLI, com fallback heurístico 100% local quando chaves ou dependências não estão presentes.

### Provedores de sumarização

| `--provider` | Variável de ambiente | Modelo padrão | Pré-requisito |
|---|---|---|---|
| `anthropic` | `ANTHROPIC_API_KEY` | `claude-3-5-sonnet-20241022` | SDK `anthropic` |
| `openai` | `OPENAI_API_KEY` | `gpt-4o-mini` | SDK `openai` |
| `gemini` | `GEMINI_API_KEY` ou `GOOGLE_API_KEY` | `gemini-1.5-flash` | SDK `google-generativeai` |
| `ollama` | `OLLAMA_HOST` (default `http://127.0.0.1:11434`) | `llama3.2` | Servidor Ollama local |
| `local` | — | — | Nenhum (heurística pura) |

Precedência: flag `--provider` > `AGENT_CTX_SUMMARIZER_PROVIDER` > chave disponível
`ANTHROPIC`/`OPENAI`/`GEMINI`/`OLLAMA_HOST` > `local` (Claude na ausência de chave).

Sumarizador é opcional. Sempre que o provedor configurado não estiver disponível
(SDK ausente, credencial inválida, servidor fora do ar), o fallback local é
acionado automaticamente e a execução segue.

• **Common Schema JSON:** Normaliza o estado bruto em uma estrutura de dados universal validada via Pydantic, atuando como um hub desacoplado.

• **Injectors Automatizados:** Converte o schema no formato esperado pela ferramenta de destino (injetando instruções direto no chat ou gerando regras dinâmicas).

• **Dashboard Local-First:** Armazena o histórico em um SQLite local e roda um servidor FastAPI leve com interface gráfica (Tailwind CSS) para auditar cada handover sem enviar nenhum byte pra nuvem.

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

Enriquecer o handover com resumo semântico (multi-provider):

```bash
# Usar o provedor autodetectado (ou fallback local)
agent-ctx extract --source claude-code --target cursor --project C:/meu/projeto --summarize

# Escolher provedor e modelo explicitamente
agent-ctx extract --source claude-code --target cursor --project C:/meu/projeto \
  --summarize --provider openai --model gpt-4o-mini
agent-ctx extract --source claude-code --target cursor --project C:/meu/projeto \
  --summarize --provider ollama --model llama3.2
agent-ctx extract --source claude-code --target cursor --project C:/meu/projeto \
  --summarize --provider local
```

Também há um comando standalone para sumarizar um diff bruto:

```bash
agent-ctx summarize --provider gemini --intent "refatoração de auth" \
  --diff "diff --git a/auth.py b/auth.py
+def login(user, pwd): return jwt.encode(user)"
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
transferindo contexto entre dois agentes (`--provider`/`--model` também suportados):

```bash
agent-ctx resume --source claude-code --target cursor --project C:/meu/projeto
agent-ctx resume --source claude-code --target cursor --project C:/meu/projeto --dry-run
agent-ctx resume --source claude-code --target cursor --project C:/meu/projeto \
  --summarize --provider anthropic
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
agent-ctx --help               # ajuda geral
```

## Tutorial

```bash
python -m pip install -e ".[dev]"
agent-ctx --help
agent-ctx extract --source claude-code --target cursor --project .
agent-ctx inject --id <ID> --project .
agent-ctx ui
```

Para usar o dashboard local (FastAPI + Tailwind), instale os extras da interface:

```bash
python -m pip install -e ".[ui]"
```

O fluxo básico é:
1. Extrair contexto do agente de origem.
2. Injetar o handover no agente de destino.
3. Abrir o dashboard local para revisar a timeline.

O dashboard roda 100% local com FastAPI e Tailwind CSS compilado no projeto.

Para regerar o CSS após alterar os templates:

```bash
npx tailwindcss -i src/agent_ctx/ui/static/input.css -o src/agent_ctx/ui/static/tailwind.css --minify --content "src/agent_ctx/ui/templates/**/*.html"
```

## Desenvolvimento

```bash
pytest -q
ruff check .
agent-ctx --help
```
