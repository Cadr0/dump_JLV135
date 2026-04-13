const fileAInput = document.getElementById('fileA');
const fileBInput = document.getElementById('fileB');
const blockSizeInput = document.getElementById('blockSize');
const bytesPerLineInput = document.getElementById('bytesPerLine');
const analyzeBtn = document.getElementById('analyzeBtn');
const resetBtn = document.getElementById('resetBtn');
const showOnlyChangedCheckbox = document.getElementById('showOnlyChanged');

const statusEl = document.getElementById('status');
const summaryEl = document.getElementById('summary');
const humanReportEl = document.getElementById('humanReport');
const tableBodyEl = document.getElementById('blocksTableBody');
const blockMetaEl = document.getElementById('blockMeta');
const hexAEl = document.getElementById('hexA');
const hexBEl = document.getElementById('hexB');

let currentAnalysis = null;

analyzeBtn.addEventListener('click', analyzeFiles);
resetBtn.addEventListener('click', resetView);
showOnlyChangedCheckbox.addEventListener('change', () => {
  if (currentAnalysis) {
    renderBlocksTable(currentAnalysis);
  }
});

function setStatus(message) {
  statusEl.textContent = message;
}

function resetView() {
  fileAInput.value = '';
  fileBInput.value = '';
  currentAnalysis = null;
  summaryEl.innerHTML = '';
  humanReportEl.innerHTML = 'Загрузите файлы и нажмите «Анализировать».';
  humanReportEl.classList.add('muted');
  tableBodyEl.innerHTML = '<tr><td colspan="7" class="muted">Пока нет данных анализа.</td></tr>';
  blockMetaEl.textContent = 'Выбери блок в таблице для просмотра деталей.';
  hexAEl.textContent = '';
  hexBEl.textContent = '';
  setStatus('Сброшено. Ожидание загрузки файлов.');
}

async function analyzeFiles() {
  const fileA = fileAInput.files[0];
  const fileB = fileBInput.files[0];

  if (!fileA || !fileB) {
    setStatus('Нужно выбрать оба файла для сравнения.');
    return;
  }

  const blockSize = Number(blockSizeInput.value);
  if (!Number.isFinite(blockSize) || blockSize < 16) {
    setStatus('Некорректный размер блока. Минимум 16 байт.');
    return;
  }

  setStatus('Чтение файлов...');

  const [bufA, bufB] = await Promise.all([fileA.arrayBuffer(), fileB.arrayBuffer()]);
  const dataA = new Uint8Array(bufA);
  const dataB = new Uint8Array(bufB);

  setStatus('Вычисление различий по блокам...');

  const maxLen = Math.max(dataA.length, dataB.length);
  const totalBlocks = Math.ceil(maxLen / blockSize);

  let totalDiffBytes = 0;
  let changedBlocks = 0;
  const blockRows = [];

  for (let i = 0; i < totalBlocks; i++) {
    const start = i * blockSize;
    const end = Math.min(start + blockSize, maxLen);

    let diffCount = 0;
    let firstDiff = null;
    let lastDiff = null;

    for (let pos = start; pos < end; pos++) {
      const a = dataA[pos];
      const b = dataB[pos];
      if (a !== b) {
        diffCount += 1;
        if (firstDiff === null) firstDiff = pos;
        lastDiff = pos;
      }
    }

    const status = diffCount === 0 ? 'equal' : classifyBlockStatus(start, end, dataA.length, dataB.length);
    const diffPercent = ((diffCount / (end - start)) * 100) || 0;

    if (diffCount > 0) {
      changedBlocks += 1;
      totalDiffBytes += diffCount;
    }

    blockRows.push({
      index: i,
      start,
      end,
      diffCount,
      diffPercent,
      firstDiff,
      lastDiff,
      status,
    });
  }

  currentAnalysis = {
    fileA,
    fileB,
    dataA,
    dataB,
    blockSize,
    totalBlocks,
    changedBlocks,
    totalDiffBytes,
    maxLen,
    blockRows,
  };

  renderSummary(currentAnalysis);
  renderHumanReadableReport(currentAnalysis);
  renderBlocksTable(currentAnalysis);

  const coverage = ((totalDiffBytes / maxLen) * 100).toFixed(2);
  setStatus(
    `Готово: блоков ${totalBlocks}, изменённых ${changedBlocks}, байтовых отличий ${totalDiffBytes} (${coverage}%).`,
  );
}

