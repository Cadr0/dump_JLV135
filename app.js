const fileAInput = document.getElementById('fileA');
const fileBInput = document.getElementById('fileB');
const blockSizeInput = document.getElementById('blockSize');
const bytesPerLineInput = document.getElementById('bytesPerLine');
const analyzeBtn = document.getElementById('analyzeBtn');
const resetBtn = document.getElementById('resetBtn');
const showOnlyChangedCheckbox = document.getElementById('showOnlyChanged');

const statusEl = document.getElementById('status');
const summaryEl = document.getElementById('summary');
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
  renderBlocksTable(currentAnalysis);

  const coverage = ((totalDiffBytes / maxLen) * 100).toFixed(2);
  setStatus(
    `Готово: блоков ${totalBlocks}, изменённых ${changedBlocks}, байтовых отличий ${totalDiffBytes} (${coverage}%).`,
  );
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
