'use strict';
async function joinWaitlist(event) {
  if (event) event.preventDefault();
  const input = document.getElementById('email');
  const message = document.getElementById('waitmsg');
  const button = document.getElementById('waitlistButton');
  if (!input.checkValidity() || !input.value.trim()) { input.reportValidity(); return; }
  button.disabled = true;
  button.textContent = 'Saving…';
  message.textContent = '';
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 20000);
  try {
    const response = await fetch('/api/waitlist', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, signal: controller.signal,
      body: JSON.stringify({ email: input.value.trim(), website: document.getElementById('website').value })
    });
    if (!(response.headers.get('content-type') || '').includes('application/json')) throw new Error('Signups are temporarily unavailable. Your email has not been saved. Please try again later.');
    const data = await response.json();
    if (!response.ok || data.status !== 'saved') throw new Error(typeof data.detail === 'string' ? data.detail : 'Your email could not be saved. Please try again.');
    message.style.color = 'var(--mint)';
    message.textContent = data.message;
    input.value = '';
  } catch (error) {
    message.style.color = '#FF9E9E';
    message.textContent = error.name === 'AbortError' ? 'The request timed out. Please retry; duplicate signups are handled safely.' : error.message;
  } finally {
    clearTimeout(timeout);
    button.disabled = false;
    button.textContent = 'Request access';
  }
}
document.getElementById('waitlistForm').addEventListener('submit', joinWaitlist);
