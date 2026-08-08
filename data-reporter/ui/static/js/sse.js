/* ODR chat UI — SSE client. EventSource can't POST, so this is a plain
 * fetch() + ReadableStream reader that parses "event: x\ndata: y\n\n"
 * frames and dispatches to a single onEvent(type, payload) callback. */
(function () {
  'use strict';

  function streamChat(message, onEvent) {
    return fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: message }),
    })
      .then(function (response) {
        if (!response.ok) {
          return response
            .json()
            .catch(function () { return {}; })
            .then(function (body) {
              var err = new Error((body && body.detail) || 'HTTP ' + response.status);
              err.status = response.status;
              throw err;
            });
        }

        var reader = response.body.getReader();
        var decoder = new TextDecoder('utf-8');
        var buffer = '';

        function dispatch(frame) {
          if (!frame.trim()) return;
          var eventType = 'message';
          var dataLines = [];
          frame.split('\n').forEach(function (line) {
            if (line.indexOf('event:') === 0) eventType = line.slice(6).trim();
            else if (line.indexOf('data:') === 0) dataLines.push(line.slice(5).trim());
          });
          var payload = {};
          try {
            payload = JSON.parse(dataLines.join('\n'));
          } catch (e) {
            return; // malformed frame, skip rather than throw
          }
          onEvent(eventType, payload);
        }

        function pump() {
          return reader.read().then(function (result) {
            if (result.done) {
              if (buffer.trim()) dispatch(buffer);
              return;
            }
            buffer += decoder.decode(result.value, { stream: true });
            var frames = buffer.split('\n\n');
            buffer = frames.pop();
            frames.forEach(dispatch);
            return pump();
          });
        }

        return pump();
      })
      .catch(function (err) {
        onEvent('error', { message: err.message || 'Request failed.', kind: 'network' });
      });
  }

  window.ODR_SSE = { streamChat: streamChat };
})();
