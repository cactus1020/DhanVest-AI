'use strict';
(() => {
  const el = id => document.getElementById(id);
  const money = value => value == null ? 'Unavailable' : '৳' + Number(value).toLocaleString('en-BD', {minimumFractionDigits: 2, maximumFractionDigits: 2});
  let token = sessionStorage.getItem('dhanvest-paper-session');
  let quotes = [], positions = [], trades = [], cash = 0, marketOpen = false;
  let pending = null, busy = false, refreshing = false, mode = 'login', generation = 0;
  let retry = null;
  try { retry = JSON.parse(sessionStorage.getItem('dhanvest-paper-retry') || 'null'); } catch (_) { sessionStorage.removeItem('dhanvest-paper-retry'); }

  function status(text, error = false) {
    el('status').textContent = text;
    el('status').dataset.error = String(error);
    el('retryOrder').hidden = !retry || !token;
  }
  function clearSession() {
    generation++;
    token = null; retry = null; pending = null;
    sessionStorage.removeItem('dhanvest-paper-session');
    sessionStorage.removeItem('dhanvest-paper-retry');
    el('workspace').hidden = true; el('auth').hidden = false;
    el('confirmation').hidden = true; el('retryOrder').hidden = true;
    el('side').value = 'buy'; el('stockSearch').value = ''; el('quantity').value = '1';
    quotes = []; positions = []; trades = []; cash = 0; marketOpen = false;
  }
  async function api(path, body) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 35000);
    try {
      const response = await fetch(path, {
        method: body ? 'POST' : 'GET', signal: controller.signal,
        headers: {'Content-Type': 'application/json', ...(token ? {Authorization: 'Bearer ' + token} : {})},
        ...(body ? {body: JSON.stringify(body)} : {})
      });
      let data;
      try { data = await response.json(); } catch (_) { throw new Error('Service response unavailable. Please retry.'); }
      if (!response.ok) {
        if (response.status === 401 && token && !path.startsWith('/api/account')) clearSession();
        const error = new Error(typeof data.detail === 'string' ? data.detail : 'Please check your details and retry.');
        error.status = response.status; throw error;
      }
      return data;
    } catch (error) {
      if (error.name === 'AbortError' || error instanceof TypeError) throw new Error('Connection interrupted. Please retry.');
      throw error;
    } finally { clearTimeout(timer); }
  }
  function row(parent, values) {
    const item = document.createElement('tr');
    for (const value of values) { const cell = document.createElement('td'); cell.textContent = value; item.append(cell); }
    parent.append(item);
  }
  function estimate() {
    const quote = quotes.find(q => q.symbol === el('symbol').value);
    const quantity = Number(el('quantity').value), selling = el('side').value === 'sell';
    const held = positions.find(p => p.symbol === el('symbol').value)?.quantity || 0;
    const price = quote?.price, fee = price ? Math.round(price * quantity * .0025 * 100) / 100 : 0;
    const maximum = selling ? held : price ? Math.floor(cash / (price * 1.0025)) : 0;
    el('estimate').textContent = price ? `Indicative quote ${money(price)} · ${selling ? 'Estimated proceeds' : 'Estimated cost'} ${money(price * quantity + (selling ? -fee : fee))} · Fee ${money(fee)}` : 'No executable quote for this stock.';
    el('orderHint').textContent = `${selling ? 'You own' : 'You can afford approximately'} ${maximum.toLocaleString()} shares. ${marketOpen ? 'The server confirms price and balance before execution.' : 'Market closed: browse your portfolio; trading resumes when DSE opens.'}`;
    el('submitOrder').disabled = busy || !marketOpen || !price || !Number.isSafeInteger(quantity) || quantity < 1 || quantity > maximum;
  }
  function stockOptions() {
    const selected = el('symbol').value, search = el('stockSearch').value.trim().toUpperCase();
    const selling = el('side').value === 'sell';
    el('symbol').replaceChildren();
    for (const q of quotes.filter(q => q.traded && q.symbol.includes(search) && (!selling || positions.some(p => p.symbol === q.symbol))).sort((a, b) => a.symbol.localeCompare(b.symbol))) {
      const option = document.createElement('option'); option.value = q.symbol; option.textContent = q.symbol + ' · ' + money(q.price); el('symbol').append(option);
    }
    if (!el('symbol').options.length) { const option = document.createElement('option'); option.value = ''; option.textContent = selling ? 'No matching holdings to sell' : 'No matching stocks'; el('symbol').append(option); }
    if ([...el('symbol').options].some(o => o.value === selected)) el('symbol').value = selected;
    estimate();
  }
  async function load() {
    if (!token || refreshing) return;
    refreshing = true; el('refresh').disabled = true;
    const version = generation;
    try {
      const [portfolio, market] = await Promise.all([api('/api/paper/portfolio'), api('/api/market').catch(() => null)]);
      if (!token || version !== generation) return;
      positions = portfolio.positions; trades = portfolio.trades; cash = Number(portfolio.account.cash);
      el('auth').hidden = true; el('workspace').hidden = false;
      el('summary').replaceChildren();
      for (const [name, value] of [['Virtual cash', cash], ['Holdings value', portfolio.equity == null ? null : portfolio.equity - cash], ['Total equity', portfolio.equity], ['Total profit / loss', portfolio.total_pnl]]) {
        const box = document.createElement('div'); box.className = 'metric'; box.textContent = name;
        if (name === 'Total profit / loss') { box.dataset.negative = String(value < 0); box.dataset.positive = String(value > 0); }
        const amount = document.createElement('strong'); amount.textContent = money(value); box.append(amount); el('summary').append(box);
      }
      el('holdings').replaceChildren();
      for (const p of positions) row(el('holdings'), [p.symbol, p.quantity, money(p.cost_basis), money(p.market_value), money(p.unrealized_pnl)]);
      if (!positions.length) row(el('holdings'), ['আপনার প্রথম শেয়ার কেনার পর এখানে দেখাবে', '—', '—', '—', '—']);
      el('trades').replaceChildren();
      for (const t of trades) row(el('trades'), [new Date(t.created_at).toLocaleString('en-GB', {timeZone: 'Asia/Dhaka'}), t.symbol, t.side, t.quantity, money(t.price), money(t.fee), money(t.realized_pnl)]);
      if (!trades.length) row(el('trades'), ['No trades yet', '—', '—', '—', '—', '—', '—']);
      quotes = market?.quotes || []; marketOpen = Boolean(market?.session.isOpen);
      el('marketState').textContent = market ? `${marketOpen ? 'Market open' : 'Market closed'} · Session ${market.session.sessionDate} · Retrieved ${new Date(market.retrieved_at).toLocaleTimeString('en-GB', {timeZone: 'Asia/Dhaka'})} Dhaka · Public quotes may be delayed` : 'Market source unavailable. Your account and saved trades remain intact.';
      stockOptions();
      if (retry) status('An earlier order needs verification. Retry the same stock, side and quantity to safely retrieve its result.', true);
    } finally { refreshing = false; el('refresh').disabled = false; }
  }
  function authMode(value) {
    mode = value;
    el('signinTab').setAttribute('aria-pressed', String(mode === 'login'));
    el('signupTab').setAttribute('aria-pressed', String(mode === 'signup'));
    el('signinTab').className = mode === 'login' ? '' : 'secondary';
    el('signupTab').className = mode === 'signup' ? '' : 'secondary';
    el('password').autocomplete = mode === 'signup' ? 'new-password' : 'current-password';
    el('authSubmit').textContent = mode === 'signup' ? 'Create account · ৳১০ লাখ virtual fund' : 'Sign in';
    el('authHelp').textContent = mode === 'signup' ? 'কমপক্ষে ৮ অক্ষরের password দিন। Email confirmation প্রয়োজন হলে inbox-এর link দিয়ে confirm করে sign in করুন।' : 'আগের account থাকলে sign in করুন। একই account-এ balance ও trade history সংরক্ষিত থাকবে।';
  }
  el('signinTab').onclick = () => authMode('login');
  el('signupTab').onclick = () => authMode('signup');
  el('togglePassword').onclick = () => {
    const show = el('password').type === 'password'; el('password').type = show ? 'text' : 'password';
    el('togglePassword').textContent = show ? 'Hide password' : 'Show password'; el('togglePassword').setAttribute('aria-pressed', String(show));
  };
  el('authForm').addEventListener('submit', async event => {
    event.preventDefault(); if (busy) return; busy = true; el('authSubmit').disabled = true;
    try {
      status('Connecting securely…');
      const data = await api('/api/account/' + mode, {email: el('email').value.trim(), password: el('password').value});
      el('password').value = '';
      if (!data.access_token) { authMode('login'); status('Check your inbox and spam folder. Confirm your email, then sign in here.'); return; }
      token = data.access_token; generation++; retry = null; sessionStorage.removeItem('dhanvest-paper-retry');
      sessionStorage.setItem('dhanvest-paper-session', token); await load(); status('আপনার সংরক্ষিত virtual portfolio প্রস্তুত। Balance ও holdings নিচে দেখুন।');
    } catch (error) { status(error.message, true); }
    finally { busy = false; el('authSubmit').disabled = false; estimate(); }
  });
  el('refresh').onclick = () => load().catch(error => status(error.message, true));
  el('logout').onclick = () => { if (busy) return; clearSession(); status('Signed out on this device. Your portfolio is saved.'); };
  el('orderForm').addEventListener('submit', event => {
    event.preventDefault(); if (busy || el('submitOrder').disabled) return;
    const order = {symbol: el('symbol').value, side: el('side').value, quantity: Number(el('quantity').value)};
    const same = retry && ['symbol', 'side', 'quantity'].every(k => retry[k] === order[k]);
    if (retry && !same) { status('Verify your earlier order before placing a different trade. Refresh and retry the same order.', true); return; }
    pending = {...order, request_id: same ? retry.request_id : crypto.randomUUID()};
    el('orderReview').textContent = `${order.side.toUpperCase()} ${order.quantity} ${order.symbol} shares using virtual funds. ${el('estimate').textContent}. Final fill price may change.`;
    el('confirmation').hidden = false; el('confirmOrder').focus();
  });
  el('retryOrder').onclick = () => { pending = {...retry}; el('orderReview').textContent = `Verify earlier ${retry.side} order: ${retry.quantity} ${retry.symbol} shares. Its original reference will be reused; no duplicate fill.`; el('confirmation').hidden = false; el('confirmOrder').focus(); };
  el('cancelOrder').onclick = () => { if (busy) return; pending = null; el('confirmation').hidden = true; };
  el('confirmOrder').onclick = async () => {
    if (!pending || busy) return; busy = true; el('confirmOrder').disabled = true; estimate();
    retry = {...pending}; sessionStorage.setItem('dhanvest-paper-retry', JSON.stringify(retry));
    let executed = false;
    try {
      status('Submitting virtual order…'); const data = await api('/api/paper/orders', pending);
      executed = true; pending = null; retry = null; sessionStorage.removeItem('dhanvest-paper-retry'); el('confirmation').hidden = true;
      status(`Virtual ${data.trade.side} filled at ${money(data.trade.price)} per share. Fee ${money(data.trade.fee)}.`);
      await load();
    } catch (error) {
      if (error.status && error.status < 500) { retry = null; pending = null; sessionStorage.removeItem('dhanvest-paper-retry'); el('confirmation').hidden = true; }
      status(executed ? 'Trade completed, but portfolio refresh failed. Refresh to view the saved result.' : error.message + (retry ? ' Verify the earlier order before submitting another.' : ''), true);
    } finally { busy = false; el('confirmOrder').disabled = false; estimate(); }
  };
  el('exportTrades').onclick = () => {
    const fields = ['created_at', 'symbol', 'side', 'quantity', 'price', 'fee', 'realized_pnl'];
    const csvCell = value => '"' + String(value ?? '').replace(/"/g, '""').replace(/^[=+@-]/, "'$&") + '"';
    const csv = [fields.join(','), ...trades.map(t => fields.map(k => csvCell(t[k])).join(','))].join('\r\n');
    const url = URL.createObjectURL(new Blob([csv], {type: 'text/csv;charset=utf-8'}));
    const link = document.createElement('a'); link.href = url; link.download = 'dhanvest-virtual-trades.csv'; link.click(); URL.revokeObjectURL(url);
  };
  el('stockSearch').addEventListener('input', stockOptions);
  el('side').addEventListener('change', stockOptions);
  for (const id of ['symbol', 'quantity']) el(id).addEventListener('input', estimate);
  setInterval(() => { if (token && !document.hidden && !busy && !pending && !retry) load().catch(error => status(error.message, true)); }, 60000);
  if (token) load().catch(error => status(error.message, true));
})();
