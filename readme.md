# LegoPy

Aplicacao desktop para organizar e exportar sequencias de videos 'Tips' e 'Hooks' usando Tkinter e FFmpeg.

## Visao Geral

- Interface unica com dois fluxos de trabalho: montagem da primeira entrega (First Batch) e das entregas seguintes (Next Batch).
- Garante que cada compilacao de Tips tenha duracao minima de dois minutos e respeite a combinacao correta de Hooks.
- Integra FFmpeg/FFprobe portaveis (pasta ffmpeg-bin/) e aceita substituicao por binarios do sistema via variaveis de ambiente FFMPEG_PATH e FFPROBE_PATH.
- Mantem logs de depuracao (duration_diag.log, ffmpeg_concat_diag.log, ffmpeg_trim_diag.log, etc.) ao lado dos arquivos de origem para facilitar suporte.
- Regras oficiais de nomenclatura (Gotcha! GP.5.1) estao documentadas em [NAMING_RULES.md](./NAMING_RULES.md) e sao aplicadas na geracao automatica de nomes.

## Requisitos

- Windows 10+ ou macOS/Linux com Python 3.10 ou superior.
- Dependencias padroes da biblioteca Tkinter (incluida nas instalacoes oficiais do Python).
- Nenhum pacote extra eh necessario: o projeto usa apenas biblioteca padrao e os binarios de FFmpeg inclusos.

## Como Executar

```bash
python -m legopy
```

Ou, para compatibilidade com scripts antigos:

```bash
python main.py
```

O aplicativo detecta automaticamente o prefixo do projeto (letras) e completa os digitos com zeros a esquerda.

## Fluxos de Trabalho

### First Batch

1. Carregue os arquivos de Tips. O aplicativo cria varias compilacoes rotacionando a ordem dos clips.
2. Opcionalmente carregue intros: elas sao adicionadas antes dos videos exportados.
3. Carregue Hooks apos definir Tips. Cada Hook e sincronizado com a compilacao correspondente.
4. Use "Export Tips Compilations" para gerar videos de dois minutos e "Export All" para criar as sequencias completas (Tips + Hooks).

### Next Batch

1. Carregue Tips e, quando houver, Hooks adicionais para o mesmo projeto.
2. Monte compilacoes manuais com os botoes de adicionar, mover e duplicar.
3. Marque apenas as listas que deseja exportar (checkbox "Export").
4. Ajuste o numero de colunas exibidas e clique em "Export All" para gerar os arquivos finais.

## Estrutura do Projeto

```
legoPy/
+- legopy/
   +- __init__.py
   +- __main__.py
   +- app.py
   +- services/
   |  +- __init__.py
   |  +- media.py
   +- ui/
      +- __init__.py
      +- first_batch.py
      +- next_batch.py
      +- compilation_widgets.py
+- main.py
+- compilations.py
+- first_batch_frame.py
+- next_batch_frame.py
+- utils.py
+- ffmpeg-bin/
+- exe/
```

## Principais Componentes

- BatchSwitcherApp: janela principal que aplica o tema escuro, mostra o menu e alterna entre fluxos.
- FirstBatchFrame: automatiza a criacao de compilacoes e sincroniza Hooks/Tips.
- NextBatchFrame: oferece edicao manual, duplicacao e selecao de compilacoes para export.
- SequenceCompilationsManager: centraliza exportacoes de sequencias e validacoes de resolucao.
- Modulo services.media: localiza FFmpeg, calcula duracoes, concatena/recorta videos e resolve pastas de exportacao.

## Exportacao de Arquivos

- Compilacoes de Tips sao salvas em <projeto>\_Parts_2min.
- Sequencias (Tips + Hooks) sao salvas em <projeto>\_Sequences_RealLength.
- Nomes seguem o padrao <prefixo>\_VxHy_Iz_T_EN.mp4, com indices adaptados automaticamente.

## Empacotamento

- Para gerar um executavel standalone, use o spec localizado em exe/main.spec:
  ```bash
  pyinstaller exe/main.spec
  ```
- Inclua a pasta ffmpeg-bin/ ao distribuir o executavel.

## Desenvolvimento

- Rode "python -m py\*compile legopy/\*\*/\_.py" para validar sintaxe rapidamente.
- Utilize o virtualenv incluso (venv/) se desejar isolar dependencias.
- Logs de diagnostico sao escritos automaticamente quando FFmpeg ou FFprobe falham.

## Suporte e Troubleshooting

- Mensagens de erro sobre duracao ou resolucao indicam arquivos com propriedades diferentes. Verifique com a opcao get_video_resolution (menu Next Batch) antes de exportar.
- Os arquivos \*\_error.log criados nas pastas de destino detalham o comando FFmpeg utilizado e as mensagens retornadas.
- Caso FFmpeg nao seja encontrado, defina FFMPEG_PATH e FFPROBE_PATH apontando para executaveis validos ou mantenha a pasta ffmpeg-bin/ ao lado da aplicacao.
