# Contrato de bancada V1

Proposta para implementar ou adaptar no firmware; **não é descrição comprovada
da placa existente**. Um canal, recepção somente, NDJSON UTF-8/ASCII, um objeto
por linha terminado por LF; CRLF também é aceito. Exemplo exclusivamente sintético:

```json
{"v":1,"seq":0,"t0_us":0,"dt_us":1000,"unit":"adc_count","samples":[2048,2051,2046]}
```

| Campo | Regra V1 |
|---|---|
| `v` | inteiro exatamente `1` |
| `seq` | inteiro de 0 a 2⁵³−1; índice da primeira amostra |
| `t0_us` | inteiro de 0 a 2⁵³−1; microssegundos desde o início da sessão da fonte |
| `dt_us` | inteiro de 1 a 1.000.000, constante durante uma conexão |
| `unit` | texto exatamente `adc_count` |
| `samples` | lista com 1 a 128 inteiros entre 0 e 2³²−1 |

Esses limites são limites do **software**, não caracterização do ADC. O índice e
o instante da última amostra também devem caber nos limites. Booleanos, floats,
NaN/Infinity, campos ausentes, extras ou repetidos e objetos não conformes são
rejeitados. Não há execução de conteúdo. O decoder também limita profundidade
por meio do parser JSON e captura erros de recursão.

A linha tem no máximo **8192 bytes antes do LF**, incluindo CR quando presente.
Ao ultrapassar, conta um erro e descarta tudo até o próximo LF; o fragmento não
cresce além do limite. Cada leitura serial pede até 4096 bytes; leituras parciais,
linhas agrupadas, mensagens de boot e UTF-8 inválido são tratadas sem travar.

## Tempo e continuidade

A amostra `i` do lote está em `t0_us + i*dt_us`. O gráfico divide esse instante
por 1.000.000 para exibir segundos. O relógio monotônico do PC serve exclusivamente
para timeout e estatísticas de chegada.

O próximo lote contíguo começa em `seq_anterior + len(samples_anterior)` e no
instante seguinte ao último, com o mesmo `dt_us`. Um avanço de sequência conta
amostras ausentes e só é aceito se o tempo avançar pelo intervalo correspondente.
O gráfico recebe uma quebra; perdas nunca são preenchidas ou ligadas por uma reta.

Um lote idêntico ao último aceito é uma duplicata e não entra no buffer. Qualquer
outra regressão/sobreposição da sequência ou regressão do tempo interrompe a fonte
e pede reconexão. Intervalos/cadência inconsistentes são descartados e contados
como erro; o último lote válido permanece como referência. Não se aceita rollover.

Uma sessão do dispositivo começa em zero, mas a conexão pode observar seu primeiro
lote mais tarde. Não é possível quantificar perdas anteriores a esse primeiro
lote observado. Um reinício que repita exatamente o último lote é indistinguível
de uma retransmissão até chegarem outros lotes; esta V1 não tem identificador de boot.

## Memória, taxas e perdas

Fila: no máximo 32 lotes (4096 amostras). Em sobrecarga, remove o lote mais antigo,
conta suas amostras e marca quebra no próximo visível. Buffer: 40.000 amostras e
10 segundos, o limite que ocorrer primeiro. Expiração por idade é esperada;
evicção por capacidade dentro dos 10 s é contada separadamente. Duplicatas e
mensagens rejeitadas não contam como amostras válidas recebidas.

Não há redução de pontos ou filtro no gráfico: todos os pontos retidos são
fornecidos ao PyQtGraph, com separadores NaN usados apenas na representação de
lacunas. A renderização ocorre aproximadamente a 30 Hz, independente da aquisição.
Durante pausa, apenas uma cópia limitada da curva fica congelada; a fila é drenada
normalmente e o buffer continua expirando.

O simulador padrão gera 1.000 amostras/s, em lotes de 20; o ensaio usa 2.000/s.
São taxas sintéticas. A taxa do PC é contagem de amostras válidas dividida pelo
tempo monotônico entre atualizações de estatística (cerca de um segundo).

## Orçamento serial

Configuração da implementação: 8N1, sem controle de fluxo. Cada byte custa
aproximadamente **10 bits** (start + 8 dados + stop). Portanto:

`bits/s = bytes_por_linha × amostras/s ÷ amostras_por_lote × 10`

O tamanho inclui nomes de campos, pontuação JSON e LF. Com `seq=100000`,
`t0_us=100000000`, `dt_us=1000`, JSON compacto e todas as amostras iguais:

| Lote / valor de exemplo | Bytes com LF | Bytes/s a 1.000 amostras/s | Bits/s 8N1 |
|---|---:|---:|---:|
| 20 / 2048 | 183 | 9.150 | 91.500 |
| 128 / 2048 | 723 | 5.648,4375 | 56.484,375 |
| 128 / 4294967295 | 1491 | 11.648,4375 | 116.484,375 |

Esses tamanhos foram conferidos com `json.dumps(..., separators=(",", ":"))`
e dependem do número de dígitos.
CRLF acrescenta um byte por lote. Índices maiores, espaços, mensagens adicionais
e jitter também consomem banda. Em 2.000 amostras/s a demanda dobra. Logo 115200
não garante toda a faixa V1; não proponha baud real sem calcular o payload real
e medir a placa. Capacidade do transporte não comprova frequência do ADC.

## Abertura da porta

`Serial(port=None)` permite configurar DTR/RTS como falsos antes de abrir; sem
`write()` ou comandos de aplicação. Driver/SO ainda podem produzir pulsos e há
placas ESP32 que usam essas linhas para reset/boot. Não se promete neutralidade
elétrica. [pySerial](https://pyserial.readthedocs.io/en/latest/pyserial_api.html),
[Espressif](https://docs.espressif.com/projects/esptool/en/latest/esp32/advanced-topics/boot-mode-selection.html).

Timeout de leitura: 100 ms. Estado “sem dados”: 2 s sem lote válido novo.
Desconectar solicita parada cooperativa; o worker fecha a porta em `finally`.
Fechar a janela aguarda o término sem bloquear a thread gráfica. Se o driver
travar durante `open()` fora do controle do timeout de leitura, a janela aguarda;
esse comportamento específico do driver ainda precisa de teste físico.
