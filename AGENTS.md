# Monitor de Sinais Musculares — V1

Preserve arquivos e alterações existentes. Responda em português brasileiro.
Escopo: desktop local, um canal, simulador e recepção serial NDJSON, janela em
memória de 10 segundos. Sem banco, nuvem, IA, filtros analíticos ou atuação.

Não abra portas físicas em testes, não grave firmware nem envie comandos à placa.
Conexão real exige ação explícita do operador. Segurança corporal não foi avaliada.
Não registre amostras nem conteúdo serial bruto em logs, arquivos ou memórias.

`core/`: modelos, parser, continuidade e buffer, sem Qt ou hardware.
`sources/`: fontes e worker com fila limitada. `ui/`: widgets somente na thread Qt.
Use Python 3.12 e `.venv`; não altere configuração global ou Python do sistema.

Verificações (use `.venv/bin/python` ou `.venv\Scripts\python.exe`):
`python -m pytest`, `python -m ruff check .`, `python -m ruff format --check .`,
`python -m mypy src`, `python scripts/soak.py --seconds 60 --rate 2000`.
Os testes usam transporte em memória; o ensaio usa apenas dados sintéticos.
Documente separadamente execução headless, inspeção visual, sistema e hardware.
Não publique releases, envie commits ao remoto ou altere grupos/permissões.

