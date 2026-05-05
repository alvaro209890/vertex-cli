# Vertex CLI

CLI para conectar ao proxy Vertex — um assistente de codigo com IA baseado em
modelos DeepSeek, acessivel direto do terminal.

**Versao atual:** `1.2.6`

## O que e

Vertex CLI e um wrapper Python que lanca um runtime Node.js empacotado (fork do
Claude Code CLI) configurado para usar modelos DeepSeek (v4-flash, v4-pro)
atraves de um proxy compativel com a API Anthropic.

### Funcionalidades

- Assistente de codigo no terminal com contexto do seu projeto
- WebSearch e WebFetch integrados (ferramentas de busca e extracao web)
- Grep nativo (ripgrep empacotado, sem necessidade de instalacao externa)
- Suporte a MCP (Model Context Protocol) para extensibilidade
- Atualizacao automatica (verifica API do servidor e GitHub Releases)
- Dois modos de operacao: remoto (padrao) e local

## Instalacao

### Linux (recomendado)

```bash
curl -fsSL https://raw.githubusercontent.com/alvaro209890/vertex-cli/main/scripts/install-vertex.sh | bash
```

O script instala Node.js 20+ (via nvm), Python 3.12+, pipx, e a CLI Vertex.
Depois feche e reabra o terminal, ou rode:

```bash
source ~/.bashrc 2>/dev/null || true
hash -r
vertex --version
```

### Manual (pipx)

```bash
python3 -m pip install --user pipx
python3 -m pipx ensurepath
pipx install "git+https://github.com/alvaro209890/vertex-cli.git" --force
vertex --version
```

### Requisitos

- Linux x64 (principal) ou ambiente compativel
- Node.js 20+ (instalado automaticamente pelo script)
- Python 3.12+
- git

## Uso

```bash
vertex                 # Abre a CLI (conectado ao servidor remoto)
vertex auth login      # Fazer login com email/senha
vertex auth status     # Verificar status da autenticacao
vertex auth logout     # Fazer logout
vertex --version       # Mostrar versao instalada
```

No primeiro uso, voce sera guiado por um wizard de autenticacao (email/senha
Firebase). O token e armazenado localmente em `~/.vertex/auth.json`.

### Modo local (opcional)

Inicia um proxy local na porta 8083 em vez de conectar ao servidor remoto:

```bash
VERTEX_LOCAL_PROXY=true vertex
```

Util quando voce tem o `vertex-server` rodando localmente.

## Comandos disponiveis na CLI

| Comando | Descricao |
|---------|-----------|
| `/help` | Mostrar ajuda e comandos disponiveis |
| `/config` | Abrir painel de configuracao (tema, modelo, permissoes) |
| `/model` | Selecionar modelo (flash/pro) |
| `/mcp` | Gerenciar servidores MCP |
| `/plugin` | Gerenciar plugins |
| `/resume` | Retomar sessoes anteriores |
| `/status` | Ver status da sessao atual |
| `/logout` | Fazer logout |
| `/clear` | Limpar historico da sessao |
| `/compact` | Compactar contexto da conversa |
| `/add-dir` | Adicionar diretorio ao workspace |
| `/ide` | Conectar ao VS Code/JetBrains |
| `/pr` | Criar/manejar pull requests |
| `/review-pr` | Revisar pull requests |
| `/commit` | Gerar commit com as alteracoes |

## Configuracao

As configuracoes sao salvas em `~/.vertex/settings.json`. Principais opcoes:

- **Modelo:** alternar entre `deepseek-v4-flash` (rapido) e `deepseek-v4-pro` (potente)
- **Tema:** escuro, claro, daltonico-friendly, ou cores ANSI
- **Permissoes:** modo padrao, auto-aprovacao, ou bypass
- **Output style:** formato das respostas (padrao, compacto, verbose)

## Atualizacao

A CLI verifica automaticamente por atualizacoes a cada 24h (via API do servidor
e GitHub Releases). Se houver versao nova, voce sera perguntado se deseja
atualizar.

Para atualizar manualmente:

```bash
pipx upgrade vertex-cli
```

Para pular a verificacao de atualizacao:

```bash
VERTEX_SKIP_UPDATE_CHECK=1 vertex
```

## Solucao de problemas

### "Runtime do Vertex CLI nao encontrado"

```bash
pipx uninstall vertex-cli
pipx install "git+https://github.com/alvaro209890/vertex-cli.git" --force
```

### "Node.js e necessario"

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.4/install.sh | bash
source ~/.bashrc
nvm install 20
nvm alias default 20
```

### "Sessao expirada"

```bash
vertex auth login
```

### Erros estranhos apos atualizacao

```bash
vertex auth logout
rm -f ~/.vertex/settings.json
vertex auth login
vertex
```

## Arquitetura

```
vertex (comando)
  └── cli/entrypoints.py         # Entry point Python
        ├── vertex_auth/         # Autenticacao Firebase
        ├── Verifica saldo (/me)
        ├── Verifica atualizacao (API + GitHub)
        ├── Configura ambiente (modelos, tokens)
        └── Lanca vendor/vertex-cli/bin/vertex (Node.js)
              └── Conecta em vertex-api.cursar.space (remoto)
                    ou 127.0.0.1:8083 (local)
```

### Fluxo de execucao

1. `vertex` → `cli()` detecta modo (remoto por padrao, local se `VERTEX_LOCAL_PROXY=true`)
2. Verifica autenticacao Firebase — se nao autenticado, abre wizard de login
3. Confirma status da conta via `GET /me` no servidor remoto
4. Verifica atualizacoes (API do servidor → GitHub Releases, usa a maior)
5. Escreve `~/.vertex/settings.json` com modelos e configuracoes
6. Lanca `node vendor/vertex-cli/bin/vertex` com ambiente configurado

## Painel do cliente

O painel web mostra dados da conta: tokens totais, custo estimado em USD/BRL,
pico de consumo, uso diario, e metricas por modelo.

Acesse em: https://vertex-ad5da.web.app

## Repositorios relacionados

- [vertex-server](https://github.com/alvaro209890/vertex-server) — Backend do proxy, bots Discord/Telegram, dashboard admin
