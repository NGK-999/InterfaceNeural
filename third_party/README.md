# Avisos de terceiros para a distribuição local

`upstream-notices.zip` contém 308 entradas (306 arquivos oficiais e dois índices gerados), coletadas em 12/10/2026. O build deve extrair o arquivo em `dist/_internal/licenses/upstream/` e copiar este README junto das licenças.

**SHA-256 do ZIP:** `a171f9e5d67deab7ec46ecf67cb8b847f1c295f05e085adb61cbd77413c27dfb`

## Proveniência

| Conjunto | Versão/tag | Árvore retornada pela API oficial |
| --- | --- | --- |
| [qtbase](https://github.com/qt/qtbase/tree/v6.12.0) | `v6.12.0` | `025bdad181de241e81bf853c8a2d7bf3d19261a9` |
| [qtsvg](https://github.com/qt/qtsvg/tree/v6.12.0) | `v6.12.0` | `883a58532078d003cefef0a549bfe9f885ce41f5` |
| [qtwayland](https://github.com/qt/qtwayland/tree/v6.12.0) | `v6.12.0` | `c4f85cd060e3e80a7d71829defac9cf5a40e8ffa` |
| [pyside-setup](https://github.com/pyside/pyside-setup/tree/v6.12.0) | `v6.12.0` | `f50facb83fc3dc5f3240c854668c7a6dd93871b2` |
| [pyserial](https://github.com/pyserial/pyserial/tree/v3.5) | `v3.5` | `0e7634747568547b8a7f9fd0c48ed74f16af4b23` |

Os downloads usam `raw.githubusercontent.com/<organização>/<repositório>/<SHA>/<caminho>`, sem depender de uma branch móvel. `MANIFEST.json`, dentro do ZIP, registra a URL exata, tamanho e SHA-256 de cada arquivo original e preservado. `ATTRIBUTIONS.txt` reúne nomes, versões, copyrights, licenças e caminhos dos avisos em texto legível.

## Conteúdo e seleção

- QtBase: corpus `LICENSES/`, metadados de licença/REUSE, todos os 77 arquivos reais de atribuição fora de testes/exemplos (88 entradas) e seus `LicenseFile`, além dos avisos explícitos encontrados nas árvores selecionadas. Inclui avisos de plataformas e ferramentas não necessariamente presentes no binário: a seleção é conservadora.
- QtSvg: corpus `LICENSES/`, metadados REUSE e regras de licença. Não há `qt_attribution.json` nessa tag; `src/svg/REUSE.toml` preserva o aviso de USC Information Sciences Institute e a licença `HPND-sell-variant`.
- QtWayland: corpus `LICENSES/`, metadados REUSE/regras de licença e a atribuição do Wayland IVI Extension Protocol 1.9.1 com seu texto MIT. Complementa QtWaylandClient, WlShellIntegration e plugins Wayland encontrados no build Linux. É um superconjunto conservador, incluindo avisos compartilhados com o compositor.
- PySide/Shiboken: corpus `LICENSES/`, `COPYING` aplicáveis, aviso Qt e duas atribuições runtime de Python 3.7.0. Em `bufferprocs_py37.h.NOTICE.txt`, foram preservados os comentários iniciais de copyright/licença e o texto PSF completo; as declarações C++ foram omitidas. A transformação está documentada no manifesto.
- pySerial 3.5: `LICENSE.txt` oficial, BSD-3-Clause. NumPy, pyqtgraph, colorama, Python e demais arquivos de licença das distributions instaladas são responsabilidade da coleta separada do build.

Os textos integrais GPLv3 e LGPLv3 já estão nas tags oficiais e foram incluídos. Nenhum livro, código de implementação ou exemplo do aplicativo foi incorporado.

## Limites

Este arquivo é um conjunto de avisos, não o código-fonte correspondente completo das bibliotecas, uma SBOM exata do executável ou uma aprovação jurídica. A presença de uma licença comercial de referência não concede uma licença comercial. As alternativas GPL/LGPL e licenças de ferramentas refletem os avisos upstream; não alteram automaticamente a licença escolhida para o aplicativo.

Não houve arquivos `LicenseFile` ausentes entre as 91 entradas reais de atribuição selecionadas. Entradas sem `LicenseFile` estão acompanhadas de seus metadados e textos SPDX no corpus `LICENSES/`. As atribuições sintéticas de testes e os exemplos upstream foram excluídos. Bibliotecas nativas externas copiadas do sistema pelo empacotador podem exigir avisos adicionais e devem ser conferidas no artefato de cada sistema.

A distribuição usa bibliotecas dinâmicas em diretório. Avisos não substituem as demais condições aplicáveis, como permitir substituição/revinculação das bibliotecas LGPL e disponibilizar seu código correspondente pelo meio adequado. Referências oficiais: [obrigações LGPL do Qt](https://www.qt.io/development/open-source-lgpl-obligations) e [licenças Qt for Python](https://doc.qt.io/qtforpython-6/licenses.html).

## Verificação

O ZIP foi testado com `ZipFile.testzip()`, sem erro de CRC; todos os arquivos oficiais preservados foram conferidos contra os hashes do manifesto. A coleta resolveu todos os caminhos `LicenseFile` selecionados e confirmou os textos completos GPLv3/LGPLv3 para QtBase, QtSvg, QtWayland e PySide/Shiboken. Os 291 arquivos oficiais da coleta anterior foram preservados byte a byte; 15 arquivos oficiais do QtWayland foram adicionados.
