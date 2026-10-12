# Monitor de Sinais Musculares · V1

Aplicativo desktop local de um canal, em português: simulador ajustável, recepção
serial NDJSON, gráfico de amplitude versus tempo, pausa visual, zoom e estatísticas.
Inicia desconectado com **Simulador** selecionado. Não guarda sessões ou amostras.

## Baixar o projeto

**[Baixar projeto completo — ZIP](https://github.com/NGK-999/InterfaceNeural/archive/refs/heads/main.zip)**

Esse ZIP contém o código-fonte e a documentação. O download exige login no
GitHub com acesso ao repositório privado. Para instalar no Windows, use o
instalador descrito na seção abaixo.

## Instalar no Windows: caminho simples

<!-- windows-installer-download:start -->

<!-- windows-installer-run:4 -->

[**Baixar instalador Windows (.zip)**](https://github.com/NGK-999/InterfaceNeural/actions/runs/38271764003/artifacts/11757880905)

Extraia o ZIP e abra `MonitorMuscular-Instalar.exe`.

<!-- windows-installer-download:end -->

Após a CI aprovar o instalador, o link acima será preenchido automaticamente e
iniciará o download do ZIP **MonitorMuscular-Instalador-Windows-x86_64**. Extraia
o ZIP para encontrar `MonitorMuscular-Instalar.exe`. O download exige login e
acesso ao repositório privado. O link vale enquanto o artefato estiver disponível;
uma nova compilação aprovada atualiza o endereço.

Para quem só vai usar o monitor, Igor entrega o arquivo **MonitorMuscular-Instalar.exe**:

1. Abra `MonitorMuscular-Instalar.exe` com dois cliques.
2. Clique em **Instalar**.
3. Clique em **Concluir** para abrir o monitor.
4. Clique em **Iniciar**, mantendo **Simulador** selecionado.

Nas próximas vezes, abra o atalho **Monitor de Sinais Musculares** na área de trabalho.
O instalador inclui Python, dependências e licenças; não exige terminal ou conta do
GitHub no computador de quem vai usar. Instala só para o usuário atual, sem pedir
administrador. Alvos: Windows 10 1809+ e Windows 11, ambos x64.

**Para Igor entregar o arquivo:** depois de baixar e extrair o ZIP pelo link acima,
entregue somente `MonitorMuscular-Instalar.exe` ao amigo. O repositório
pode continuar privado; o amigo não precisa acessá-lo se receber esse arquivo.

A CI compila, instala, confere arquivos/atalho, roda a simulação e desinstala antes
de disponibilizar o instalador. Essa receita ainda depende de execução Windows;
nenhum instalador Windows foi gerado neste ambiente Linux. O instalador produzido
não tem assinatura digital própria; o primeiro teste deve ser acompanhado se o
Windows exibir um aviso de segurança. Não é necessário desativar proteções do sistema.

Quando a CI concluir, o pacote portátil completo também será disponibilizado como
`MuscleMonitor-windows-latest-x86_64`.
Ele exige extrair a pasta inteira e conservar `_internal` junto de `MuscleMonitor.exe`.

No pacote Linux, abra `MuscleMonitor`, mantendo `_internal` ao lado.
As instruções abaixo são para o código-fonte, que pode ser baixado em **Code →
Download ZIP**, extraído por completo, ou clonado com Git.

## Executar neste computador

Depois de instalar as dependências no ambiente `.venv`:

```bash
sh scripts/start.sh
```

Escolha **Iniciar** para simular. O aviso **SIMULAÇÃO — DADOS ARTIFICIAIS** permanece
visível. Depois de instalar, abrir o aplicativo não baixa nada e não usa internet,
conta, API, ai-memory, navegador ou GPU dedicada.

## Instalar no Linux

Alvo: Ubuntu 24.04 x86_64, Python **3.12** e uma sessão gráfica. Instale o suporte
`python3.12-venv` pelos procedimentos do seu sistema se `venv` informar ausência
de `ensurepip`; não execute o aplicativo como root. Dentro da pasta do projeto:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m pip install --no-deps .
sh scripts/start.sh
```

As bibliotecas gráficas X11/XCB precisam estar presentes para o backend X11;
consulte [requisitos e distribuição](docs/distribuicao.md). Não altere o Python global.

## Instalar no Windows nativo

Alvos: Windows 10 x64 (1809 ou posterior) e Windows 11 x64, com Python **3.12 x64**.
Abra PowerShell na pasta do projeto; não precisa de WSL nem alterar a ExecutionPolicy:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m pip install --no-deps .
.\scripts\start.cmd
```

O ambiente local de desenvolvimento é Linux. A CI Windows avançou até a etapa
do instalador, mas a distribuição ainda aguarda aprovação. A instalação e a
interface nativa Windows continuam pendentes. Veja [evidências](docs/verificacao.md).

## Usar

1. Selecione **Simulador** e pressione **Iniciar**; ajuste a intensidade artificial.
2. Use **Pausar visualização** (`Ctrl+P`) para congelar o gráfico mantendo a aquisição.
3. Arraste o gráfico ou use a roda para zoom; **Voltar ao vivo** (`Ctrl+L`) restaura
   a janela atual de 10 segundos. Ao retomar, dados antigos não são reproduzidos.
4. Desmarque **Escala automática** para ajustar mínimo e máximo do eixo vertical.
5. Pressione **Desconectar** ou feche a janela para encerrar o worker.

Para bancada serial, desconecte, escolha **Serial**, atualize portas, selecione
ou digite a porta e configure o baud rate **conforme o firmware**. Só **Conectar**
abre a porta. O valor inicial de 115200 é editável e não afirma compatibilidade da
placa. A contagem “amostras/s recebidas” mede chegada ao PC, não precisão do ADC.

Porta aberta não significa dados válidos. O monitor mostra “aguardando dados”,
“recebendo”, “sem dados” após 2 segundos sem amostras válidas ou “erro”. Ruído de
inicialização é descartado e contado; falhas nunca trocam serial por simulação.
Reinício/regressão encerra a aquisição e exige nova conexão explícita.

O eixo usa **contagens do ADC**, sem conversão para tensão, força, ângulo ou
atividade fisiológica. Sem filtros, suavização, normalização ou reconhecimento.
Lacunas são desenhadas como interrupções. A janela tem limite de 40.000 amostras;
a fila tem 32 lotes. Sob sobrecarga, os dados mais antigos são descartados e
contabilizados. Expiração normal da janela de 10 s não é perda de aquisição.

## Desenvolvimento e verificação

No ambiente virtual, instale `requirements-dev.lock` e o projeto editável:

```bash
.venv/bin/python -m pip install -r requirements-dev.lock
.venv/bin/python -m pip install --no-build-isolation --no-deps -e .
.venv/bin/python -m pytest
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
.venv/bin/python -m mypy src
.venv/bin/python scripts/soak.py --seconds 60 --rate 2000 --headless
```

No Windows, substitua `.venv/bin/python` por `.\.venv\Scripts\python.exe`.
Os testes proíbem abertura de portas físicas. O núcleo também pode ser testado
sem Qt: `python -m pytest tests/test_protocol.py tests/test_core.py` (NumPy e
pytest; o ambiente de testes completo inclui pySerial para bloquear portas).
Para inspecionar o ensaio em uma janela real, omita `--headless` e aguarde o fechamento.

## Protocolo, build e limites

- [Contrato NDJSON, limites e cálculo de banda](docs/protocolo.md).
- [Build PyInstaller e licenças](docs/distribuicao.md).
- [Sistemas testados e resultados observados](docs/verificacao.md).
- [Decisões e referências consultadas](docs/decisoes.md).

O ESP32 atual não foi conectado nem seu firmware confirmado. Modelo da placa,
faixa/resolução do ADC, condicionamento, taxa real e formato existente permanecem
desconhecidos. O contrato documentado precisa ser confrontado com o firmware e
testado em bancada sem pessoa conectada. Não há código de atuação ou de gravação
de firmware. DTR/RTS podem reiniciar algumas placas mesmo sem transmitir comandos.

**Segurança para contato corporal não foi avaliada.** O aplicativo e o aviso não
validam a montagem elétrica. Revisão qualificada é necessária antes de uso corporal.

Logs técnicos limitados (até três arquivos de 128 KiB) ficam em
`$XDG_STATE_HOME/muscle-monitor`, ou `~/.local/state/muscle-monitor`, no Linux, e
`%LOCALAPPDATA%\MuscleMonitor\logs` no Windows. Não contêm bytes recebidos nem
amostras. Se o diretório não puder ser criado, avisos vão para stderr.

