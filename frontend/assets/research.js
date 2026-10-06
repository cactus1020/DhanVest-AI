'use strict';
let currentStock = null;
let selectionVersion = 0;
const list = document.getElementById('stockList');
const loading = document.getElementById('loadingList');
const explainButton = document.getElementById('btnExplain');
const explanation = document.getElementById('explanationText');

async function request(path, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 20000);
  try {
    const response = await fetch('/api/' + path, { ...options, signal: controller.signal });
    const type = response.headers.get('content-type') || '';
    if (!type.includes('application/json')) throw new Error('The research service is unavailable. Please try again later.');
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Unable to complete the request.');
    return data;
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('The connection timed out. Please try again.');
    if (error instanceof TypeError) throw new Error('Unable to connect. Please check your internet connection.');
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

const displayScore = (stock, key) => stock[key] ?? (stock.coverage === 0 ? stock.saved_scores?.[key] : null) ?? null;
const canExplain = stock => stock && (stock.coverage > 0 || stock.stored_data);
const scoreText = value => typeof value === 'number' && Number.isFinite(value) ? value.toFixed(1) : 'Unavailable';

function showLoadingError(message) {
  loading.style.display = 'block';
  loading.replaceChildren();
  const text = document.createElement('p');
  text.textContent = message;
  const retry = document.createElement('button');
  retry.className = 'btn btn-light';
  retry.type = 'button';
  retry.textContent = 'Try again';
  retry.addEventListener('click', fetchStocks);
  loading.append(text, retry);
}

async function fetchStocks() {
  selectionVersion++;
  currentStock = null;
  updateSaveButton();
  historyPoints = [];
  drawChart();
  explainButton.disabled = true;
  document.getElementById('detailCard').classList.remove('loaded');
  list.replaceChildren();
  loading.style.display = 'block';
  loading.textContent = 'Loading market research…';
  try {
    const stocks = await request('stocks');
    if (!Array.isArray(stocks)) throw new Error('The research service returned an invalid response.');
    if (!stocks.length) {
      loading.textContent = 'No stocks are available yet. Market data is being prepared.';
      return;
    }
    loading.style.display = 'none';
    allStocks = stocks;
    const sectors = [...new Set(stocks.map(stock => stock.sector))].sort();
    const selectedSector = sectorFilter.value;
    sectorFilter.replaceChildren(new Option('All sectors', ''));
    sectors.forEach(sector => sectorFilter.add(new Option(sector, sector)));
    sectorFilter.value = sectors.includes(selectedSector) ? selectedSector : '';
    renderList();
    const first = list.querySelector('button');
    if (first) renderStock(stocks.find(stock => String(stock.id) === first.dataset.stockId), first);
  } catch (error) {
    showLoadingError(error.message);
  }
}

function renderStock(stock, button) {
  selectionVersion++;
  currentStock = stock;
  document.querySelectorAll('.stock-item').forEach(item => item.classList.remove('active'));
  button.classList.add('active');
  document.querySelectorAll('.stock-item').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
  updateSaveButton();
  loadHistory(stock, selectionVersion);

  document.getElementById('detailCard').classList.add('loaded');
  document.getElementById('c-sym').textContent = stock.symbol;
  document.getElementById('c-name').textContent = stock.name + ' · ' + stock.sector;
  document.getElementById('c-score').textContent = displayScore(stock, 'composite') == null ? '—' : scoreText(displayScore(stock, 'composite'));
  document.getElementById('c-score').style.background = stock.composite == null ? '#5B6472' : '#1E2761';
  const coverage = document.getElementById('c-trend');
  coverage.className = '';
  coverage.textContent = stock.coverage ? stock.coverage + '% of verified factor inputs available' : stock.saved_scores ? 'Previously saved scores · method unvalidated' : 'No saved scores';
  const summary = document.getElementById('storedSummary');
  const data = stock.stored_data;
  summary.textContent = data ? 'Legacy imported price: ' + data.close.toFixed(2) + ' BDT · Change from previous stored record: ' + (data.change_percent == null ? 'Not available' : (data.change_percent > 0 ? '+' : '') + data.change_percent.toFixed(2) + '%') + ' · Volume: ' + (data.volume == null ? 'Not recorded' : data.volume.toLocaleString()) + ' · ' + data.count + ' records. ' + (data.dates_verified ? '' : 'Import dates and sources need verification; these are not live quotes.') : stock.latest_close != null ? 'Latest verified close: ' + stock.latest_close.toFixed(2) + ' BDT · Volume: ' + stock.latest_volume.toLocaleString() : 'No price records available.';
  document.querySelector('.mock-score-label').textContent = stock.composite == null && stock.saved_scores ? 'Saved composite' : 'Composite';
  const mapping = { value: 'val', quality: 'qual', momentum: 'mom', liquidity: 'liq' };
  Object.entries(mapping).forEach(([factor, id]) => {
    const value = displayScore(stock, factor);
    document.getElementById('c-' + id + '-text').textContent = value == null ? 'Unavailable' : scoreText(value) + '/100';
    document.getElementById('c-' + id + '-bar').style.width = (value == null ? 0 : Math.max(0, Math.min(100, value))) + '%';
    const label = document.getElementById('c-' + id + '-text').previousElementSibling;
    label.textContent = factor.charAt(0).toUpperCase() + factor.slice(1) + (stock.weights[factor] ? ' (' + (stock.weights[factor] * 100).toFixed(1) + '%)' : '');
  });
  document.getElementById('dataDate').textContent = stock.as_of ? 'Market snapshot: ' + stock.as_of + (stock.stale ? ' · Historical data' : '') : stock.stored_data ? 'Stored import date: ' + stock.stored_data.stored_date + ' · Date unverified' : 'No market records available';
  document.getElementById('dataWarnings').textContent = stock.coverage === 0 && stock.stored_data ? 'Showing your preserved database records and previously saved scores. Import dates and original scoring method are unvalidated; scores do not describe current business health.' : (stock.warnings || []).join(' ');
  const source = document.getElementById('dataSource');
  source.hidden = true;
  source.removeAttribute('href');
  if (stock.source_url) {
    try {
      const url = new URL(stock.source_url);
      if (url.protocol === 'https:') { source.href = url.href; source.hidden = false; }
    } catch (_) { /* Invalid sources never become clickable links. */ }
  }
  const archive = document.getElementById('savedResearch');
  const archiveContent = document.getElementById('savedResearchContent');
  archive.hidden = !stock.saved_scores;
  archiveContent.replaceChildren();
  if (stock.saved_scores) {
    const scoreLine = document.createElement('p');
    scoreLine.textContent = 'Original saved scores (method unvalidated): ' + ['composite','value','quality','momentum','liquidity'].map(key => key + ' ' + scoreText(stock.saved_scores[key])).join(' · ');
    const oldText = document.createElement('p'); oldText.textContent = stock.saved_scores.explanation_bn || 'No explanation was saved.';
    archiveContent.append(scoreLine,oldText);
  }
  explanation.style.display = 'none';
  explanation.textContent = '';
  if (stock.coverage === 0 && stock.stored_data) {
    explanation.style.display = 'block';
    explanation.textContent = stock.stored_summary_bn || 'Your stored data is available. Use Explain in Bangla for price movement and data limitations.';
    if (stock.saved_scores?.explanation_bn) {
      const archive = document.createElement('details');
      const title = document.createElement('summary'); title.textContent = 'Previously saved Bangla analysis · unvalidated historical output';
      const text = document.createElement('p'); text.textContent = stock.saved_scores.explanation_bn;
      archive.append(title, text); explanation.append(archive);
    }
  }
  explainButton.textContent = 'Explain in Bangla';
  explainButton.disabled = !canExplain(stock);
  document.dispatchEvent(new CustomEvent("stock-selected", {detail:stock}));
}

async function generateExplanation() {
  if (!canExplain(currentStock)) return;
  const stock = currentStock;
  if (stock.coverage === 0 && stock.stored_summary_bn) { explanation.textContent = stock.stored_summary_bn; explanation.style.display = 'block'; return; }
  const version = selectionVersion;
  explainButton.disabled = true;
  explainButton.textContent = 'Preparing explanation…';
  try {
    const data = await request('explain', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ stock_id: stock.id })
    });
    if (version !== selectionVersion) return;
    const label = data.method === 'stored_records' ? 'Explanation of your stored data (not a forecast)' : data.method === 'rules' ? 'Explanation from factor rules' : 'AI explanation from factor scores';
    explanation.textContent = label + '\n\n' + data.explanation;
    explanation.style.display = 'block';
  } catch (error) {
    if (version !== selectionVersion) return;
    explanation.textContent = error.message;
    explanation.style.display = 'block';
  } finally {
    if (version === selectionVersion) {
      explainButton.disabled = false;
      explainButton.textContent = 'Explain in Bangla';
    }
  }
}


