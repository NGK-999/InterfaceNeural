const assert = require('node:assert/strict');
const test = require('node:test');

const start = '<!-- windows-installer-download:start -->';
const end = '<!-- windows-installer-download:end -->';
const artifactName = 'MonitorMuscular-Instalador-Windows-x86_64';
const url = 'https://github.com/NGK-999/InterfaceNeural/actions/runs/123/artifacts/456';
const prefix = '# Projeto\r\n\r\nDescrição com ação e espaço.\r\n';
const suffix = '\r\n\r\n## Executar\r\nTexto que precisa ser preservado.\r\n';
const readme = `${prefix}${start}\r\nLink anterior\r\n${end}${suffix}`;

function fixture(options = {}) {
  const pages = options.pages ?? [[{ id: 456, name: artifactName, expired: false }]];
  const calls = { reads: [], writes: [], listings: [] };
  const context = {
    repo: { owner: 'NGK-999', repo: 'InterfaceNeural' },
    runId: 123,
    runNumber: 3,
    serverUrl: 'https://github.com',
    ...options.context,
  };
  const file = options.file ?? {
    type: 'file',
    encoding: 'base64',
    sha: 'abcdef1234567890abcdef1234567890abcdef1234',
    content: Buffer.from(options.readme ?? readme, 'utf8').toString('base64'),
  };
  const github = {
    rest: {
      actions: {
        async listWorkflowRunArtifacts(request) {
          calls.listings.push(request);
          return { data: { total_count: pages.flat().length, artifacts: pages[request.page - 1] ?? [] } };
        },
      },
      repos: {
        async getContent(request) {
          calls.reads.push(request);
          return { data: file };
        },
        async createOrUpdateFileContents(request) {
          calls.writes.push(request);
          if (options.writeError) throw options.writeError;
          return { data: { content: { sha: 'new-sha' } } };
        },
      },
    },
  };
  return { calls, context, github, core: { info() {} } };
}

async function invoke(input) {
  const update = require('../.github/scripts/update-download-link.cjs');
  return update(input);
}

test('publica o download direto e preserva todo o texto fora do bloco marcado', async () => {
  const input = fixture();
  await invoke(input);
  assert.equal(input.calls.writes.length, 1);
  const request = input.calls.writes[0];
  const updated = Buffer.from(request.content, 'base64').toString('utf8');
  assert.ok(updated.startsWith(`${prefix}${start}`));
  assert.ok(updated.endsWith(`${end}${suffix}`));
  assert.ok(updated.includes(`](${url})`));
  assert.ok(!updated.includes('Link anterior'));
  assert.equal(request.sha, 'abcdef1234567890abcdef1234567890abcdef1234');
  assert.equal(request.branch, 'main');
  assert.equal(request.path, 'README.md');
  assert.equal(request.owner, 'NGK-999');
  assert.equal(request.repo, 'InterfaceNeural');
  assert.ok(request.message.includes('[skip ci]'));
  assert.deepEqual(input.calls.reads, [{ owner: 'NGK-999', repo: 'InterfaceNeural', path: 'README.md', ref: 'main' }]);
});

test('encontra o instalador na segunda página dos artefatos da execução atual', async () => {
  const first = Array.from({ length: 100 }, (_, i) => ({ id: i + 1, name: `outro-${i}`, expired: false }));
  const input = fixture({ pages: [first, [{ id: 456, name: artifactName, expired: false }]] });
  await invoke(input);
  assert.deepEqual(input.calls.listings.map((request) => [request.run_id, request.page, request.per_page]), [[123, 1, 100], [123, 2, 100]]);
  assert.ok(Buffer.from(input.calls.writes[0].content, 'base64').toString('utf8').includes(url));
});

for (const [name, artifacts, error] of [
  ['ausente', [], /artefato.*encontrado/i],
  ['expirado', [{ id: 456, name: artifactName, expired: true }], /expirado|inválido/i],
  ['id inválido', [{ id: 0, name: artifactName, expired: false }], /inválido/i],
  ['id não inteiro', [{ id: 4.5, name: artifactName, expired: false }], /inválido/i],
  ['validade desconhecida', [{ id: 456, name: artifactName }], /inválido/i],
  ['duplicado', [{ id: 456, name: artifactName, expired: false }, { id: 789, name: artifactName, expired: false }], /ambíguo|duplicado/i],
]) {
  test(`não publica quando o artefato está ${name}`, async () => {
    const input = fixture({ pages: [artifacts] });
    await assert.rejects(invoke(input), error);
    assert.equal(input.calls.writes.length, 0);
  });
}

for (const [name, document] of [
  ['ausentes', '# Projeto sem marcadores'],
  ['início duplicado', `${start}${start}${end}`],
  ['fim duplicado', `${start}${end}${end}`],
  ['invertidos', `${end}conteúdo${start}`],
]) {
  test(`não altera o README com marcadores ${name}`, async () => {
    const input = fixture({ readme: document });
    await assert.rejects(invoke(input), /marcadores/i);
    assert.equal(input.calls.writes.length, 0);
  });
}

