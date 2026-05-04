# Vertex CLI

CLI para conectar ao proxy Vertex remoto.

## Instalação

```bash
pipx install git+https://github.com/alvaro209890/vertex-cli.git
```

Ou via script:
```bash
curl -fsSL https://raw.githubusercontent.com/alvaro209890/vertex-cli/main/scripts/install-vertex.sh | bash
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

## Modo local (opcional)

```bash
VERTEX_LOCAL_PROXY=true vertex
```