function renderHumanReadableReport(analysis) {
  const reportA = buildReadableReportForFile(analysis.dataA, analysis.fileA.name, analysis.fileB.name);
  const reportB = buildReadableReportForFile(analysis.dataB, analysis.fileB.name, analysis.fileA.name);

  humanReportEl.classList.remove('muted');
  humanReportEl.innerHTML = `
    <div class="human-cols">
      ${buildReportPanelHtml(reportA)}
      ${buildReportPanelHtml(reportB)}
    </div>
  `;
}

function buildReportPanelHtml(report) {
  return `
    <article class="human-panel">
      <h3>${escapeHtml(report.fileLabel)}</h3>
      <div><b>Векторы:</b> ${escapeHtml(report.vectorsSummary)}</div>
      <div><b>Причины риска:</b> ${escapeHtml(report.hypothesis)}</div>
      <div><b>Сигнатуры:</b> ${escapeHtml(report.signaturesSummary)}</div>
      <div><b>MAC:</b> ${escapeHtml(report.macSummary)}</div>
      <div><b>GUID:</b> ${escapeHtml(report.guidSummary)}</div>
      <div><b>SN/ID:</b> ${escapeHtml(report.serialSummary)}</div>
      <div><b>Сектора:</b> ${escapeHtml(report.sectorsSummary)}</div>
      <ul class="human-list">
        ${report.highlights.map((x) => `<li>${escapeHtml(x)}</li>`).join('')}
      </ul>
    </article>
  `;
}

function buildReadableReportForFile(data, fileName, otherFileName) {
  const vectors = parseVectors(data);
  const macs = extractMacCandidates(data, 8);
  const guids = extractGuidCandidates(data, 8);
  const serials = extractSerialCandidates(data, 10);
  const signatures = findSignatures(data, ['boot', 'firmware', 'config', 'serial', 'guid', 'mac', 'arm', 'nxp', 'cortex']);
  const sectors = analyzeSectors(data, 0x1000, 0x20000);

  const vectorsSummary = vectors
    ? `SP=0x${hex(vectors.sp)}, Reset=0x${hex(vectors.reset)}`
    : 'Недостаточно данных для таблицы векторов (нужно ≥ 64 байт).';

  const badReasons = [];
  if (vectors) {
    if (vectors.sp === 0 || vectors.sp === 0xffffffff) badReasons.push('невалидный Stack Pointer');
    if (vectors.reset === 0 || vectors.reset === 0xffffffff) badReasons.push('невалидный Reset Handler');
  }
  if (isAllFF(data, 0x1000, 0x2000)) badReasons.push('стёрто начало прошивки (0xFF)');
  const hypothesis = badReasons.length
    ? badReasons.join('; ')
    : 'Критичных проблем старта по базовым признакам не видно.';

  const changedSectorCount = sectors.filter((s) => s.state !== 'данные').length;
  const sectorsSummary = `проверено ${sectors.length} (4KB), аномалий ${changedSectorCount}`;

  const highlights = [
    `Сравнивайте с ${otherFileName}: если отличаются только GUID/SN/MAC блоки — это часто норма.`,
    `Если различия в векторах и в секторах 0x0000..0x1FFF — это частая причина "не стартует".`,
    ...sectors.slice(0, 4).map((s) => `${s.range}: FF=${s.ff.toFixed(1)}%, 00=${s.zz.toFixed(1)}% → ${s.state}`),
  ];

  return {
    fileLabel: fileName,
    vectorsSummary,
    hypothesis,
    signaturesSummary: signatures.length ? signatures.map((s) => `${s.name}@0x${hex(s.pos)}`).join(', ') : 'не найдены',
    macSummary: macs.length ? macs.map((m) => `0x${hex(m.pos)}=${m.value}`).join(', ') : 'не найдены',
    guidSummary: guids.length ? guids.map((g) => `0x${hex(g.pos)}=${g.value}`).join(', ') : 'не найдены',
    serialSummary: serials.length ? serials.map((s) => `0x${hex(s.pos)}=${s.value}`).join(', ') : 'не найдены',
    sectorsSummary,
    highlights,
  };
}

function parseVectors(data) {
  if (data.length < 64) return null;
  const dv = new DataView(data.buffer, data.byteOffset, data.byteLength);
  return {
    sp: dv.getUint32(0, true),
    reset: dv.getUint32(4, true),
  };
}

function extractMacCandidates(data, limit = 8) {
  const out = [];
  const seen = new Set();
  for (let i = 0; i <= data.length - 6; i++) {
    const b0 = data[i];
    const candidate = data.slice(i, i + 6);
    if (candidate.every((x) => x === 0x00) || candidate.every((x) => x === 0xff)) continue;
    if ((b0 & 0x01) !== 0) continue;
    const value = [...candidate].map((x) => x.toString(16).padStart(2, '0').toUpperCase()).join(':');
    if (seen.has(value)) continue;
    seen.add(value);
    out.push({ pos: i, value });
    if (out.length >= limit) break;
  }
  return out;
}

