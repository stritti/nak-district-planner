// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

'use strict';

const CI_TAG = /^(?:main|develop|sha-[0-9a-f]{7,40})$/;

function isCandidate(version) {
  const tags = version.metadata?.container?.tags;
  return Array.isArray(tags) && tags.length > 0 &&
    tags.every((tag) => typeof tag === 'string' && CI_TAG.test(tag));
}

async function cleanup({ request, owner, repository, mode, log }) {
  if (!['preview', 'delete'].includes(mode)) throw new Error('Invalid cleanup mode');
  // Enumerate BOTH packages completely before starting any deletion.
  const plans = [];
  for (const service of ['backend', 'frontend']) {
    const packageName = repository + '/' + service;
    const endpoint = '/users/' + encodeURIComponent(owner) +
      '/packages/container/' + encodeURIComponent(packageName) + '/versions';
    const versions = [];
    for (let page = 1; ; page += 1) {
      const batch = await request('GET', endpoint + '?per_page=100&page=' + page);
      if (!Array.isArray(batch)) throw new Error('Invalid package response');
      versions.push(...batch);
      if (batch.length < 100) break;
    }
    const protectedDigests = new Set(versions.filter((v) => !isCandidate(v)).map((v) => v.name));
    const candidates = versions.filter((v) => isCandidate(v) && !protectedDigests.has(v.name));
    plans.push({ packageName, endpoint, candidates });
    log(packageName + ': ' + candidates.length + ' candidates; ' +
      (versions.length - candidates.length) + ' protected versions');
    for (const version of candidates) {
      if (!Number.isSafeInteger(version.id) || version.id <= 0) throw new Error('Invalid version ID');
      log(JSON.stringify({ package: packageName, id: version.id,
        digest: version.name, tags: version.metadata.container.tags }));
    }
  }

  let deleted = 0;
  if (mode === 'delete') {
    for (const plan of plans) {
      for (const candidate of plan.candidates) {
        const endpoint = plan.endpoint + '/' + candidate.id;
        // Re-read immediately before deletion: a new release tag protects the version.
        const current = await request('GET', endpoint);
        if (current.id !== candidate.id || current.name !== candidate.name || !isCandidate(current)) {
          log('Protected after recheck: ' + plan.packageName + ' version ' + candidate.id);
          continue;
        }
        await request('DELETE', endpoint);
        deleted += 1;
        log('Deleted: ' + plan.packageName + ' version ' + candidate.id);
      }
    }
  }
  return { candidates: plans.reduce((total, plan) => total + plan.candidates.length, 0), deleted };
}

async function main() {
  const { GITHUB_TOKEN, GITHUB_REPOSITORY, CLEANUP_MODE, GITHUB_STEP_SUMMARY } = process.env;
  if (!GITHUB_TOKEN) throw new Error('GITHUB_TOKEN is required');
  if (GITHUB_REPOSITORY !== 'stritti/nak-district-planner') throw new Error('Unexpected repository');
  const [owner, repository] = GITHUB_REPOSITORY.split('/');
  async function request(method, endpoint) {
    const response = await fetch('https://api.github.com' + endpoint, {
      method,
      headers: {
        Authorization: 'Bearer ' + GITHUB_TOKEN,
        Accept: 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28'
      }
    });
    if (!response.ok) throw new Error(method + ' ' + endpoint + ': HTTP ' + response.status);
    return response.status === 204 ? undefined : response.json();
  }
  const lines = [];
  const result = await cleanup({
    request, owner, repository, mode: CLEANUP_MODE,
    log: (line) => { console.log(line); lines.push(line); }
  });
  if (GITHUB_STEP_SUMMARY) {
    await require('node:fs/promises').appendFile(GITHUB_STEP_SUMMARY,
      '# Container cleanup: ' + CLEANUP_MODE + '\n\nCandidates: ' + result.candidates +
      '; deleted: ' + result.deleted + '\n\n\`\`\`text\n' + lines.join('\n') + '\n\`\`\`\n');
  }
}

module.exports = { isCandidate, cleanup };
if (require.main === module) {
  main().catch((error) => { console.error(error.message); process.exitCode = 1; });
}
