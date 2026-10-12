# Build local e distribuição

## Instalador Windows para quem só vai usar

O arquivo a entregar é `MonitorMuscular-Instalar.exe`. Ele instala o pacote
completo, cria atalhos na área de trabalho e no menu Iniciar e oferece abrir o
aplicativo ao concluir. A interface do instalador é em português brasileiro.
Não exige Python, GitHub ou terminal no computador do usuário final.

Instalação por usuário em `%LOCALAPPDATA%\Programs\MuscleMonitor`, sem elevação.
Somente Windows 10 1809+ e Windows 11 x64. O `AppId` permanece estável nas
atualizações; fechamento de aplicações é cooperativo, sem opção `force` e sem
reabrir automaticamente uma aquisição anterior. A desinstalação não apaga os
logs em `%LOCALAPPDATA%\MuscleMonitor\logs`.

Na CI, `scripts/windows-installer.ps1` usa Inno Setup **6.7.3** em uma pasta
temporária isolada. O download vem do fornecedor oficial, com SHA256 fixado e
assinatura Authenticode conferida (Pyrsys B.V.). Instala o compilador em modo
portátil no runner, sem associação `.iss`, atalhos ou instalação global. O
compilador não é uma dependência do aplicativo e não vai para o PC do amigo.

O script compila `packaging/windows.iss`, instala em uma pasta de teste, compara
todo o payload com o pacote original, confere destino/diretório do atalho, roda
`--smoke-test` e desinstala. A CI só disponibiliza o artefato
`MonitorMuscular-Instalador-Windows-x86_64` depois que essas etapas passam.

O script de instalação/desinstalação é restrito à CI do GitHub (PowerShell 7,
`GITHUB_ACTIONS` e `RUNNER_TEMP`); não deve ser executado no PC de quem usa o
monitor. Ele também aborta caso encontre registro, atalhos ou pasta anteriores.
Para compilar manualmente, um desenvolvedor com o pacote Windows e o compilador
Inno Setup 6.7.3 pode chamar `ISCC.exe /DAppVersion=0.1.0 packaging\windows.iss`;
essa chamada só gera o instalador e não instala/desinstala o aplicativo.

O smoke da CI usa Qt `offscreen`: confirma payload, inicialização, simulador e
encerramento, mas o primeiro teste gráfico nativo Windows ainda cabe ao operador.

O executável próprio ainda não é assinado digitalmente. A assinatura verificada
do compilador não assina o instalador produzido. Não há desativação de proteções,
instalação de drivers, abertura de portas físicas ou alteração de firmware.
Compilação e execução Windows ainda precisam ser confirmadas pela CI; esta
receita não foi executada no Linux.

Referências: [Inno Setup](https://jrsoftware.org/isdl.php),
[hash do instalador 6.7.3](https://raw.githubusercontent.com/microsoft/winget-pkgs/master/manifests/j/JRSoftware/InnoSetup/6.7.3/JRSoftware.InnoSetup.installer.yaml),
[modo portátil oficial](https://raw.githubusercontent.com/jrsoftware/issrc/is-6_7_3/isportable.iss),
[privilégios](https://jrsoftware.org/ishelp/topic_setup_privilegesrequired.htm).

## Pacote portátil e código-fonte

Execute o build no **próprio sistema-alvo**, com Python 3.12 x64 e o ambiente de
desenvolvimento instalado. Não há compilação Windows feita no Linux.

Linux:

```bash
.venv/bin/python -m pip install -r requirements-dev.lock
.venv/bin/python -m pip install --no-build-isolation --no-deps -e .
.venv/bin/python scripts/build.py
./dist/MuscleMonitor/MuscleMonitor
```

Windows PowerShell, receita ainda não executada:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
.\.venv\Scripts\python.exe -m pip install --no-build-isolation --no-deps -e .
.\.venv\Scripts\python.exe scripts\build.py
.\dist\MuscleMonitor\MuscleMonitor.exe
```

Copie **a pasta inteira** `dist/MuscleMonitor`, incluindo `_internal`, avisos e
documentação. O pacote é `onedir`, não um único executável. PyInstaller inclui
o interpretador e os módulos necessários; não inclui ferramentas de qualidade,
ai-memory ou dependências de IA. A inicialização não usa pip ou rede.

O comando de build substitui apenas `build/` e `dist/MuscleMonitor` gerados por
este projeto. Não coloca dados de aquisição no pacote nem publica artefatos.
Scripts e execução aceitam caminhos com espaços/acentos, sem comandos shell
construídos a partir do nome da porta.

## Requisitos externos

No Linux, uma sessão gráfica e as bibliotecas do sistema usadas pelo backend Qt
continuam necessárias. Em X11/XWayland, isso inclui X11/XCB, `libxcb-cursor0`,
`libxkbcommon-x11-0`, Fontconfig e FreeType. Confira a falta específica relatada
pelo loader/plugin; não instale indiscriminadamente pacotes de compilação.
O pacote gerado em Ubuntu 24.04 não promete rodar em distribuições mais antigas.
[Requisitos oficiais](https://doc.qt.io/qt-6/linux-requirements.html).

No Windows, drivers USB/serial adequados e permissões continuam necessários.
O aplicativo não instala drivers e não altera configuração da placa. No Linux,
em caso de acesso negado, consulte `ls -l /dev/<porta>` e `id`; um administrador
deve avaliar a política/grupo adequado e eventual nova sessão de login. Não
recomendar `chmod 777`, execução como root ou alterações automáticas de grupo.

## Avisos e fontes

O build copia licenças encontradas nas distribuições instaladas (inclusive
terceiros do NumPy), o texto de licença do Python e os avisos oficiais versionados
em `third_party/upstream-notices.zip`. A origem está em `third_party/README.md`.
O pacote contém `_internal/licenses/versions.json` e os textos extraídos.
No Ubuntu, o build identifica as bibliotecas nativas efetivamente copiadas pelo
PyInstaller e inclui seus arquivos `copyright` via `dpkg-query`, os textos em
`/usr/share/common-licenses` e a relação em `system-libraries.json`.

Qt e PySide são bibliotecas dinâmicas em `_internal`, sem vinculação estática ou
alteração de seus binários. Não se proíbe substituir essas bibliotecas ou depurar
essas substituições. Fontes correspondentes e instruções oficiais:

- [Qt 6.12.0](https://download.qt.io/archive/qt/6.12/6.12.0/submodules/),
  [qtbase v6.12.0](https://github.com/qt/qtbase/tree/v6.12.0),
  [qtsvg v6.12.0](https://github.com/qt/qtsvg/tree/v6.12.0),
  [qtwayland v6.12.0](https://github.com/qt/qtwayland/tree/v6.12.0).
- [PySide/Shiboken v6.12.0](https://github.com/pyside/pyside-setup/tree/v6.12.0),
  [build do Qt for Python](https://doc.qt.io/qtforpython-6/building_from_source/index.html).
- [Termos Qt for Python](https://doc.qt.io/qtforpython-6/licenses.html) e
  [obrigações LGPL](https://www.qt.io/development/open-source-lgpl-obligations).

Os avisos acompanham este build local; não representam revisão jurídica de uma
futura distribuição pública. Nenhuma licença para o código próprio do usuário foi
escolhida unilateralmente. Não houve publicação de release.
