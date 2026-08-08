/* ODR chat UI — message rendering, activity rows, artifact-link detection.
 * Design principle: exactly one way any intent reaches the claude
 * subprocess — POST /api/chat via send()/sendComposed(). Skill cards and
 * Quick Build (app.js) both just call into this, never a separate endpoint.
 */
(function () {
  'use strict';

  var messagesEl, inputEl, sendBtn, newConvBtn;
  var sending = false;
  var currentAssistantEl = null;
  var currentAssistantText = '';
  var currentActivityEl = null;
  var lastToolRow = null;
  var needsParagraphBreak = false;

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function addUserMessage(text) {
    var wrap = el('div', 'msg msg-user');
    var bubble = el('div', 'msg-bubble', text);
    wrap.appendChild(bubble);
    messagesEl.appendChild(wrap);
    scrollToBottom();
  }

  function startAssistantMessage() {
    var wrap = el('div', 'msg msg-assistant');
    var bubble = el('div', 'msg-bubble');
    var textEl = el('div', 'msg-text');
    var activityEl = el('div', 'activity');
    bubble.appendChild(textEl);
    bubble.appendChild(activityEl);
    wrap.appendChild(bubble);
    messagesEl.appendChild(wrap);
    scrollToBottom();
    currentAssistantEl = textEl;
    currentActivityEl = activityEl;
    currentAssistantText = '';
    needsParagraphBreak = false;
  }

  function updateAssistantText() {
    if (!currentAssistantEl) return;
    currentAssistantEl.innerHTML = window.ODR_MARKDOWN.renderMarkdown(currentAssistantText);
    scrollToBottom();
  }

  function addActivityRow(status, label, detail) {
    if (!currentActivityEl) return null;
    var row = el('div', 'activity-row activity-' + status);
    row.appendChild(el('span', 'activity-icon'));
    row.appendChild(el('span', 'activity-label', label));
    if (detail) row.appendChild(el('div', 'activity-detail', detail));
    currentActivityEl.appendChild(row);
    scrollToBottom();
    return row;
  }

  function setRowStatus(row, status) {
    if (!row) return;
    row.className = row.className.replace(/activity-(pending|ok|error|denied)\b/, 'activity-' + status);
  }

  function addOpenReportButton(urlPath) {
    if (!currentActivityEl) return;
    var row = el('div', 'activity-row activity-artifact');
    var link = el('a', 'open-report-btn', 'Open Report ↗');
    link.href = '/artifacts/' + urlPath;
    link.target = '_blank';
    link.rel = 'noopener';
    row.appendChild(link);
    currentActivityEl.appendChild(row);
    scrollToBottom();
  }

  function setSending(isSending) {
    sending = isSending;
    sendBtn.disabled = isSending;
    sendBtn.textContent = isSending ? 'Sending…' : 'Send';
  }

  function handleEvent(type, payload) {
    if (type === 'text') {
      // Only break between what look like complete sentences/clauses — a
      // tool call can land mid-word (Claude may stream "R" then pause to
      // call a tool before continuing "ebuilt: ..."), and breaking there
      // would visibly mangle the word.
      if (needsParagraphBreak && currentAssistantText && /[.!?:]\s*$|\s$/.test(currentAssistantText)) {
        currentAssistantText += '\n\n';
      }
      needsParagraphBreak = false;
      currentAssistantText += payload.delta || '';
      updateAssistantText();
    } else if (type === 'tool_start') {
      needsParagraphBreak = true;
      lastToolRow = addActivityRow('pending', payload.label || ('Using ' + payload.tool));
    } else if (type === 'tool_result') {
      setRowStatus(lastToolRow, payload.is_error ? 'error' : 'ok');
      if (payload.is_error && lastToolRow && payload.summary) {
        lastToolRow.appendChild(el('div', 'activity-detail', payload.summary));
      }
      if (payload.wrote_artifact) {
        addOpenReportButton(payload.wrote_artifact);
        if (window.ODR_APP && window.ODR_APP.refreshArtifacts) window.ODR_APP.refreshArtifacts();
      }
    } else if (type === 'tool_denied') {
      addActivityRow('denied', payload.label || 'Blocked', payload.detail || '');
    } else if (type === 'done') {
      if (!currentAssistantText && payload.final_text) {
        currentAssistantText = payload.final_text;
        updateAssistantText();
      }
      finishTurn();
    } else if (type === 'error') {
      addActivityRow('error', payload.message || 'Something went wrong.');
      finishTurn();
    }
  }

  function finishTurn() {
    setSending(false);
    currentAssistantEl = null;
    currentActivityEl = null;
    lastToolRow = null;
  }

  function send() {
    var text = inputEl.value.trim();
    if (!text || sending) return;
    inputEl.value = '';
    setSending(true);
    addUserMessage(text);
    startAssistantMessage();
    window.ODR_SSE.streamChat(text, handleEvent).then(function () {
      if (sending) finishTurn(); // safety net; backend guarantees a terminal event
    });
  }

  function insertAndFocus(text) {
    inputEl.value = text;
    inputEl.focus();
    inputEl.setSelectionRange(text.length, text.length);
  }

  function sendComposed(text) {
    if (sending) return;
    inputEl.value = text;
    send();
  }

  function newConversation() {
    if (sending && !window.confirm('A message is still in progress. Start a new conversation anyway?')) {
      return;
    }
    fetch('/api/reset', { method: 'POST' }).then(function () {
      messagesEl.innerHTML = '';
      finishTurn();
    });
  }

  function init() {
    messagesEl = document.getElementById('messages');
    inputEl = document.getElementById('chat-input');
    sendBtn = document.getElementById('send-btn');
    newConvBtn = document.getElementById('new-conversation-btn');

    sendBtn.addEventListener('click', send);
    newConvBtn.addEventListener('click', newConversation);
    inputEl.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        send();
      }
    });
  }

  window.ODR_CHAT = { init: init, insertAndFocus: insertAndFocus, sendComposed: sendComposed };
})();
