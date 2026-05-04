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
