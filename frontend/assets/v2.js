'use strict';
let v2Quotes = new Map();
let v2Selection = null;
let v2NewsVersion = 0;
function renderCurrentMetrics() {
  if (!v2Selection) return;
  const stock = v2Selection;
  const quote = v2Quotes.get(stock.symbol);
  const data = stock.stored_data;
  document.getElementById('storedSummary').hidden = !data && Boolean(quote);
  const container = document.getElementById('companyMetrics');
  container.replaceChildren();
  const metrics = quote ? [['DSE last trade', quote.traded ? quote.price.toFixed(2) + ' BDT' : 'No trade'], ['vs prior close', quote.change_percent == null ? 'No trade' : (quote.change_percent > 0 ? '+' : '') + quote.change_percent.toFixed(2) + '%'], ['Session volume', quote.volume.toLocaleString()]] : [['Last stored price', data ? data.close.toFixed(2) + ' BDT' : 'No records'], ['Stored change', data?.change_percent == null ? 'Not recorded' : (data.change_percent > 0 ? '+' : '') + data.change_percent.toFixed(2) + '%'], ['Price records', data ? String(data.count) : '0']];
  metrics.forEach(([label, value], index) => { const card = document.createElement('div'); const title = document.createElement('span'); title.textContent = label; const number = document.createElement('strong'); number.textContent = value; const change = quote ? quote.change_percent : data?.change_percent; if (index === 1 && change) number.className = change > 0 ? 'up' : 'down'; card.append(title, number); container.append(card); });
  if (quote) {
    document.getElementById('dataDate').textContent = 'DSE session: ' + quote.session_date + ' · Sector: ' + quote.sector;
    const link = document.getElementById('dataSource'); link.href = 'https://www.dsebd.org/api/live/prices'; link.hidden = false; link.textContent = 'DSE source data ↗';
  }
  document.getElementById('companyHealth').textContent = data ? 'Business health inputs: P/E ' + (data.pe_ratio ?? 'not supplied') + ', ROE ' + (data.roe ?? 'not supplied') + ', debt/equity ' + (data.debt_to_equity ?? 'not supplied') + '. Saved scores remain separate from DSE quotes; current financial health requires dated company reports.' : 'Company fundamentals have not been supplied yet.';
}
document.addEventListener('stock-selected', event => {
  v2Selection = event.detail;
  renderCurrentMetrics();
  loadAnnouncements(v2Selection, ++v2NewsVersion);
});
async function loadAnnouncements(stock, version) {
  const panel = document.getElementById('companyAnnouncements');
  panel.textContent = 'Loading DSE company announcements…';
  try {
    const data = await request('market/' + encodeURIComponent(stock.symbol) + '/news');
    if (version !== v2NewsVersion) return;
    panel.replaceChildren();
    const heading = document.createElement('h3'); heading.textContent = 'DSE company announcements'; panel.append(heading);
    if (!data.items.length) { const empty = document.createElement('p'); empty.textContent = 'No announcements returned by the source.'; panel.append(empty); }
    data.items.slice(0,5).forEach(item => { const article = document.createElement('article'); const date = document.createElement('small'); date.textContent = (item.filed_at || 'Date not supplied') + ' · ' + item.kind; const link = document.createElement('a'); link.textContent = item.title; const url = new URL(item.source_url); if (url.protocol === 'https:' && url.hostname === 'www.dsebd.org') link.href = url.href; link.target = '_blank'; link.rel = 'noopener noreferrer'; article.append(date, link); panel.append(article); });
    const note = document.createElement('p'); note.textContent = 'Exchange-published announcements. Company claims have not been independently verified. These events are not yet inputs to a validated prediction model.'; panel.append(note);
  } catch (error) { if (version === v2NewsVersion) panel.textContent = error.message; }
}
let refreshPending = false;
async function refreshMarket() {
  if (refreshPending) return;
  refreshPending = true;
  const status = document.getElementById('marketFeedStatus');
  try {
    const data = await request('market');
    v2Quotes = new Map(data.quotes.map(quote => [quote.symbol, quote]));
    const fetched = new Date(data.retrieved_at).toLocaleString('en-GB',{timeZone:'Asia/Dhaka'});
    status.textContent = 'DSE session ' + data.session.sessionDate + ' · Market ' + (data.session.isOpen ? 'open' : 'closed') + ' · ' + data.quotes.length + ' equities · Source time: ' + (data.source_updated_at || 'not supplied') + ' · Retrieved: ' + fetched + ' (Dhaka). Public website snapshots; latency is not guaranteed.';
    renderCurrentMetrics();
  } catch (error) {
    status.textContent = error.message + (v2Quotes.size ? ' Previous DSE snapshot retained; update failed.' : ' Showing preserved database records.');
  } finally { refreshPending = false; }
}
async function checkConnection() {
  const status = document.getElementById('connectionStatus');
  try { const health = await request('health'); status.textContent = health.database === 'reachable' ? 'Connected to your database · Stored research available' + (health.status === 'degraded' ? ' · Schema upgrade pending' : '') : 'Database connection needs attention'; }
  catch (error) { status.textContent = error.message; }
}
document.getElementById('refreshStocks').addEventListener('click',refreshMarket);
setInterval(() => { if (!document.hidden) refreshMarket(); },60000);
document.addEventListener('visibilitychange', () => { if (!document.hidden) refreshMarket(); });
checkConnection(); refreshMarket();

