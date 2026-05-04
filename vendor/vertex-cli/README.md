# Vertex CLI Runtime Vendorizado

Este diretorio contem o runtime JavaScript vendorizado que o comando `vertex`
executa depois de iniciar o proxy local.

Vertex foi criado por Alvaro Emanuel Alves Araujo. Ele nao e um produto da
Anthropic. A identidade do assistente e fixada como Vertex, e o trafego de
modelo passa pelo proxy local Anthropic-compativel para os modelos DeepSeek.

## Uso Normal

Usuarios finais nao precisam executar arquivos deste diretorio diretamente.
Use sempre:

```bash
vertex
```

Para trocar a chave DeepSeek:

```bash
vertex /logout
vertex auth login
```

## Fluxo De Patch

`dist/cli.mjs` e um bundle gerado. Qualquer ajuste feito nele deve tambem ser
registrado em `../../patches/vertex-cli-disable-anthropic-login.patch`, para que
o patch possa ser reaplicado quando o runtime vendorizado for atualizado.

O patch cobre todas as traducoes para portugues brasileiro dos comandos,
mensagens de status, descricoes de ferramentas e textos visiveis ao usuario
na CLI. Alteracoes em strings visiveis devem sempre ser refletidas no patch.

Depois de alterar o bundle, rode:

```bash
node --check vendor/vertex-cli/dist/cli.mjs
uv run pytest tests/cli/test_vertex_cli_version.py
```

## Invariantes Do Vertex

- Login de conta Anthropic fica desativado.
- O estado de login suportado e somente a chave `DEEPSEEK_API_KEY`.
- Os modelos expostos usam DeepSeek.
- Os comandos e mensagens visiveis do Vertex devem ficar em portugues quando
  forem parte da experiencia direta da CLI.
