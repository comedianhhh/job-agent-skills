#!/usr/bin/env node
// Pre-publish verification for job-agent-skills: check exactly what `npm publish` would ship.
//
//   npm run verify                 ~2 min: offline checks + pack + packaged jobs-mcp + live board smoke
//   npm run verify -- --release    + skill evals (~10 min of model calls on the claude CLI login); required to publish
//   npm run verify -- --all        also the parts that don't ship to npm (graph/, web/api)
//   npm run verify -- --evals-json <file>   re-score a saved eval result instead of running the model again
//
// Evals gate only on deterministic graders (regex / tool_used / file_exists). llm-judge graders are
// reported as NOTE: a single smoke run of a small judge is too noisy to block a release.
//
// Verdict: PASS (with --release: publish .verify/<run>/<tarball> with `npm publish <tarball>`), FAIL (a check failed),
// BLOCKED (a check could not run: no network, a board gone, a tool missing). Never publish on FAIL or BLOCKED.
// Evidence: .verify/<run>/ (gitignored) — summary.md, results.json, logs/, the tarball and its sha256.
// Exit codes: 0 PASS, 1 FAIL, 2 BLOCKED, 3 cleanup incomplete.

import { spawnSync, execSync } from 'node:child_process';
import { mkdirSync, writeFileSync, readFileSync, rmSync, existsSync, readdirSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const WIN = process.platform === 'win32';
const ALL = process.argv.includes('--all');
const RELEASE = process.argv.includes('--release');
const EVALS_JSON = (() => { const i = process.argv.indexOf('--evals-json'); return i > 0 ? process.argv[i + 1] : null; })();
const RUN = new Date().toISOString().replace(/[-:]/g, '').replace(/\..+/, '').replace('T', '-');
const DIR = join(ROOT, '.verify', RUN), LOGS = join(DIR, 'logs'), PKG = join(DIR, 'pkg');
mkdirSync(LOGS, { recursive: true });

// Live smoke targets: public boards that are large and stable. If one disappears, the Doctor
// reports BLOCKED ("target gone") and the fix is to pick another board here, not to change jobs-mcp.
const LIVE_BOARDS = [
  { spec: 'greenhouse:anthropic', probe: 'https://boards-api.greenhouse.io/v1/boards/anthropic/jobs' },
  { spec: 'lever:spotify', probe: 'https://api.lever.co/v0/postings/spotify?mode=json&limit=1' },
  { spec: 'ashby:cohere', probe: 'https://api.ashbyhq.com/posting-api/job-board/cohere' },
  { spec: 'smartrecruiters:Ubisoft2', probe: 'https://api.smartrecruiters.com/v1/companies/Ubisoft2/postings?limit=1' },
];
const EXPECTED_TOOLS = ['get_job', 'linkedin_search', 'list_board_jobs', 'scan'];

const results = [];
const meta = { run: RUN, startedAt: new Date().toISOString(), all: ALL };

// status: PASS | FAIL | BLOCKED
function record(stage, name, status, detail = {}) {
  results.push({ stage, name, status, ...detail });
  const tag = status.padEnd(7);
  const extra = status === 'PASS' ? (detail.note ? '  (' + detail.note + ')' : '') : '  -> ' + (detail.why || detail.log || '');
  console.log(`${tag} [${stage}] ${name}${extra}`);
}

// Run one command (all command strings are fixed in this file), log its output, record PASS/FAIL.
// A missing tool (exit 127 / "not recognized") is BLOCKED, not FAIL: the check never ran.
function run(stage, name, cmd, cwd = ROOT) {
  const slug = `${stage}-${name}`.replace(/[^a-z0-9]+/gi, '-').toLowerCase();
  const t0 = Date.now();
  const r = spawnSync(cmd, { cwd, shell: true, encoding: 'utf8', maxBuffer: 64 << 20, env: { ...process.env, PYTHONIOENCODING: 'utf-8' } });
  const out = `$ ${cmd}\n(cwd ${cwd})\n\n${r.stdout || ''}${r.stderr || ''}\nexit ${r.status}\n`;
  writeFileSync(join(LOGS, slug + '.log'), out);
  const missing = r.status === 127 || /is not recognized as an internal or external command|command not found/.test(r.stderr || '');
  const status = r.status === 0 ? 'PASS' : missing ? 'BLOCKED' : 'FAIL';
  record(stage, name, status, { cmd, exit: r.status, ms: Date.now() - t0, log: `logs/${slug}.log`, why: status === 'PASS' ? undefined : lastLines(out) });
  return r;
}
const lastLines = (s, n = 4) => s.trim().split('\n').slice(-n).join(' | ').slice(0, 300);
const sh = (cmd) => execSync(cmd, { cwd: ROOT, encoding: 'utf8' }).trim();

// ---------- base ----------
meta.commit = sh('git rev-parse HEAD');
meta.branch = sh('git rev-parse --abbrev-ref HEAD');
meta.dirty = sh('git status --short') || '(clean)';
meta.version = JSON.parse(readFileSync(join(ROOT, 'package.json'), 'utf8')).version;
meta.tools = { node: process.version };
for (const [k, c] of [['uv', 'uv --version'], ['python', 'python --version']]) {
  try { meta.tools[k] = sh(c); } catch { meta.tools[k] = 'missing'; }
}

// ---------- launch: dependencies ----------
if (!existsSync(join(ROOT, 'node_modules', '@modelcontextprotocol', 'sdk'))) run('launch', 'npm ci', 'npm ci');
for (const dir of ['mcp/jobs-mcp', ...(ALL ? ['graph'] : [])]) {
  if (!existsSync(join(ROOT, dir, '.venv'))) run('launch', `${dir} venv`, 'uv venv && uv pip install -e ".[dev]"', join(ROOT, dir));
}
if (ALL && !existsSync(join(ROOT, 'web/api/.venv'))) run('launch', 'web/api sync', 'uv sync --extra dev', join(ROOT, 'web/api'));

// ---------- offline: the same checks CI runs, for the parts that ship ----------
run('offline', 'eval cases validate', 'python evals/validate.py');
for (const t of ['test_check_trace', 'test_career_eval', 'test_check_ats', 'test_rank_cuts']) run('offline', t, `python scripts/${t}.py`);
const MCP = join(ROOT, 'mcp/jobs-mcp');
run('offline', 'jobs-mcp ruff check', 'uv run --no-project ruff check .', MCP);
run('offline', 'jobs-mcp ruff format', 'uv run --no-project ruff format --check .', MCP);
run('offline', 'jobs-mcp pytest', 'uv run --no-project pytest -q', MCP);
run('offline', 'extension typecheck', 'npm run check');
run('offline', 'extension load (pi)', 'npm run test:pi');
if (ALL) {
  const G = join(ROOT, 'graph'), A = join(ROOT, 'web/api');
  run('offline', 'graph ruff', 'uv run --no-project ruff check . && uv run --no-project ruff format --check .', G);
  run('offline', 'graph pytest', 'uv run --no-project pytest -q', G);
  run('offline', 'tracker-api ruff', 'uv run ruff check . && uv run ruff format --check .', A);
  run('offline', 'tracker-api pytest', 'uv run pytest -q', A);
}

// ---------- pack: what npm would publish ----------
mkdirSync(PKG, { recursive: true });
const packed = run('pack', 'npm pack', `npm pack --json --pack-destination "${DIR}"`);
let files = [];
if (packed.status === 0) {
  const info = JSON.parse(packed.stdout.slice(packed.stdout.indexOf('[')))[0];
  meta.tarball = info.filename;
  meta.sha256 = createHash('sha256').update(readFileSync(join(DIR, info.filename))).digest('hex');
  files = info.files.map((f) => f.path);
  writeFileSync(join(DIR, 'files.txt'), files.join('\n') + '\n');

  const skills = readdirSync(join(ROOT, 'skills')).filter((d) => existsSync(join(ROOT, 'skills', d, 'SKILL.md')));
  const required = [...skills.map((s) => `skills/${s}/SKILL.md`), 'extensions/jobs-mcp.ts', 'agents/application-reviewer.md',
    'mcp/jobs-mcp/pyproject.toml', 'mcp/jobs-mcp/jobs_mcp/server.py', 'scripts/check-trace.py', 'scripts/check-ats.py', 'README.md', 'LICENSE'];
  const missing = required.filter((f) => !files.includes(f));
  record('pack', `required files present (${required.length})`, missing.length ? 'FAIL' : 'PASS', { why: missing.join(', ') });

  // nothing private or bulky: the user's career workspace, secrets, caches, eval fixtures, PDFs, local settings
  const FORBIDDEN = [/^career\//, /(^|\/)\.env/, /__pycache__/, /\.pyc$/, /^evals\//, /\.pdf$/i, /^\.claude\//, /^\.verify\//, /^web\//, /^graph\//, /\.venv\//];
  const leaked = files.filter((f) => FORBIDDEN.some((re) => re.test(f)));
  record('pack', 'no private, cache or dev-only files', leaked.length ? 'FAIL' : 'PASS', { why: leaked.slice(0, 10).join(', ') });

  const size = info.size;
  meta.packSize = size; meta.fileCount = files.length;
  record('pack', `tarball under 2 MB (${(size / 1024).toFixed(0)} KB, ${files.length} files)`, size < 2 << 20 ? 'PASS' : 'FAIL', { why: `${size} bytes` });

  // relative paths: GNU tar on Windows reads "C:\..." as a remote host
  const unpacked = run('pack', 'unpack tarball', `tar -xzf "${info.filename}" -C pkg`, DIR);

  // The skill evals run against the repo (the tarball has no evals/ or plugin manifest), so prove the
  // shipped skills, agents, extension and scripts are byte-for-byte the files being evaluated.
  if (unpacked.status === 0) {
    const sha = (p) => createHash('sha256').update(readFileSync(p)).digest('hex');
    const shipped = files.filter((f) => /^(skills|agents|extensions|scripts|templates)\//.test(f));
    const differ = shipped.filter((f) => !existsSync(join(ROOT, f)) || sha(join(ROOT, f)) !== sha(join(PKG, 'package', f)));
    record('pack', `shipped skills/agents/scripts identical to the evaluated tree (${shipped.length} files)`, differ.length ? 'FAIL' : 'PASS', { why: differ.slice(0, 5).join(', ') });
  }
}

// ---------- doctor + drive: start jobs-mcp from the unpacked package, the way the plugin does ----------
const SERVER_DIR = join(PKG, 'package', 'mcp', 'jobs-mcp');
let client = null;
async function liveStage() {
  if (!existsSync(join(SERVER_DIR, 'pyproject.toml'))) { record('mcp', 'packaged jobs-mcp present', 'BLOCKED', { why: 'pack step failed' }); return; }
  const { Client } = await import('@modelcontextprotocol/sdk/client/index.js');
  const { StdioClientTransport } = await import('@modelcontextprotocol/sdk/client/stdio.js');
  const transport = new StdioClientTransport({ command: 'uvx', args: ['--from', SERVER_DIR, 'jobs-mcp'], stderr: 'pipe' });
  let stderr = '';
  transport.stderr?.on('data', (d) => { stderr += d; });
  client = new Client({ name: 'verify', version: '1' });
  try {
    await withTimeout(client.connect(transport), 120_000, 'connect');
  } catch (e) {
    writeFileSync(join(LOGS, 'mcp-start.log'), stderr);
    record('mcp', 'packaged jobs-mcp starts over stdio', 'FAIL', { why: String(e.message), log: 'logs/mcp-start.log' });
    return;
  }
  record('mcp', 'packaged jobs-mcp starts over stdio', 'PASS');
  const names = (await client.listTools()).tools.map((t) => t.name).sort();
  record('mcp', 'exposes exactly the four tools', JSON.stringify(names) === JSON.stringify(EXPECTED_TOOLS) ? 'PASS' : 'FAIL', { why: names.join(',') });

  const call = async (name, args) => {
    const r = await withTimeout(client.callTool({ name, arguments: args }), 90_000, name);
    return JSON.parse(r.content[0].text);
  };
  const calls = [];

  for (const b of LIVE_BOARDS) {
    // Doctor: can we reach the board at all? If not, jobs-mcp can't be judged on it -> BLOCKED.
    const probe = await fetchStatus(b.probe);
    if (probe !== 200) {
      record('live', `${b.spec} reachable`, 'BLOCKED', { why: probe === 404 ? 'target gone: pick another board in LIVE_BOARDS' : `probe ${probe}` });
      continue;
    }
    const list = await call('list_board_jobs', { board: b.spec, limit: 5 });
    calls.push({ tool: 'list_board_jobs', board: b.spec, ok: list.ok, count: list.count, error: list.error, first: list.items?.[0] });
    if (!list.ok) {
      const blocked = list.error?.retryable || list.error?.code === 'RATE_LIMITED';
      record('live', `${b.spec} list_board_jobs`, blocked ? 'BLOCKED' : 'FAIL', { why: JSON.stringify(list.error) });
      continue;
    }
    const item = list.items?.[0] || {};
    const shapeOk = list.count > 0 && ['source', 'board', 'id', 'title', 'company', 'url'].every((k) => item[k]);
    record('live', `${b.spec} list_board_jobs (${list.count} jobs, item shape)`, shapeOk ? 'PASS' : 'FAIL', { why: JSON.stringify(item).slice(0, 200) });
    if (!shapeOk) continue;

    const job = await call('get_job', { board: b.spec, job_id: String(item.id) });
    const j = job.items?.[0] || {};
    calls.push({ tool: 'get_job', board: b.spec, id: item.id, ok: job.ok, error: job.error, descLen: (j.description || '').length, integrity: j.integrity });
    const descOk = job.ok && (j.description || '').length > 50 && j.integrity !== undefined;
    record('live', `${b.spec} get_job (description + posting guard)`, descOk ? 'PASS' : job.error?.retryable ? 'BLOCKED' : 'FAIL',
      { why: job.ok ? `desc ${(j.description || '').length} chars, integrity ${JSON.stringify(j.integrity)}` : JSON.stringify(job.error) });
  }

  // LinkedIn guest search is rate-limited by design: anything but a clean answer is BLOCKED, never FAIL
  const li = await call('linkedin_search', { keywords: 'software engineer', location: 'Toronto', limit: 3 });
  calls.push({ tool: 'linkedin_search', ok: li.ok, count: li.count, error: li.error });
  record('live', `linkedin_search${li.ok ? ` (${li.count} jobs)` : ''}`, li.ok && li.count > 0 ? 'PASS' : li.ok || !['BAD_INPUT'].includes(li.error?.code) ? 'BLOCKED' : 'FAIL',
    { why: li.ok ? 'no results' : JSON.stringify(li.error) });

  writeFileSync(join(LOGS, 'live-calls.json'), JSON.stringify(calls, null, 2));
  writeFileSync(join(LOGS, 'mcp-stderr.log'), stderr);
}

function withTimeout(p, ms, what) {
  return Promise.race([p, new Promise((_, rej) => setTimeout(() => rej(new Error(`${what} timed out after ${ms / 1000}s`)), ms))]);
}
// two tries, 20 s each: one slow answer from a board is common and says nothing about jobs-mcp
async function fetchStatus(url) {
  let last;
  for (let i = 0; i < 2; i++) {
    try { const r = await fetch(url, { signal: AbortSignal.timeout(20_000) }); if (r.status < 500) return r.status; last = r.status; }
    catch (e) { last = `unreachable (${e.cause?.code || e.name})`; }
  }
  return last;
}

try { await liveStage(); } catch (e) { record('live', 'live stage crashed', 'FAIL', { why: String(e.stack || e).slice(0, 300) }); }

// ---------- cleanup ----------
try { await client?.close(); } catch { }
await new Promise((r) => setTimeout(r, 1000));
const leftovers = runPids();          // anything still running from the unpacked package is a cleanup bug
for (const pid of leftovers) { try { execSync(`taskkill /pid ${pid} /T /F`, { stdio: 'ignore' }); } catch { } }
let pkgGone = false;
for (let i = 0; i < 10 && !pkgGone; i++) {
  try { rmSync(PKG, { recursive: true, force: true }); pkgGone = true; } catch { await new Promise((r) => setTimeout(r, 500)); }
}
const stillLeft = runPids().length;
meta.cleanup = { killedAfterClose: leftovers.length, stillLeft, unpackedRemoved: pkgGone };

// The marker reaches PowerShell through an env var so the query never matches its own command line.
function runPids() {
  if (!WIN) { try { return execSync(`pgrep -f -- '.verify/${RUN}'`, { encoding: 'utf8' }).split(/\s+/).filter(Boolean); } catch { return []; } }
  const ps = 'Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine.Contains($env:VERIFY_MARK) } | ForEach-Object { $_.ProcessId }';
  return execSync(`powershell -NoProfile -Command "${ps}"`, { encoding: 'utf8', env: { ...process.env, VERIFY_MARK: `.verify\\${RUN}` } })
    .split(/\s+/).filter(Boolean).map(Number).filter((p) => p !== process.pid);
}

// ---------- skill evals: real model calls through the logged-in claude CLI ----------
// Smoke mode (1 run per case, plugin arm only). A case passes when its deterministic graders pass;
// llm-judge failures become NOTEs. Cases in evals/baseline.json are KNOWN. A new deterministic failure
// is re-run once (the agent itself is nondeterministic); failing twice is a FAIL.
async function evalsStage() {
  if (!RELEASE && !EVALS_JSON) return;
  if (results.some((r) => r.status === 'FAIL')) { record('evals', 'skill evals', 'BLOCKED', { why: 'skipped: an earlier check already FAILED' }); return; }
  const baseline = JSON.parse(readFileSync(join(ROOT, 'evals', 'baseline.json'), 'utf8')).knownFailing || {};

  // gate on deterministic graders only; collect llm-judge failures as notes
  const caseResult = (c) => {
    const types = Object.fromEntries((c.graders || []).map((g) => [g.name, g.type]));
    const runs = c.arms?.with || [];
    const err = runs.find((x) => x.error)?.error;
    const bad = (llm) => [...new Set(runs.flatMap((x) => (x.graders || [])
      .filter((g) => g.scored && !g.passed && (types[g.name] === 'llm') === llm)
      .map((g) => `${g.name}: ${String(g.explanation || '').slice(0, 60)}`)))];
    return { err, failed: bad(false), judge: bad(true), passed: runs.length > 0 && bad(false).length === 0 };
  };
  const judgeNote = (r) => (r.judge.length ? { note: `judge (report only): ${r.judge.join('; ')}` } : {});

  if (EVALS_JSON) {   // re-score a saved result: no model calls, no reruns
    const saved = JSON.parse(readFileSync(EVALS_JSON, 'utf8'));
    meta.evals = { cases: saved.cases.length, costUsd: 0, durationSeconds: 0, reruns: [], rescored: EVALS_JSON };
    for (const c of saved.cases) {
      const r = caseResult(c);
      if (r.err) record('evals', c.name, 'BLOCKED', { why: `run error: ${String(r.err).slice(0, 150)}` });
      else if (r.passed) record('evals', c.name, r.judge.length ? 'NOTE' : 'PASS', { ...judgeNote(r), why: r.judge.join('; '), ...(baseline[c.name] ? { note: 'listed in evals/baseline.json but passes now: remove it' } : {}) });
      else if (baseline[c.name]) record('evals', c.name, 'KNOWN', { why: `baseline: ${baseline[c.name]}`.slice(0, 160) });
      else record('evals', c.name, 'FAIL', { why: r.failed.join('; ').slice(0, 300) });
    }
    return;
  }

  const bash = gitBash();
  if (!bash) { record('evals', 'skill evals', 'BLOCKED', { why: 'Git Bash not found (the bash on PATH may be WSL)' }); return; }
  const env = { ...process.env };
  delete env.ANTHROPIC_API_KEY;              // use the CLI's claude.ai login, never a billed key
  const auth = spawnSync('claude auth status', { shell: true, encoding: 'utf8', env });
  if (!/"loggedIn":\s*true/.test(auth.stdout || '')) { record('evals', 'claude CLI logged in', 'BLOCKED', { why: 'run `claude auth login`' }); return; }
  meta.claude = spawnSync('claude --version', { shell: true, encoding: 'utf8' }).stdout.trim();

  const evalRun = (extra, slug) => {
    const out = join(DIR, `${slug}.json`);
    const t0 = Date.now();
    const r = spawnSync(`"${bash}" evals/run.sh --smoke ${extra} --json "${out}"`,
      { cwd: ROOT, shell: true, encoding: 'utf8', env, maxBuffer: 256 << 20, timeout: 90 * 60_000 });
    writeFileSync(join(LOGS, `${slug}.log`), `${r.stdout || ''}${r.stderr || ''}\nexit ${r.status}\n`);
    console.log(`        [evals] ${slug}: exit ${r.status}, ${((Date.now() - t0) / 60000).toFixed(1)} min`);
    return existsSync(out) ? JSON.parse(readFileSync(out, 'utf8')) : null;
  };
  console.log('        [evals] running the smoke suite through the claude CLI (10-20 min)…');
  const first = evalRun('-j 3', 'evals');
  if (!first || first.partial) { record('evals', 'smoke suite ran', 'BLOCKED', { why: first ? 'partial result (cost ceiling or abort)' : 'no result JSON', log: 'logs/evals.log' }); return; }
  meta.evals = { cases: first.cases.length, costUsd: first.costUsd, durationSeconds: first.durationSeconds, reruns: [] };
  record('evals', `smoke suite ran (${first.cases.length} cases, ≈$${first.costUsd.toFixed(2)}, ${Math.round(first.durationSeconds / 60)} min)`, 'PASS', { log: 'logs/evals.log' });

  for (const c of first.cases) {
    const r = caseResult(c);
    const name = `${c.name}`;
    if (r.err) { record('evals', name, 'BLOCKED', { why: `run error: ${String(r.err).slice(0, 150)}` }); continue; }
    if (r.passed) {
      record('evals', name, r.judge.length ? 'NOTE' : 'PASS', { ...judgeNote(r), why: r.judge.join('; '), ...(baseline[name] ? { note: 'listed in evals/baseline.json but passes now: remove it' } : {}) });
      continue;
    }
    if (baseline[name]) { record('evals', name, 'KNOWN', { why: `baseline: ${baseline[name]}`.slice(0, 160) }); continue; }
    // new failure: one rerun before calling it a regression
    const again = evalRun(`--case "${name}"`, `evals-rerun-${name}`);
    const rc = again?.cases?.find((x) => x.name === name);
    meta.evals.reruns.push(name);
    if (rc && caseResult(rc).passed) record('evals', name, 'PASS', { note: `flaky: failed once (${r.failed.join('; ')}), passed on rerun` });
    else if (!rc || caseResult(rc).err) record('evals', name, 'BLOCKED', { why: 'rerun did not complete' });
    else record('evals', name, 'FAIL', { why: `failed twice: ${caseResult(rc).failed.join('; ')}`.slice(0, 300) });
  }
}

function gitBash() {
  if (!WIN) return 'bash';
  try {
    const exec = execSync('git --exec-path', { encoding: 'utf8' }).trim();   // …/Git/mingw64/libexec/git-core
    const b = join(exec, '..', '..', '..', 'bin', 'bash.exe');
    return existsSync(b) ? b : null;
  } catch { return null; }
}

try { await evalsStage(); } catch (e) { record('evals', 'evals stage crashed', 'BLOCKED', { why: String(e.stack || e).slice(0, 300) }); }

// ---------- evidence ----------
const count = (s) => results.filter((r) => r.status === s).length;
meta.verdict = count('FAIL') ? 'FAIL' : count('BLOCKED') ? 'BLOCKED' : 'PASS';
// only a PASS with freshly run evals is publishable; a fast run or a re-score is not
const publishable = meta.verdict === 'PASS' && RELEASE && !EVALS_JSON;
const counts = `${count('PASS')} pass, ${count('FAIL')} fail, ${count('BLOCKED')} blocked, ${count('KNOWN')} known, ${count('NOTE')} judge notes`;
meta.finishedAt = new Date().toISOString();
writeFileSync(join(DIR, 'results.json'), JSON.stringify({ meta, results }, null, 2));
const rows = results.map((r) => `| ${r.status === 'PASS' ? 'PASS' : `**${r.status}**`} | ${r.stage} | ${r.name} | ${r.log ? `[log](${r.log})` : ''} ${(r.status === 'PASS' ? r.note || '' : r.why || '').replace(/\|/g, '/').slice(0, 160)} |`).join('\n');
writeFileSync(join(DIR, 'summary.md'), `# job-agent-skills verification ${RUN}

**Verdict: ${meta.verdict}** — ${counts}

- Package: job-agent-skills@${meta.version}${meta.tarball ? ` → \`${meta.tarball}\` (${meta.fileCount} files, ${(meta.packSize / 1024).toFixed(0)} KB)` : ''}
- Tarball sha256: \`${meta.sha256 || 'n/a'}\`
- Commit: \`${meta.commit}\` on \`${meta.branch}\`
- Uncommitted changes: ${meta.dirty === '(clean)' ? 'none' : '\n```\n' + meta.dirty + '\n```'}
- Tools: node ${meta.tools.node}, ${meta.tools.uv}, ${meta.tools.python}
- Skill evals: ${meta.evals?.rescored ? `re-scored from ${meta.evals.rescored} (no model calls)` : meta.evals ? `smoke, ${meta.evals.cases} cases via ${meta.claude} (CLI login), ≈$${meta.evals.costUsd.toFixed(2)}, ${Math.round(meta.evals.durationSeconds / 60)} min${meta.evals.reruns.length ? `, re-ran ${meta.evals.reruns.join(', ')}` : ''}; gate = deterministic graders, llm judge = notes` : 'not run (fast mode; `npm run verify -- --release` before publishing)'}
- Scope: ${ALL ? 'everything (incl. graph/, web/api)' : 'what ships to npm (graph/ and web/ not checked: use --all)'}; web/app (Next.js build) is CI-only
- Cleanup: ${meta.cleanup.stillLeft} process(es) left, unpacked copy ${meta.cleanup.unpackedRemoved ? 'removed' : 'NOT removed'}

${publishable ? `Publish this exact file:\n\n\`\`\`bash\nnpm publish .verify/${RUN}/${meta.tarball}\n\`\`\`\n` : meta.verdict === 'PASS' ? 'Code checks pass. Not a release check: run `npm run verify -- --release` before publishing.' : 'Do not publish.'}

| Result | Stage | Check | Evidence |
|---|---|---|---|
${rows}

Every command's full output is under logs/; live tool calls are in logs/live-calls.json; the packed file list is files.txt.
`);
console.log(`\n${meta.verdict}  ${counts}   evidence: .verify/${RUN}/summary.md`);
if (publishable) console.log(`publish with: npm publish .verify/${RUN}/${meta.tarball}`);
else if (meta.verdict === 'PASS' && !RELEASE) console.log('fast check only: run `npm run verify -- --release` before publishing');
if (stillLeft || !pkgGone) { console.error(`CLEANUP INCOMPLETE: ${stillLeft} process(es) left, unpacked removed: ${pkgGone}`); process.exit(3); }
process.exit({ PASS: 0, FAIL: 1, BLOCKED: 2 }[meta.verdict]);
