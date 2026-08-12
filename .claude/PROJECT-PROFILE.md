# PROJECT PROFILE

> Perfil do projeto lido pelas skills `dev-*`. Detectado e confirmado com o
> aprovador em 2026-08-11 (run-2026-08-11-phase1).

## Identidade

- **Projeto:** AgentContext Hub
- **Aprovador:** Douglas Siqueira (doglaS2)

## Git

- **Branch de produção:** main
- **Fluxo de entrega:** PR para a branch de produção
- **Isolamento:** worktree

## Gates de qualidade

- **Lint:** `ruff check .`
- **Tipos:** nenhum (Python sem mypy por ora)
- **Testes (unit/integração):** `pytest -q`
- **Build:** `python -m pip install -e .`
- **E2E:** nenhum

## Ambientes

- **Produção acessível para verificação?** não
  - Ferramenta 100% local-first; critério de pronto = suíte verde + build verde.

## Inspeção de dados (read-only)

- **Ferramenta:** nenhuma
- **Regras:** dados sensíveis de código/conversa nunca saem da máquina (princípio
  Local-First do PRD).

## Especificação

- **Usa spec formal antes de implementar?** não
  - Decisões de alto risco exigem plano curto aprovado por mensagem antes do código.
- **Diretório de ciclo/aprovações:** C:\Users\dougx\.agent-ctx-hub-runs

## Superfícies do sistema

- CLI (`agent-ctx`)
- Interface web (Fase 4 — ainda não existe)

## Ferramentas de verificação autorizadas

- **Para interface:** nenhuma (a interface web será adicionada na Fase 4)
- **Proibidas:** nenhum browser com janela visível
- **Restrições:** sessão única
- **Verificador de interface:** nenhum
