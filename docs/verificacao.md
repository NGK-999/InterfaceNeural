# Evidências da V1 — 12/10/2026

Ambiente efetivamente usado: **Ubuntu 24.04.5 LTS x86_64**, kernel
`6.17.0-1033-oem`, glibc 2.39, Python 3.12.3. PySide6-Essentials/Qt 6.12.0,
PyQtGraph 0.14.0, NumPy 2.5.4, pySerial 3.5. Não houve dispositivo físico conectado
pelo aplicativo ou pelos testes; nenhuma gravação de firmware.

## Comandos e resultados

Executados com `.venv/bin/python` neste checkout:

| Comando | Resultado observado |
|---|---|
| `-m pytest -q` | **62 passed** |
| `-m ruff check .` | All checks passed |
| `-m ruff format --check .` | Todos os arquivos verificados já formatados |
| `-m mypy src` | Sem problemas em 15 arquivos, modo strict |
| `-m pip check` | Nenhuma dependência quebrada |
| `scripts/soak.py --seconds 60 --rate 2000 --headless --output artifacts/soak-linux-headless.json` | Todos os dez critérios do ensaio passaram |
| `scripts/build.py` | PyInstaller 6.22.3 concluiu `dist/MuscleMonitor` |

Também executados:

```bash
QT_QPA_PLATFORM=offscreen sh scripts/start.sh --smoke-test
QT_QPA_PLATFORM=offscreen ./dist/MuscleMonitor/MuscleMonitor --smoke-test
./dist/MuscleMonitor/MuscleMonitor --smoke-test
```

Os três encerraram com código **0**. O smoke final abre a interface, inicia somente
o simulador, exige pelo menos 100 amostras e verifica encerramento do worker. A
inicialização normal continua desconectada. O pacote também passou pelo mesmo
smoke após cópia para caminho contendo **espaços e acentos**, a partir de outro
diretório de trabalho. Não foi usado o Python da `.venv` para executar o binário.

## Ensaio de 60 segundos

Resultado completo em [ensaio-linux.json](ensaio-linux.json), somente métricas
agregadas sintéticas. Nenhuma amostra pessoal ou bruta nesse relatório.

| Medida | Observação |
|---|---:|
| Duração real | 60,0597 s |
| Entrada sintética solicitada | 2.000 amostras/s |
| Geradas / recebidas / consumidas | 120.040 / 120.040 / 120.040 |
| Erros / amostras perdidas / descartes | 0 / 0 / 0 |
| Máximo no buffer | 20.001 amostras, dentro de 10 s |
| Maior grupo drenado da fila | 2 lotes; capacidade de 32 |
| Atualizações observadas do loop gráfico | 1.876 |
| Maior intervalo / percentil 99 | 57,11 ms / 32,94 ms |
| RSS após aquecimento | 127,32 a 127,61 MiB |

A visualização ficou pausada aproximadamente entre 15 e 36 s. O ensaio verificou
que a curva permaneceu congelada enquanto a contagem aumentava e que a retomada
mostrou a janela recente. O teste automático complementar entrega 15,0495 s de
tempo sintético e exige janela final de 5,0495 a 15,0495 s, sem replay.

Backend do ensaio medido: **Qt offscreen**. Essa medição confirma processamento,
limites e cadência do loop nesse ambiente; não mede precisão do ESP32 nem EMG.
Uma primeira tentativa de ensaio em janela nativa encerrou antes de gerar
relatório e **não foi contada como aprovada**; sua causa não foi determinada.

## Interface e pacote

Separadamente do ensaio headless, a janela foi aberta no desktop Linux. Pausa,
retorno ao vivo e desconexão foram acionados pela acessibilidade e seus estados
lidos novamente: contagens continuaram na pausa e pararam após desconectar.
Capturas próprias do widget foram inspecionadas visualmente: layout redimensionado
para 1092 × 610 pontos lógicos com escala 125% (1365 × 762 pixels de conteúdo),
gráfico, contraste, texto de simulação e controles legíveis. Não se capturou o
desktop inteiro. Capturas locais: `artifacts/visual-disconnected.png` e
`artifacts/visual-simulation.png`. Isso não é uma inspeção humana de todas as
combinações de escala, tema e monitor.

O pacote Linux ocupa cerca de **211 MiB** em diretório. Sua tabela de módulos foi
inspecionada: sem pytest, psutil, mypy, Ruff, pip, setuptools ou módulos auxiliares
de análise de tipos. Sem PyQt junto do PySide. A ferramenta de medição psutil é
exclusiva do desenvolvimento. Avisos de 87 bibliotecas nativas do sistema foram
coletados; o ZIP upstream com 308 entradas passou na verificação de CRC e hash.

