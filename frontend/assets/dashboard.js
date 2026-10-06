'use strict';
let selectedStock = null;
let version = 0;
const list = document.getElementById('stockList');
const generate = document.getElementById('generateBtn');
const displayScore = (stock, key) => stock[key] ?? (stock.coverage === 0 ? stock.saved_scores?.[key] : null) ?? null;
const explanation = document.getElementById('explanationBox');

async function apiRequest(path, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 20000);
  try {
    const response = await fetch('/api/' + path, { ...options, signal: controller.signal });
    if (!(response.headers.get('content-type') || '').includes('application/json')) throw new Error('The research service is unavailable. Please try again later.');
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Unable to complete this request.');
    return data;
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('The connection timed out. Please try again.');
    throw error;
  } finally { clearTimeout(timeout); }
}

function selectStock(stock, button) {
  version++;
  selectedStock = stock;
  document.querySelectorAll('.stock-item').forEach(item => item.classList.remove('active'));
  button.classList.add('active');
  document.getElementById('emptyState').style.display = 'none';
  document.getElementById('detailPanel').style.display = 'block';
  document.getElementById('detailTitle').textContent = stock.name + ' (' + stock.symbol + ')';
  document.getElementById('detailSector').textContent = stock.sector;
  document.getElementById('snapshotDate').textContent = (stock.as_of ? 'Snapshot: ' + stock.as_of : 'No verified snapshot') + ' · Factor coverage: ' + stock.coverage + '%' + (stock.stale && stock.as_of ? ' · Historical data' : '');
  document.getElementById('snapshotWarnings').textContent = stock.stored_data && stock.coverage === 0 ? 'Stored price: ' + stock.stored_data.close + ' BDT. ' + stock.stored_data.count + ' records preserved. Displaying previously saved scores; dates and scoring method are unvalidated.' : (stock.warnings || []).join(' ');
  const source = document.getElementById('snapshotSource');
  source.hidden = true;
  source.removeAttribute('href');
  if (stock.source_url) {
    try { const url = new URL(stock.source_url); if (url.protocol === 'https:') { source.href = url.href; source.hidden = false; } } catch (_) {}
  }
  ['value', 'quality', 'momentum', 'liquidity'].forEach(factor => {
    const name = factor[0].toUpperCase() + factor.slice(1);
    const value = displayScore(stock, factor);
    document.getElementById('bar' + name).style.width = (value == null ? 0 : Math.max(0, Math.min(100, value))) + '%';
    document.getElementById('val' + name).textContent = value == null ? 'Unavailable' : value.toFixed(1) + '/100';
    document.getElementById('label' + name).textContent = name + (stock.weights[factor] ? ' (' + (stock.weights[factor] * 100).toFixed(1) + '%)' : '');
  });
  document.getElementById('loader').style.display = 'none';
  explanation.style.display = 'block';
  explanation.textContent = 'Click generate to see the Bangla explanation of the available scores.';
  generate.disabled = stock.coverage === 0 && !stock.stored_data;
}

async function fetchStocks() {
  list.replaceChildren();
  document.getElementById('loadStatus').textContent = 'Loading market research…';
  try {
    const stocks = await apiRequest('stocks');
    if (!Array.isArray(stocks)) throw new Error('Invalid response from the research service.');
    document.getElementById('loadStatus').textContent = stocks.length ? '' : 'No stocks available yet.';
    stocks.forEach(stock => {
      const item = document.createElement('li');
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'stock-item';
      button.style.cssText = 'width:100%;text-align:left;font:inherit;background:transparent;';
      const identity = document.createElement('div');
      const symbol = document.createElement('div');
      symbol.className = 'stock-symbol'; symbol.textContent = stock.symbol;
      const name = document.createElement('div');
      name.className = 'stock-name'; name.textContent = stock.name;
      identity.append(symbol, name);
      const score = document.createElement('div');
      score.className = 'stock-score-badge';
      score.style.backgroundColor = '#1E2761';
      score.textContent = displayScore(stock, 'composite') == null ? '—' : displayScore(stock, 'composite').toFixed(1);
      button.append(identity, score);
      button.addEventListener('click', () => selectStock(stock, button));
      item.append(button);
      list.append(item);
    });
  } catch (error) {
    document.getElementById('loadStatus').textContent = error.message;
    const retry = document.createElement('button');
    retry.type = 'button'; retry.textContent = 'Try again'; retry.className = 'generate-btn';
    retry.addEventListener('click', fetchStocks);
    const item = document.createElement('li'); item.append(retry); list.append(item);
  }
}

generate.addEventListener('click', async () => {
  if (!selectedStock || !selectedStock.coverage) return;
  const capturedVersion = version;
  const id = selectedStock.id;
  generate.disabled = true;
  document.getElementById('loader').style.display = 'block';
  try {
    const data = await apiRequest('explain', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ stock_id: id }) });
    if (capturedVersion !== version) return;
    explanation.textContent = (data.method === 'rules' ? 'Explanation from factor rules' : 'AI explanation from factor scores') + '\n\n' + data.explanation;
  } catch (error) {
    if (capturedVersion === version) explanation.textContent = error.message;
  } finally {
    if (capturedVersion === version) { generate.disabled = false; document.getElementById('loader').style.display = 'none'; }
  }
});
generate.disabled = true;
fetchStocks();