test('não cria commit quando o link e as instruções já estão atualizados', async () => {
  const first = fixture();
  await invoke(first);
  const second = fixture({ readme: Buffer.from(first.calls.writes[0].content, 'base64').toString('utf8') });
  await invoke(second);
  assert.equal(second.calls.writes.length, 0);
});

test('execução antiga preserva o link já publicado por uma execução mais nova', async () => {
  const newerReadme = `${prefix}${start}\n<!-- windows-installer-run:4 -->\n[Download novo](https://github.com/NGK-999/InterfaceNeural/actions/runs/124/artifacts/457)\n${end}${suffix}`;
  const input = fixture({ readme: newerReadme });
  const result = await invoke(input);
  assert.equal(input.calls.writes.length, 0);
  assert.equal(result.changed, false);
  assert.equal(result.downloadUrl, url);
  assert.equal(result.artifactId, 456);
});

test('execução mais nova substitui o link antigo e registra seu número dentro do bloco', async () => {
  const olderReadme = `${prefix}<!-- windows-installer-run:99 -->\r\n${start}\r\n<!-- windows-installer-run:3 -->\r\n[Download antigo](https://github.com/NGK-999/InterfaceNeural/actions/runs/122/artifacts/455)\r\n${end}${suffix}`;
  const input = fixture({ readme: olderReadme, context: { runNumber: 4 } });
  await invoke(input);
  assert.equal(input.calls.writes.length, 1);
  const updated = Buffer.from(input.calls.writes[0].content, 'base64').toString('utf8');
  assert.ok(updated.startsWith(`${prefix}<!-- windows-installer-run:99 -->\r\n${start}`));
  assert.ok(updated.endsWith(`${end}${suffix}`));
  assert.ok(updated.includes('<!-- windows-installer-run:4 -->'));
  assert.ok(updated.includes(url));
  assert.ok(!updated.includes('<!-- windows-installer-run:3 -->'));
});

test('reexecução do mesmo número pode atualizar o artefato publicado', async () => {
  const input = fixture({ readme: `${prefix}${start}\n<!-- windows-installer-run:3 -->\n[Download anterior](https://github.com/NGK-999/InterfaceNeural/actions/runs/123/artifacts/455)\n${end}${suffix}` });
  await invoke(input);
  assert.equal(input.calls.writes.length, 1);
  assert.ok(Buffer.from(input.calls.writes[0].content, 'base64').toString('utf8').includes(url));
});

for (const [name, metadata] of [
  ['duplicado', '<!-- windows-installer-run:3 --><!-- windows-installer-run:4 -->'],
  ['não inteiro', '<!-- windows-installer-run:3.5 -->'],
  ['inválido', '<!-- windows-installer-run:0 -->'],
]) {
  test(`não publica com número de execução ${name} no bloco`, async () => {
    const input = fixture({ readme: `${prefix}${start}\n${metadata}\n${end}${suffix}` });
    await assert.rejects(invoke(input), /número.*execução|execução.*número/i);
    assert.equal(input.calls.writes.length, 0);
  });
}

test('rejeita contexto sem número de execução inteiro positivo', async () => {
  const input = fixture({ context: { runNumber: 0 } });
  await assert.rejects(invoke(input), /execução/i);
  assert.equal(input.calls.writes.length, 0);
});

test('preserva o BOM UTF-8 existente antes do primeiro marcador', async () => {
  const input = fixture({ readme: `\uFEFF${readme}` });
  await invoke(input);
  const bytes = Buffer.from(input.calls.writes[0].content, 'base64');
  assert.deepEqual([...bytes.subarray(0, 3)], [0xef, 0xbb, 0xbf]);
  assert.ok(bytes.toString('utf8').startsWith(`\uFEFF${prefix}${start}`));
});

test('aborta se o conteúdo do README não for um arquivo UTF-8 em base64', async () => {
  const input = fixture({ file: { type: 'file', encoding: 'base64', sha: 'original-sha', content: Buffer.from([0xff]).toString('base64') } });
  await assert.rejects(invoke(input), /UTF-8|codificação/i);
  assert.equal(input.calls.writes.length, 0);
});

test('rejeita contexto que produziria um link para outro servidor', async () => {
  const input = fixture({ context: { serverUrl: 'https://github.com.evil.example' } });
  await assert.rejects(invoke(input), /servidor/i);
  assert.equal(input.calls.writes.length, 0);
});

test('preserva conflito de SHA para evitar sobrescrever uma edição concorrente', async () => {
  const conflict = Object.assign(new Error('SHA mudou'), { status: 409 });
  const input = fixture({ writeError: conflict });
  await assert.rejects(invoke(input), (error) => error === conflict);
  assert.equal(input.calls.writes.length, 1);
  assert.equal(input.calls.writes[0].sha, 'abcdef1234567890abcdef1234567890abcdef1234');
});
