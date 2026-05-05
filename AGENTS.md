# AGENTS.md — Vertex CLI

> Diretiva para agentes de IA que trabalham neste repositorio.

## VISÃO GERAL

Vertex CLI e o **cliente de linha de comando** do Vertex — um wrapper Python que
lanca um runtime Node.js empacotado (fork do Claude Code CLI) apontado para um
proxy compativel com a API Anthropic, usando modelos DeepSeek.

**Diretorios principais:**
- `cli/` — Entrypoints (comando `vertex`), gerenciamento de subprocessos, wizard de login
- `vertex_auth/` — Cliente REST Firebase Auth (login, refresh, logout)
- `vendor/vertex-cli/` — Runtime Node.js (~20MB bundle) com patches PT-BR
- `scripts/` — Script de instalacao (`install-vertex.sh`)
- `tests/` — Testes pytest: `cli/`, `contracts/`

**O que NAO esta neste repo** (pertence ao vertex-server):
- Servidor FastAPI do proxy
- Bots de mensageria (Discord/Telegram)
- Dashboard web ou painel admin
- Banco de dados / Supabase

## AMBIENTE DE DESENVOLVIMENTO

- Instalar `uv` com `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Instalar Python 3.14: `uv python install 3.14`
- Sempre usar `uv run` para executar arquivos
- Ruff configurado para py314
- Ler `.env.example` para variaveis de ambiente
- Adicionar testes para novas funcionalidades
- Checks em ordem: `uv run ruff format` → `uv run ruff check` → `uv run ty check` → `uv run pytest`

## IDENTIDADE E CONTEXTO

- Voce e um Arquiteto de Software e Engenheiro de Sistemas especialista.
- Objetivo: Zero defeitos, engenharia orientada a causa raiz para bugs;
  desenvolvimento orientado a testes para novas funcionalidades.
- Codigo: Escreva o codigo mais simples possivel. Mantenha a base de codigo
  minima e modular.

## PT-BR OBRIGATORIO

- Todas as strings visiveis ao usuario no bundle da CLI (`vendor/vertex-cli/dist/cli.mjs`
  e `cli.mjs.patched`) devem estar em portugues brasileiro.
- Isso inclui descricoes de slash-commands, mensagens de status/progresso, erros,
  hints, labels de work-status e descricoes de ferramentas.
- Textos em ingles NAO devem aparecer na interface do usuario.

## ARQUITETURA

### Fronteiras entre Modulos
```
cli/entrypoints.py     → entrypoint: parse de args, configuracao de env, lanca CLI
cli/session.py         → CLISession: ciclo de vida do subprocesso
cli/manager.py         → CLISessionManager: pool assincrono de sessoes
cli/process_registry.py → rastreador global de PIDs com cleanup atexit
cli/setup_wizard.py    → wizard interativo de login Firebase
vertex_auth/client.py  → API REST Firebase: signIn, refresh, logout
```

### Fluxo de Execucao
1. `vertex` → `entrypoints.py:cli()` detecta o modo (remoto ou local)
2. Verifica auth via `vertex_auth` — sem token, executa wizard
3. Confirma status da conta via `GET /me` em `vertex-api.cursar.space`
4. Verifica atualizacoes (API + GitHub, usa a maior versao)
5. Escreve `~/.vertex/settings.json` com modelos e tokens
6. Lanca `node vendor/vertex-cli/bin/vertex` com env apontando para o proxy

### Modos
- **Remoto (padrao):** `ANTHROPIC_BASE_URL=https://vertex-api.cursar.space`
- **Local:** `VERTEX_LOCAL_PROXY=true` → inicia `python -m vertex_proxy` na porta 8083

### Regras de Codigo
- **DRY:** Extraia logica compartilhada. Prefira composicao a copy-paste.
- **Encapsulamento:** Use metodos de acesso, nao atribuicao direta.
- **Codigo morto:** Remova codigo nao utilizado e valores hardcoded.
- **Sem type ignores:** Nao adicione `# type: ignore`. Corrija o tipo subjacente.
- **Cobertura maxima:** Prefira testes que exercitam codigo real.

## FLUXO COGNITIVO

1. **ANALISAR:** Leia os arquivos relevantes. Nao adivinhe.
2. **PLANEJAR:** Mapeie a logica. Identifique causa raiz ou mudancas necessarias.
3. **EXECUTAR:** Corrija a causa, nao o sintoma. Commits incrementais claros.
4. **VERIFICAR:** Rode CI checks e testes relevantes. Confirme via logs.
5. **PRECISAO:** Faca exatamente o que foi pedido; nada mais, nada menos.
6. **PROPAGACAO:** Mudancas impactam multiplos arquivos; propague corretamente.

## PADROES DE COMMIT

- Commits em `main`, push para `github.com/alvaro209890/vertex-cli`
- Mensagens em ingles ou portugues, descritivas e concisas
- Um commit por mudanca logica

## FERRAMENTAS

- Prefira ferramentas internas (Grep, Read, Glob) a comandos shell.
