// Atualiza apenas o bloco de download do README, depois das verificações da CI.
const { TextDecoder } = require('node:util');

const startMarker = '<!-- windows-installer-download:start -->';
const endMarker = '<!-- windows-installer-download:end -->';
const runMarker = '<!-- windows-installer-run:';
const artifactName = 'MonitorMuscular-Instalador-Windows-x86_64';

module.exports = async ({ github, context, core }) => {
  const { owner, repo } = context.repo;
  if (![owner, repo].every((value) => typeof value === 'string' && /^[A-Za-z0-9][A-Za-z0-9_.-]*$/.test(value))) {
    throw new Error('Repositório inválido no contexto da CI.');
  }
  const runId = context.runId;
  if (!Number.isSafeInteger(runId) || runId <= 0) {
    throw new Error('Execução inválida no contexto da CI.');
  }
  const runNumber = context.runNumber;
  if (!Number.isSafeInteger(runNumber) || runNumber <= 0) {
    throw new Error('Número de execução inválido no contexto da CI.');
  }
  const server = new URL(context.serverUrl || process.env.GITHUB_SERVER_URL || 'https://github.com');
  if (server.origin !== 'https://github.com' || server.pathname !== '/' || server.search || server.hash || server.username || server.password) {
    throw new Error('Servidor inválido: o download deve usar github.com.');
  }

  const candidates = [];
  for (let page = 1; ; page += 1) {
    const response = await github.rest.actions.listWorkflowRunArtifacts({
      owner, repo, run_id: runId, per_page: 100, page,
    });
    const artifacts = response.data.artifacts;
    if (!Array.isArray(artifacts)) throw new Error('Resposta de artefatos inválida.');
    candidates.push(...artifacts.filter((artifact) => artifact.name === artifactName));
    if (artifacts.length < 100) break;
  }
  if (candidates.length === 0) throw new Error('Artefato do instalador não encontrado nesta execução.');
  if (candidates.length !== 1) throw new Error('Artefato do instalador ambíguo: nomes duplicados.');
  const artifact = candidates[0];
  if (artifact.expired !== false || !Number.isSafeInteger(artifact.id) || artifact.id <= 0) {
    throw new Error('Artefato do instalador expirado ou inválido.');
  }
  const downloadUrl = `${server.origin}/${owner}/${repo}/actions/runs/${runId}/artifacts/${artifact.id}`;

  const response = await github.rest.repos.getContent({ owner, repo, path: 'README.md', ref: 'main' });
  const file = response.data;
  if (!file || Array.isArray(file) || file.type !== 'file' || file.encoding !== 'base64' || typeof file.content !== 'string' || typeof file.sha !== 'string' || !file.sha) {
    throw new Error('README.md não é um arquivo com codificação base64 e SHA válidos.');
  }
  let readme;
  try {
    const base64 = file.content.replace(/[\r\n]/g, '');
    if (!/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(base64)) {
      throw new Error('Base64 inválido.');
    }
    readme = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(Buffer.from(base64, 'base64'));
  } catch {
    throw new Error('README.md tem codificação base64 ou UTF-8 inválida.');
  }
  if (readme.split(startMarker).length !== 2 || readme.split(endMarker).length !== 2) {
    throw new Error('README.md deve conter um único par de marcadores do download.');
  }
  const start = readme.indexOf(startMarker) + startMarker.length;
  const end = readme.indexOf(endMarker);
  if (end < start) throw new Error('Marcadores do download estão fora de ordem.');
  const previousInterior = readme.slice(start, end);
  const runMarkers = previousInterior.split(runMarker).length - 1;
  if (runMarkers > 1) throw new Error('Número de execução duplicado no bloco de download.');
  if (runMarkers === 1) {
    const metadata = previousInterior.slice(previousInterior.indexOf(runMarker));
    const match = /^<!-- windows-installer-run:([1-9][0-9]*) -->/.exec(metadata);
    const previousRunNumber = match ? Number(match[1]) : NaN;
    if (!Number.isSafeInteger(previousRunNumber)) {
      throw new Error('Número de execução inválido no bloco de download.');
    }
    // runNumber cresce por workflow; este helper pertence somente a ci.yml.
    if (previousRunNumber > runNumber) {
      core.info('Uma execução mais nova já publicou seu instalador; README preservado.');
      return { changed: false, downloadUrl, artifactId: artifact.id };
    }
  }
  const newline = readme.includes('\r\n') ? '\r\n' : '\n';
  const interior = [
    '', '',
    `<!-- windows-installer-run:${runNumber} -->`,
    '',
    `[**Baixar instalador Windows (.zip)**](${downloadUrl})`,
    '',
    'Extraia o ZIP e abra `MonitorMuscular-Instalar.exe`.',
    '', '',
  ].join(newline);
  const updated = readme.slice(0, start) + interior + readme.slice(end);
  if (updated === readme) {
    core.info('O link do instalador já está atualizado; nenhum commit criado.');
    return { changed: false, downloadUrl, artifactId: artifact.id };
  }
  await github.rest.repos.createOrUpdateFileContents({
    owner, repo, path: 'README.md', branch: 'main', sha: file.sha,
    message: 'docs: atualizar download do instalador Windows [skip ci]',
    content: Buffer.from(updated, 'utf8').toString('base64'),
  });
  core.info(`Link do instalador atualizado: ${downloadUrl}`);
  return { changed: true, downloadUrl, artifactId: artifact.id };
};