let allStocks = [];
let watchOnly = false;
let saved = new Set();
try { const value = JSON.parse(localStorage.getItem('dhanvest-watchlist') || '[]'); if (Array.isArray(value)) saved = new Set(value.map(String)); } catch (_) {}
const sectorFilter = document.getElementById('sectorFilter');
const searchInput = document.getElementById('stockSearch');
const sortInput = document.getElementById('stockSort');
function renderList() {
    const query = searchInput.value.trim().toLowerCase();
    const visible = allStocks.filter(stock => (!query || (stock.symbol + ' ' + stock.name).toLowerCase().includes(query)) && (!sectorFilter.value || stock.sector === sectorFilter.value) && (!watchOnly || saved.has(String(stock.id))));
    visible.sort((a, b) => sortInput.value === 'score' ? (displayScore(b, 'composite') ?? -1) - (displayScore(a, 'composite') ?? -1) || a.symbol.localeCompare(b.symbol) : sortInput.value === 'coverage' ? b.coverage - a.coverage || a.symbol.localeCompare(b.symbol) : a.symbol.localeCompare(b.symbol));
    list.replaceChildren();
    document.getElementById('resultCount').textContent = visible.length + ' of ' + allStocks.length + ' stocks' + (visible.length ? '' : ' · No matches. Try changing the filters.');
    visible.forEach((stock) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.dataset.stockId = String(stock.id);
      button.className = 'stock-item';
      button.style.cssText = 'width:100%;text-align:left;font:inherit;';
      const identity = document.createElement('div');
      const symbol = document.createElement('div');
      symbol.className = 'si-sym';
      symbol.textContent = stock.symbol;
      const name = document.createElement('div');
      name.className = 'si-name';
      name.textContent = stock.name;
      identity.append(symbol, name);
      const score = document.createElement('div');
      score.className = 'si-score';
      score.textContent = displayScore(stock, 'composite') == null ? '—' : scoreText(displayScore(stock, 'composite'));
      button.append(identity, score);
      button.addEventListener('click', () => {
        renderStock(stock, button);
        if (window.innerWidth <= 850) document.getElementById('detailCard').scrollIntoView({ behavior: 'smooth', block: 'center' });
      });
      list.append(button);
      if (currentStock && currentStock.id === stock.id) { button.classList.add("active"); button.setAttribute("aria-pressed", "true"); }
    });
}
function updateSaveButton() {
  const active = currentStock && saved.has(String(currentStock.id));
  const button = document.getElementById('saveStock');
  button.disabled = !currentStock;
  button.setAttribute('aria-pressed', String(Boolean(active)));
  button.textContent = active ? 'Saved · Remove from watchlist' : 'Save to watchlist';
}
document.getElementById('saveStock').addEventListener('click', () => {
  if (!currentStock) return;
  const id = String(currentStock.id);
  const next = new Set(saved);
  next.has(id) ? next.delete(id) : next.add(id);
  try { localStorage.setItem('dhanvest-watchlist', JSON.stringify([...next])); saved = next; }
  catch (_) { document.getElementById('resultCount').textContent = 'Browser storage is unavailable. Watchlist was not saved.'; return; }
  updateSaveButton(); renderList();
});
[searchInput, sectorFilter, sortInput].forEach(input => input.addEventListener('input', renderList));
document.getElementById('watchOnly').addEventListener('click', event => { watchOnly = !watchOnly; event.currentTarget.setAttribute('aria-pressed', String(watchOnly)); renderList(); });
document.getElementById('refreshStocks').addEventListener('click', fetchStocks);
document.getElementById('backToStocks').addEventListener('click', () => { searchInput.scrollIntoView({behavior: 'smooth', block: 'center'}); searchInput.focus({preventScroll: true}); });
let historyPoints = [];
let historyMode = "verified";
let range = '20';
async function loadHistory(stock, version) {
  historyPoints = [];
  drawChart();
  document.getElementById('chartStatus').textContent = 'Loading verified history…';
  try {
    let data;
    if (document.body.dataset.version === 'v2') {
      try { data = await request('market/' + encodeURIComponent(stock.symbol) + '/history'); }
      catch (error) { data = await request('stocks/' + encodeURIComponent(stock.id) + '/history?include_stored=true'); data.feed_warning = error.message; }
    } else { data = await request('stocks/' + encodeURIComponent(stock.id) + '/history?include_stored=true'); }
    if (version !== selectionVersion) return;
    historyMode = data.mode || "verified";
    historyPoints = (data.points || []).filter(point => typeof point.close === 'number' && Number.isFinite(point.close) && point.close > 0);
    drawChart();
    if (data.adjustment) document.getElementById('chartStatus').textContent += ' · ' + data.adjustment;
    if (data.feed_warning) document.getElementById('chartStatus').textContent += ' · DSE archive unavailable; showing stored history.';
  } catch (error) { if (version === selectionVersion) document.getElementById('chartStatus').textContent = error.message; }
}
function drawChart() {
  const svg = document.getElementById('priceChart');
  document.querySelectorAll('[data-range]').forEach(button => { const labels = {'20':'1M','60':'3M','250':'1Y','all':'All'}; button.textContent = historyMode === 'stored_sequence' && button.dataset.range !== 'all' ? button.dataset.range + ' records' : labels[button.dataset.range]; });
  document.getElementById('chartTitle').textContent = historyMode === 'stored_sequence' ? 'Your stored price history · import order · BDT' : historyMode === 'dse_history' ? 'DSE historical closing prices · BDT' : 'Verified closing prices · BDT';
  const points = range === 'all' ? historyPoints : historyPoints.slice(-Number(range));
  svg.replaceChildren(); svg.toggleAttribute('hidden', points.length < 2);
  const status = document.getElementById('chartStatus');
  if (!points.length) { status.textContent = 'No verified, dated prices available. Historical records have been preserved.'; return; }
  if (points.length < 2) { status.textContent = 'At least two verified observations are needed for a chart.'; return; }
  const low = Math.min(...points.map(p => p.close)), high = Math.max(...points.map(p => p.close));
  const line = document.createElementNS('http://www.w3.org/2000/svg', 'polyline');
  line.setAttribute('points', points.map((p, i) => (10 + i / (points.length - 1) * 480) + ',' + (140 - (p.close - low) / (high - low || 1) * 120)).join(' '));
  line.setAttribute('fill', 'none'); line.setAttribute('stroke', '#1E7F5C'); line.setAttribute('stroke-width', '3');
  svg.append(line);
  const summary = (historyMode === 'stored_sequence' ? 'Stored records ' + points[0].observation + ' to ' + points.at(-1).observation + ' · Dates/source unverified' : points[0].date + ' to ' + points.at(-1).date) + ' · ' + points.length + ' observations · Low ' + low.toFixed(2) + ' / High ' + high.toFixed(2) + ' BDT · Latest ' + points.at(-1).close.toFixed(2) + ' BDT';
  svg.setAttribute('aria-label', summary); status.textContent = summary;
}
document.querySelectorAll('[data-range]').forEach(button => button.addEventListener('click', () => { range = button.dataset.range; document.querySelectorAll('[data-range]').forEach(item => item.setAttribute('aria-pressed', String(item === button))); drawChart(); }));
explainButton.disabled = true;
explainButton.addEventListener('click', generateExplanation);
fetchStocks();