function extractGuidCandidates(data, limit = 8) {
  const out = [];
  const seen = new Set();
  for (let i = 0; i <= data.length - 16; i++) {
    const chunk = data.slice(i, i + 16);
    if (chunk.every((x) => x === 0x00) || chunk.every((x) => x === 0xff)) continue;
    const value = formatGuid(chunk);
    if (seen.has(value)) continue;
    seen.add(value);
    out.push({ pos: i, value });
    if (out.length >= limit) break;
  }
  return out;
}

function formatGuid(chunk) {
  const h = [...chunk].map((x) => x.toString(16).padStart(2, '0')).join('');
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20, 32)}`;
}

function extractSerialCandidates(data, limit = 10) {
  const strings = extractAsciiStrings(data, 6, 300);
  const regex = /(?:sn|serial|id|guid|mac)?[:=_\- ]?([A-Z0-9][A-Z0-9\-]{7,31})/gi;
  const out = [];
  for (const item of strings) {
    let m;
    while ((m = regex.exec(item.value)) !== null) {
      if (/^[A-Z]+$/i.test(m[1])) continue;
      out.push({ pos: item.pos, value: m[1] });
      if (out.length >= limit) return out;
    }
  }
  return out;
}

function extractAsciiStrings(data, minLen = 6, maxItems = 300) {
  const out = [];
  let start = -1;
  for (let i = 0; i < data.length; i++) {
    const v = data[i];
    const printable = v >= 32 && v <= 126;
    if (printable && start < 0) start = i;
    if ((!printable || i === data.length - 1) && start >= 0) {
      const end = printable && i === data.length - 1 ? i + 1 : i;
      if (end - start >= minLen) {
        const bytes = data.slice(start, end);
        out.push({ pos: start, value: String.fromCharCode(...bytes) });
        if (out.length >= maxItems) return out;
      }
      start = -1;
    }
  }
  return out;
}

function findSignatures(data, signatures) {
  const text = new TextDecoder('latin1').decode(data).toLowerCase();
  const out = [];
  for (const sig of signatures) {
    const pos = text.indexOf(sig.toLowerCase());
    if (pos >= 0) out.push({ name: sig, pos });
  }
  return out;
}

function analyzeSectors(data, sectorSize = 0x1000, maxBytes = 0x20000) {
  const out = [];
  const limit = Math.min(maxBytes, data.length);
  for (let start = 0; start < limit; start += sectorSize) {
    const end = Math.min(start + sectorSize, limit);
    const blk = data.slice(start, end);
    const ff = (countByte(blk, 0xff) / blk.length) * 100;
    const zz = (countByte(blk, 0x00) / blk.length) * 100;
    let state = 'данные';
    if (ff > 98) state = 'стерт (0xFF)';
    else if (zz > 95) state = 'нулевой/подозрительный';
    out.push({ range: `0x${hex(start)}..0x${hex(end - 1)}`, ff, zz, state });
  }
  return out;
}

function countByte(arr, value) {
  let n = 0;
  for (const x of arr) if (x === value) n += 1;
  return n;
}

function isAllFF(data, start, end) {
  if (start >= data.length) return false;
  for (let i = start; i < Math.min(end, data.length); i++) {
    if (data[i] !== 0xff) return false;
  }
  return true;
}

function escapeHtml(s) {
  return String(s)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function classifyBlockStatus(start, end, lenA, lenB) {
  if (start >= lenA || start >= lenB) return 'size-mismatch';
  if (end > lenA || end > lenB) return 'size-mismatch';
  return 'changed';
}

function renderSummary(analysis) {
  const metrics = [
    ['Файл A', `${analysis.fileA.name} (${formatNum(analysis.dataA.length)} B)`],
    ['Файл B', `${analysis.fileB.name} (${formatNum(analysis.dataB.length)} B)`],
    ['Всего блоков', formatNum(analysis.totalBlocks)],
    ['Изменённые блоки', `${formatNum(analysis.changedBlocks)} (${pct(analysis.changedBlocks, analysis.totalBlocks)}%)`],
    ['Изменённые байты', `${formatNum(analysis.totalDiffBytes)} (${pct(analysis.totalDiffBytes, analysis.maxLen)}%)`],
  ];

  summaryEl.innerHTML = metrics
    .map(([label, value]) => `<div class="metric"><div class="label">${label}</div><div class="value">${value}</div></div>`)
    .join('');
}

function renderBlocksTable(analysis) {
  const onlyChanged = showOnlyChangedCheckbox.checked;
  const rows = onlyChanged ? analysis.blockRows.filter((b) => b.diffCount > 0) : analysis.blockRows;

  if (rows.length === 0) {
    tableBodyEl.innerHTML = '<tr><td colspan="7" class="muted">Нет строк по текущему фильтру.</td></tr>';
    return;
  }

  tableBodyEl.innerHTML = rows
    .map((block) => {
      const statusText = block.status === 'equal' ? 'OK' : block.status === 'size-mismatch' ? 'SIZE Δ' : 'CHANGED';
      return `
      <tr data-index="${block.index}">
        <td>${block.index}</td>
        <td>0x${hex(block.start)} - 0x${hex(block.end - 1)}</td>
        <td><span class="badge ${block.status}">${statusText}</span></td>
        <td>${formatNum(block.diffCount)}</td>
        <td>${block.diffPercent.toFixed(2)}%</td>
        <td>${block.firstDiff === null ? '—' : `0x${hex(block.firstDiff)}`}</td>
        <td>${block.lastDiff === null ? '—' : `0x${hex(block.lastDiff)}`}</td>
      </tr>
      `;
    })
    .join('');

  [...tableBodyEl.querySelectorAll('tr[data-index]')].forEach((row) => {
    row.addEventListener('click', () => {
      [...tableBodyEl.querySelectorAll('tr')].forEach((r) => r.classList.remove('selected'));
      row.classList.add('selected');
      const idx = Number(row.dataset.index);
      showBlockDetails(idx);
    });
  });
}

function showBlockDetails(blockIndex) {
  if (!currentAnalysis) return;

  const { dataA, dataB, blockRows } = currentAnalysis;
  const bytesPerLine = Number(bytesPerLineInput.value) || 16;
  const block = blockRows[blockIndex];
  if (!block) return;

  const changedList = collectChangedOffsets(dataA, dataB, block.start, block.end);
  const changedPreview = changedList.slice(0, 12).map((x) => `0x${hex(x)}`).join(', ');

  blockMetaEl.innerHTML = `
    Блок <b>#${block.index}</b> | Диапазон <b>0x${hex(block.start)} - 0x${hex(block.end - 1)}</b><br>
    Изменено байт: <b>${formatNum(block.diffCount)}</b> (${block.diffPercent.toFixed(2)}%)<br>
    Первое отличие: <b>${block.firstDiff === null ? '—' : `0x${hex(block.firstDiff)}`}</b>
    | Последнее отличие: <b>${block.lastDiff === null ? '—' : `0x${hex(block.lastDiff)}`}</b><br>
    Смещения (первые 12): <span class="muted">${changedPreview || 'нет'}</span>
  `;

  hexAEl.innerHTML = buildHexView(dataA, dataB, block.start, block.end, bytesPerLine, 'A');
  hexBEl.innerHTML = buildHexView(dataA, dataB, block.start, block.end, bytesPerLine, 'B');
}

function buildHexView(dataA, dataB, start, end, bytesPerLine, mode) {
  const lines = [];

  for (let offset = start; offset < end; offset += bytesPerLine) {
    const lineEnd = Math.min(offset + bytesPerLine, end);
    const chunks = [];
    const ascii = [];

    for (let i = offset; i < lineEnd; i++) {
      const a = dataA[i];
      const b = dataB[i];
      const value = mode === 'A' ? a : b;
      const changed = a !== b;

      const byteHex = typeof value === 'number' ? value.toString(16).padStart(2, '0').toUpperCase() : '--';
      const text = typeof value === 'number' && value >= 32 && value <= 126 ? String.fromCharCode(value) : '.';

      chunks.push(changed ? `<span class="diff-byte">${byteHex}</span>` : byteHex);
      ascii.push(changed ? `<span class="diff-byte">${text}</span>` : text);
    }

    lines.push(`0x${hex(offset)} | ${chunks.join(' ')} | ${ascii.join('')}`);
  }

  return lines.join('\n');
}

function collectChangedOffsets(dataA, dataB, start, end) {
  const out = [];
  for (let i = start; i < end; i++) {
    if (dataA[i] !== dataB[i]) out.push(i);
  }
  return out;
}

function formatNum(v) {
  return new Intl.NumberFormat('ru-RU').format(v);
}

function pct(value, total) {
  if (!total) return '0.00';
  return ((value / total) * 100).toFixed(2);
}

function hex(v) {
  return Number(v).toString(16).toUpperCase().padStart(8, '0');
}
