# Implementação da V1

Especificação: `PROMPT_CODEX_MONITOR_MUSCULAR_V1.md`, fornecida em Downloads.
Ela substitui o escopo anterior de banco/web do Plano de ação v0.2.
Implementação direta autorizada pelo pedido; nenhuma mudança global ou no hardware.

Arquitetura: `Batch` → parser incremental → verificação de continuidade → fila
limitada → buffer NumPy circular → gráfico Qt. Fontes compartilham `open/read/close`.
O worker não acessa widgets. A GUI consome lotes a cada 33 ms. Desconexão cooperativa.

1. [x] Contrato e núcleo: testes de limites, bytes parciais, linhas longas,
   duplicatas, regressões, lacunas, timestamps e buffer antes do código.
   Arquivos: `core/models.py`, `protocol.py`, `continuity.py`, `buffer.py`.
2. [x] Fontes: simulador ajustável e worker com fila limitada, timeout e
   encerramento; integração serial com transporte falso e sem escrita.
   Arquivos: `sources/simulator.py`, `serial_source.py`, `acquisition.py`.
3. [x] Interface: iniciar desconectado; controles de fonte, serial e intensidade;
   gráfico grande com zoom, escala, pausa visual e retorno ao vivo; estados e
   contadores. Arquivos: `ui/window.py`, `ui/plot.py`, `__main__.py`.
4. [x] Verificação: pytest, Ruff, mypy, abertura/fechamento headless, inspeção
   visual nativa e ensaio real de 60 s a 2.000 amostras/s. CI Linux/Windows.
5. [x] Distribuição: dependências fixadas, inicializadores, PyInstaller em
   diretório com licenças, teste Linux e receita Windows; documentação concisa.

Foco de revisão: fechamento enquanto conecta; avalanche de bytes inválidos;
reinício do dispositivo; pausa prolongada e sobrecarga; caminhos com espaços/acentos.
Nenhum teste abre porta física. Somente software sintético pode ser validado aqui.

Concluído: resultados e sistemas efetivamente usados em `verificacao.md`.
Windows e integração física permanecem explicitamente não testados.