async function showModelResearch() {
  const container = document.getElementById('modelResearchResults');
  try {
    const response = await fetch('/assets/news-model-research.json');
    if (!response.ok) throw new Error('Research report unavailable.');
    const report = await response.json();
    const data = document.createElement('p'); data.textContent = report.companies + ' companies · ' + report.price_records.toLocaleString() + ' price observations · ' + report.announcement_events.toLocaleString() + ' official events · ' + report.coverage_start + ' to ' + report.coverage_end;
    container.replaceChildren(data);
    const table = document.createElement('table');
    const header = document.createElement('tr');
    ['Horizon','Price-only','Price + news'].forEach(label => { const cell=document.createElement('th');cell.textContent=label;header.append(cell); });table.append(header);
    report.results.forEach(row => {const line=document.createElement('tr'); [row.horizon.replaceAll('_',' '),row.price_only_balanced_accuracy + '%',row.news_balanced_accuracy + '%'].forEach(value => {const cell=document.createElement('td');cell.textContent=value;line.append(cell);});table.append(line);});
    container.append(table);
    const note = document.createElement('p'); note.textContent = 'Mean balanced accuracy across three chronological tests. News did not consistently improve the two-session model; longer-horizon improvement is modest. Candidate models are saved for research and are not enabled as production predictions.';container.append(note);
  } catch (error) { container.textContent = error.message; }
}
showModelResearch();

async function showIngestionStatus() {
 const target = document.getElementById('ingestionStatus');
 try { const response = await request('ingestion/status'); const run = response.last_run; target.textContent = run ? 'Daily collector: ' + run.status + ' · Session ' + run.session_date + ' · ' + run.record_count + ' records processed. Schedule: daily, around 16:30 Dhaka.' : 'Daily collector is scheduled; first run pending.'; }
 catch (error) { target.textContent = error.message; }
}
showIngestionStatus();

async function showNewsCaptureStatus() {
 const target = document.getElementById("newsCaptureStatus");
 try { const response = await request("news/status"); const run = response.last_run; target.textContent = run ? "Announcement collection: " + run.status + " · " + run.company_count + " companies · " + run.observed_versions + " versions observed. First-seen times are recorded for research." : "Announcement collection is scheduled daily; first run pending."; }
 catch (_) { target.textContent = "Announcement collection status unavailable. Stock research remains available."; }
}
showNewsCaptureStatus();
