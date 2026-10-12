# Decisões e referências

Registro de 12/10/2026, restrito a este projeto. Não contém dados de coleta.

## Escopo e ambiente

A especificação `PROMPT_CODEX_MONITOR_MUSCULAR_V1.md` foi lida integralmente,
assim como o `Plano_de_acao_EMG_v0_2.txt`, fornecidos em Downloads. A V1 mais
recente substitui as propostas anteriores de ASP.NET/SQLite e define Python,
um canal, janela em memória, sem gravação de sessões. Repositório inicial vazio,
commit `c2bf8d0`, sem alterações a preservar além do Git. Não houve push ou release.

Tecnologias verificadas no PyPI e nas documentações oficiais: Python 3.12.3,
PySide6 6.12.0, PyQtGraph 0.14.0, NumPy 2.5.4 e pySerial 3.5. O projeto usa
**PySide6-Essentials**: é a distribuição oficial que fornece os módulos
`PySide6.QtCore/QtGui/QtWidgets`, suficiente para esta interface. Evita instalar
WebEngine/Pdf/Addons, sem trocar para PyQt. Sem bibliotecas de IA.
Pins diretos e transitivos nos dois arquivos `requirements*.lock`.

Qt 6.12 declara suporte a Windows 10 ≥1809, Windows 11 e Ubuntu 24.04;
compatibilidade declarada não substitui execução. Windows não estava disponível.
[Qt](https://doc.qt.io/qt-6/supported-platforms.html),
[PySide6-Essentials](https://pypi.org/project/PySide6-Essentials/6.12.0/),
[PyQtGraph estável](https://pypi.org/project/pyqtgraph/0.14.0/).

`python3 -m venv` falhou porque o sistema não tinha `ensurepip`. Foi criado pip
apenas dentro de `.venv`, usando o bootstrap oficial PyPA. Nenhum pacote de sistema,
grupo, driver ou configuração global foi alterado. Instalações futuras seguem o
procedimento normal de venv documentado no README.

## Estrutura e escolhas

Responsabilidades: modelos/parser/continuidade/buffer em `core`; fontes e worker
em `sources`; widgets em `ui`. Núcleo sem importação de Qt. Uma thread de aquisição
e QTimer de 33 ms na GUI, sem sinal por amostra. Fila de 32 lotes e buffer de 40.000
amostras, com descarte dos mais antigos e contadores. Renderização sem redução de
pontos para preservar os dados e as lacunas. Pausa não impede a drenagem da fila.

Os limites numéricos e a cadência constante do contrato são decisões V1 de
software. São ajustáveis por mudança futura explícita de contrato após conhecer
o firmware. A serial não envia comandos; DTR/RTS são desativados antes da abertura,
com os limites do driver documentados. A lista de portas só é consultada por ação
no botão Atualizar; conexão sempre exige ação do operador.

## Referências solicitadas

- [clean-code-book](https://github.com/Gatjuat-Wicteat-Riek/clean-code-book):
  README consultado; ele aponta para um PDF e não apresenta conteúdo técnico
  próprio. **O livro não foi baixado, lido nem redistribuído.** Aplicados os
  princípios já exigidos no prompt: legibilidade, nomes claros, funções coesas,
  erros explícitos e separação por responsabilidade.
- [Vibe Coding Toolkit](https://github.com/soumatheusgomes/vibe-coding-toolkit):
  README consultado; planejamento curto, testes antes do núcleo, revisão
  independente e verificações adaptadas para pytest/Ruff/mypy. Nenhum plugin ou
  ferramenta JavaScript foi instalado. Uma implementação principal; consultas
  e revisão independentes delegadas para reduzir espera e conferir falhas.
- [ai-memory](https://github.com/akitaonrails/ai-memory): README, documentação de
  [suporte](https://github.com/akitaonrails/ai-memory/blob/main/docs/support-matrix.md)
  e [exclusões](https://github.com/akitaonrails/ai-memory/blob/main/docs/marker-file.md#capture-exclusions)
  consultados. Sem executável no PATH ou locais usuais, processo/serviço identificado,
  integração no Codex ou ferramenta MCP exposta. O diretório local continha apenas
  `logs/`; conteúdo desses logs e memórias de outros projetos não foi lido.
  Sem binário, não foi possível conferir help de versão instalada. Não reinstalado
  ou configurado; este arquivo é o registro curto de decisões solicitado.

Não existe dependência de ai-memory no aplicativo ou build. `.gitignore` não é
exclusão de captura. Se a integração vier a ser instalada, validar no help/documentos
daquela versão o escopo do projeto e `[capture] ignore_paths` antes de dados privados;
filtros de caminhos não garantem remoção de conteúdo de prompts ou comandos shell.
Nenhuma amostra real foi processada ou enviada a memória nesta implementação.

## Documentação técnica consultada

- [Qt for Python](https://doc.qt.io/qtforpython-6/),
  [requisitos Linux](https://doc.qt.io/qt-6/linux-requirements.html),
  [PyQtGraph](https://pyqtgraph.readthedocs.io/en/latest/getting_started/installation.html).
- [pySerial](https://pyserial.readthedocs.io/en/latest/pyserial_api.html) e
  [boot ESP32](https://docs.espressif.com/projects/esptool/en/latest/esp32/advanced-topics/boot-mode-selection.html).
- [PyInstaller](https://pyinstaller.org/en/stable/operating-mode.html),
  [licença](https://pyinstaller.org/en/stable/license.html),
  [Qt for Python licenças](https://doc.qt.io/qtforpython-6/licenses.html).
- [AGENTS.md](https://developers.openai.com/codex/guides/agents-md): arquivo local
  curto com escopo, preservação, limites e comandos reais de verificação.

