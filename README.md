# Vertex CLI

CLI para conectar ao proxy Vertex remoto.

Versao atual: `1.2.6`. Esta versao ja inclui WebSearch, WebFetch e o binario
`rg` empacotado para o Grep funcionar mesmo em maquinas sem ripgrep instalado.

## Instalação

Instalação recomendada em Linux:

```bash
curl -fsSL https://raw.githubusercontent.com/alvaro209890/vertex-cli/main/scripts/install-vertex.sh | bash
```

Instalação manual via `pipx`:

```bash
python3 -m pip install --user pipx
python3 -m pipx ensurepath
pipx install "git+https://github.com/alvaro209890/vertex-cli.git" --force
vertex --version
vertex auth login
vertex auth status
```

## Painel do cliente

O painel web mostra os dados da conta autenticada: tokens totais, custo estimado
em USD/BRL, pico de consumo por hora, uso diario, mix de entrada/saida/cache,
ultimas chamadas e uso por modelo.

O frontend usa o backend remoto padrao:

```bash
https://vertex-api.cursar.space
```

## Atualizar em outro Linux

Use este comando em cada maquina Linux para instalar ou atualizar a CLI pela
versao atual do `main`:

```bash
curl -fsSL https://raw.githubusercontent.com/alvaro209890/vertex-cli/main/scripts/install-vertex.sh | bash
```

Depois feche e abra o terminal, ou rode:

```bash
source ~/.bashrc 2>/dev/null || true
hash -r
vertex --version
vertex auth login
vertex auth status
```

Se preferir fazer manualmente, rode:

```bash
python3 -m pip install --user pipx
python3 -m pipx ensurepath
source ~/.bashrc 2>/dev/null || true

if ! command -v node >/dev/null 2>&1; then
  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.4/install.sh | bash
  export NVM_DIR="$HOME/.nvm"
  . "$NVM_DIR/nvm.sh"
  nvm install 20
  nvm alias default 20
fi

pipx uninstall vertex-cli 2>/dev/null || true
pipx uninstall vertex-deepseek 2>/dev/null || true
pipx install "git+https://github.com/alvaro209890/vertex-cli.git" --force

hash -r
vertex --version
vertex auth login
vertex auth status
```

Se a maquina ja tinha configuracao antiga e continuar mostrando erro estranho,
limpe a sessao/config local e faca login novamente:

```bash
vertex auth logout
rm -f ~/.vertex/settings.json
vertex auth login
vertex
```

Observacao: a CLI so deve mostrar "Conta bloqueada" quando o servidor responder
explicitamente que a conta foi bloqueada. Respostas `403` genericas de
Cloudflare/WAF agora aparecem apenas como aviso de verificacao de status.

## Uso

```bash
vertex              # Abre a CLI (conectado ao servidor remoto)
vertex auth login   # Fazer login com email/senha
vertex auth status  # Verificar status da autenticacao
vertex /logout      # Fazer logout
```

No modo remoto, a CLI usa o ID token Firebase da sessao autenticada como
`ANTHROPIC_AUTH_TOKEN`. Isso permite que o backend aplique bloqueio e saldo por
usuario nas chamadas `/v1/*`.

## Modo local (opcional)

```bash
VERTEX_LOCAL_PROXY=true vertex
```
