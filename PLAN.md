# Architecture Plan — Vertex CLI

Guia de arquitetura do cliente Vertex. Referenciado por `AGENTS.md`.

## Estrutura do Projeto

```
vertex-cli/
├── cli/                       # Entrypoints e gerenciamento da CLI
│   ├── entrypoints.py         # Funcao principal cli() + modos (remoto/local)
│   ├── session.py             # CLISession: ciclo de vida do subprocesso
│   ├── manager.py             # CLISessionManager: pool assincrono de sessoes
│   ├── process_registry.py    # Rastreador global de PIDs com cleanup atexit
│   └── setup_wizard.py        # Wizard interativo de login Firebase
├── vertex_auth/               # Cliente de autenticacao Firebase
│   └── client.py              # signIn, refresh, logout via REST API
├── vendor/vertex-cli/         # Runtime Node.js empacotado (fork Claude Code)
│   ├── bin/vertex             # Launcher Node.js
│   └── dist/cli.mjs           # Bundle principal (~20MB) com patches PT-BR
├── scripts/                   # Instalacao e manutencao
│   └── install-vertex.sh      # Script one-curl-pipe-bash
├── tests/                     # Testes pytest
│   ├── cli/                   # Testes de entrypoints, sessao, manager
│   └── contracts/             # Testes de contrato (import boundaries, smoke)
└── pyproject.toml             # Build system (hatchling), deps, ferramentas
```

## Fluxo de Dependencia

```
vertex_auth → cli/entrypoints.py → vendor/vertex-cli/bin/vertex
                    ↑
              cli/setup_wizard.py
```

Nao ha dependencia circular. `vertex_auth` e puramente um cliente HTTP Firebase.
`cli/` orquestra autenticacao, verificacao de saldo, update, e lancamento do runtime.

## Modos de Operacao

### Modo Remoto (padrao)
```
Usuario → vertex → cli() → autentica Firebase
                        → GET /me (verifica saldo)
                        → node bin/vertex
                          └── ANTHROPIC_BASE_URL=https://vertex-api.cursar.space
```

### Modo Local
```
Usuario → VERTEX_LOCAL_PROXY=true vertex
       → cli() → python -m vertex_proxy (porta 8083)
               → node bin/vertex
                 └── ANTHROPIC_BASE_URL=http://127.0.0.1:8083
```

## Auto-Update

1. `_check_and_prompt_update()` executado a cada 24h (cache em `~/.vertex/update_check.json`)
2. Consulta `GET /cli-version` na API do servidor
3. Consulta GitHub Releases (`/repos/alvaro209890/vertex-cli/releases/latest`)
4. Usa a **maior versao** entre as duas fontes
5. Se `latest > installed`, pergunta `[Y] Sim, atualizar  [n] Nao  [s] Pular esta versao`
6. Atualiza via `pipx upgrade` ou `uv tool upgrade`

Skip via env: `VERTEX_SKIP_UPDATE_CHECK=1 vertex`

## Configuracao Local

- `~/.vertex/settings.json` — configuracoes da CLI vendored (modelos, env, permissoes)
- `~/.vertex/auth.json` — token Firebase (permissao 0600)
- `~/.vertex/update_check.json` — cache de verificacao de atualizacao
- `~/.vertex/.claude.json` — arquivo de estado da CLI (criado/validado pelo wrapper)
- `~/.config/vertex/.env` — variaveis de ambiente do usuario

## Regras de Desenvolvimento

- **DRY:** Extrair logica compartilhada. Preferir composicao a copy-paste.
- **Encapsulamento:** Usar metodos de acesso, nao atribuicao direta de `_atributos`.
- **Codigo morto:** Remover codigo e valores hardcoded nao utilizados.
- **Tipagem:** Usar `from __future__ import annotations`, type hints, dataclasses frozen.
- **PT-BR:** Todas as strings visiveis ao usuario devem estar em portugues brasileiro.
- **Idempotencia:** Scripts e funcoes de configuracao devem ser seguros para reexecucao.

## Testes

- Framework: pytest + pytest-asyncio + pytest-xdist
- Marcadores: `cli` (integracao), `contract` (contratos de arquitetura)
- Testes de contrato validam fronteiras de importacao, manifesto de features, smoke config
- Nunca adicionar `# type: ignore` ou `# ty: ignore`

## CI / Qualidade

Executar em ordem:
```bash
uv run ruff format  # formatacao
uv run ruff check   # linting
uv run ty check     # type checking
uv run pytest       # testes
```