Os avisos do PyInstaller incluem importações opcionais não usadas e símbolos
dinâmicos do NumPy/PyQtGraph. Não foram instaladas essas opções para silenciar
avisos; os fluxos de abertura, aquisição simulada, renderização e fechamento do
binário foram executados com sucesso.

## Cobertura e matriz

Os testes cobrem validação JSON/campos/limites, linhas de 8 KiB e descarte até LF,
UTF-8 inválido, ruído de boot, fragmentação, vários lotes por leitura, continuidade,
duplicatas, regressões, intervalos inconsistentes, buffer circular, sobrecarga da
fila, timeout, fechamento e reconexão. O transporte serial é falso em memória;
uma fixture proíbe `serial.Serial.open` em toda a suíte. Também houve uma execução
do núcleo com imports de Qt/PyQtGraph explicitamente proibidos.

A revisão independente encontrou contadores perdidos quando ruído/lacuna/reinício
chegavam juntos; o teste de regressão falhou antes da correção e passou depois.
A edição manual da porta também recebeu regressão que falhou antes da correção.
O eixo horizontal foi testado em tempos longos: permanece em segundos, sem mudar
automaticamente para quilosegundos. Essa regressão também falhou antes da correção.

| Sistema / cenário | Situação |
|---|---|
| Ubuntu 24.04.5 x64 / testes, tipos, lint | Executado e aprovado |
| Ubuntu / GUI offscreen e ensaio 60 s | Executado e aprovado |
| Ubuntu / GUI nativa e pacote | Abertura, controles descritos, simulação e fechamento executados |
| Windows 10/11 x64 | **Não executado**; instalação e receita de build preparadas |
| GitHub Actions Ubuntu/Windows | Matriz criada; **nenhuma execução remota nesta entrega** |
| Outro Linux, instalação Linux limpa ou outro computador | Não executado |

## Pendências de hardware

Identificar modelo exato do ESP32, firmware existente e responsável pelo firmware;
confrontar contrato, baud rate, sequência, unidade, faixa do ADC e tempo declarado;
medir taxa efetiva, throughput, timeout e efeitos de DTR/RTS em bancada.
Nenhuma equivalência entre contagem ADC, tensão ou grandeza fisiológica foi estabelecida.

Integração serial física **não testada**. Segurança do circuito para contato corporal
**não avaliada** e dependente de revisão qualificada. Nenhum resultado de software
deste documento autoriza teste no corpo.

## Entrega simplificada para Windows

Foi acrescentada a receita `packaging/windows.iss` e o script
`scripts/windows-installer.ps1` para produzir `MonitorMuscular-Instalar.exe`:
instalação por usuário em português, com atalho na área de trabalho.
Nenhuma função de aquisição do aplicativo foi alterada nessa etapa.

A CI Windows foi configurada para compilar o instalador com Inno Setup 6.7.3,
instalar em uma pasta com espaços e acentos, conferir todos os arquivos e o
atalho, executar o smoke do aplicativo instalado e desinstalar. O upload desse
artefato depende do sucesso dessas etapas. A assinatura e o hash conferidos
são do compilador oficial, não do instalador próprio, que ainda não é assinado.
O teste é restrito ao runner da CI e aborta perante instalações anteriores;
o smoke usa Qt offscreen, sem validar o backend gráfico nativo Windows.

Verificações locais: Ruff, formatação, mypy e 62 testes do aplicativo passaram.
A receita e as flags foram confrontadas com documentação oficial e revisão
independente. Compilação, instalação e desinstalação **não foram executadas neste
Linux**, pois não há Windows/ISCC/PowerShell disponíveis. Nenhuma ferramenta
Windows ou camada de emulação foi instalada no computador de desenvolvimento.
As etapas da CI são verificações preparadas, não resultados já obtidos.

## Link direto de download

O README passou a reservar um bloco para o endereço direto do ZIP do instalador.
O job de atualização depende das verificações dos dois sistemas e só usa um
artefato real, não expirado, da mesma execução. Ele preserva o texto fora dos
marcadores e usa o SHA do README para recusar uma edição concorrente.

Verificação local: 24 testes Node com API em memória, validação do YAML e teste
de integração da chamada da CI com o helper e o README. Os 62 testes Python
também passaram. Não houve chamada de escrita ao GitHub durante esses testes.
Atualização do README no GitHub e download real pelo navegador continuam
pendentes da execução remota aprovada; as falhas na CI ainda exigem os logs.
O número da execução é guardado dentro do bloco: uma execução antiga que terminar
depois de uma nova preserva o link mais recente.
