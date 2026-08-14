# AI-SPEC: Handover Inteligente

## 1. Objetivo
Implementar um mecanismo de **Handover Inteligente** que realiza a sumarização semântica do *diff* de alterações antes de realizar o handover de contexto entre agentes ou sessões. O objetivo principal é otimizar o uso da janela de contexto, mantendo a integridade da intenção das mudanças realizadas.

## 2. Arquitetura
O sistema será composto por um pipeline assíncrono de três estágios:

*   **Estágio 1: Extração (Diff Analyzer):** Coleta as mudanças brutas do `git diff`. Utiliza um extrator focado em identificar blocos de código alterados, funções modificadas e estrutura de arquivos.
*   **Estágio 2: Sumarizador (LLM Processor):** Um agente especializado (LLM) que processa o *diff* extraído. Ele sintetiza as mudanças, focando no "porquê" (intenção) e no "quê" (impacto funcional) em vez de apenas listar linhas adicionadas/removidas.
*   **Estágio 3: Payload Enriquecido:** O resultado é encapsulado em um objeto JSON contendo:
    *   `summary`: Texto conciso da mudança.
    *   `impact_areas`: Lista de módulos/funções afetadas.
    *   `intent`: A intenção original extraída das mensagens de commit ou contexto da tarefa.
    *   `token_count_diff`: Metadados comparativos.

## 3. Critérios de Sucesso
*   **Eficiência de Tokens:** Redução superior a 60% no volume de tokens quando comparado ao *diff* bruto.
*   **Preservação de Intenção:** O "Juiz LLM" deve classificar a intenção sumarizada como "fiel" ao original em pelo menos 90% dos casos.
*   **Latência:** Tempo de processamento do pipeline < 5 segundos para *diffs* de tamanho médio (até 20 arquivos).

## 4. Plano de Evals
Para garantir a qualidade, utilizaremos um pipeline de avaliação automatizado:
*   **Juiz LLM:** Um subagente que compara dois payloads (RAW vs SUMARIZADO).
*   **Dimensões de Avaliação:** Fidelidade, Concisão e Utilidade para o Destinatário.

## 5. Implementação پیشنهادی
1. Extrair diffs e metadados do handover atual.
2. Enviar apenas os trechos relevantes para o sumarizador.
3. Persistir tanto o payload bruto quanto o resumido.
4. Expor no dashboard a diferença entre contexto bruto e contexto sintetizado.
5. Validar a qualidade com um conjunto rotulado de handovers históricos.
