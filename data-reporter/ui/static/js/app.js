/* ODR chat UI — bootstrap: fetch skills/roles/artifacts/doctor, wire the
 * sidebar. Exposes ODR_APP.refreshArtifacts() for chat.js to call after a
 * build completes. */
(function () {
  'use strict';

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  function loadSkills() {
    fetch('/api/skills')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var container = document.getElementById('skills-list');
        container.innerHTML = '';
        (data.skills || []).forEach(function (skill) {
          var card = el('div', 'skill-card');
          card.appendChild(el('div', 'skill-name', skill.name));
          card.appendChild(el('div', 'skill-desc', skill.description));
          card.addEventListener('click', function () {
            window.ODR_CHAT.insertAndFocus('/' + skill.name + ' ');
          });
          container.appendChild(card);
        });
      })
      .catch(function () {
        document.getElementById('skills-list').textContent = 'Could not load skills.';
      });
  }

  var rolesData = [];

  function loadRoles() {
    return fetch('/api/roles')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        rolesData = data.roles || [];
        var roleSelect = document.getElementById('qb-role');
        roleSelect.innerHTML = '';
        rolesData.forEach(function (role) {
          var opt = document.createElement('option');
          opt.value = role.role;
          opt.textContent = role.role + (role.data_kind === 'live' ? ' (live)' : '');
          roleSelect.appendChild(opt);
        });
        if (rolesData.length) updateRoleDependentFields();
      })
      .catch(function () {
        document.getElementById('qb-role').innerHTML = '<option>Could not load roles</option>';
      });
  }

  function updateRoleDependentFields() {
    var roleSelect = document.getElementById('qb-role');
    var role = rolesData.filter(function (r) { return r.role === roleSelect.value; })[0];
    if (!role) return;

    var periodSelect = document.getElementById('qb-period');
    periodSelect.innerHTML = '';
    role.available_periods.forEach(function (p) {
      var opt = document.createElement('option');
      opt.value = p;
      opt.textContent = p;
      if (p === role.default_period) opt.selected = true;
      periodSelect.appendChild(opt);
    });

    var formatWrap = document.getElementById('qb-formats');
    formatWrap.innerHTML = '';
    role.formats.forEach(function (fmt, i) {
      var label = el('label', 'filter-chip');
      var input = document.createElement('input');
      input.type = 'radio';
      input.name = 'qb-format';
      input.value = fmt;
      if (i === 0) input.checked = true;
      label.appendChild(input);
      label.appendChild(document.createTextNode(' ' + fmt));
      formatWrap.appendChild(label);
    });

    document.getElementById('qb-role-error').textContent = role.error ? 'Note: ' + role.error : '';
  }

  function loadArtifacts() {
    fetch('/api/artifacts?limit=15')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var list = document.getElementById('artifacts-list');
        list.innerHTML = '';
        var items = data.artifacts || [];
        if (!items.length) {
          list.appendChild(el('div', 'empty-note', 'No reports built yet.'));
          return;
        }
        items.forEach(function (a) {
          var row = document.createElement('a');
          row.className = 'artifact-row';
          row.href = '/artifacts/' + a.rel_path;
          row.target = '_blank';
          row.rel = 'noopener';
          row.appendChild(el('div', 'artifact-filename', a.filename));
          row.appendChild(el('div', 'artifact-role', a.role));
          list.appendChild(row);
        });
      });
  }

  function loadDoctor() {
    var pill = document.getElementById('doctor-pill');
    fetch('/api/doctor')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        pill.classList.toggle('doctor-ok', !!data.ok);
        pill.classList.toggle('doctor-fail', !data.ok);
        if (data.ok) {
          pill.textContent = 'All systems normal';
          pill.title = '';
        } else {
          var failing = (data.checks || []).filter(function (c) { return !c.passed; }).map(function (c) { return c.name; });
          pill.textContent = failing.length + ' check' + (failing.length === 1 ? '' : 's') + ' failing';
          pill.title = failing.join(', ');
        }
      })
      .catch(function () {
        pill.textContent = 'Status unavailable';
      });
  }

  function wireQuickBuild() {
    document.getElementById('qb-role').addEventListener('change', updateRoleDependentFields);
    document.getElementById('qb-build-btn').addEventListener('click', function () {
      var role = document.getElementById('qb-role').value;
      var period = document.getElementById('qb-period').value;
      var fmtInput = document.querySelector('input[name="qb-format"]:checked');
      var fmt = fmtInput ? fmtInput.value : 'doc';
      if (!role || !period) return;
      window.ODR_CHAT.sendComposed('Build the ' + role + ' ' + fmt + ' for ' + period + '.');
    });
  }

  function init() {
    window.ODR_CHAT.init();
    loadSkills();
    loadRoles().then(wireQuickBuild);
    loadArtifacts();
    loadDoctor();
  }

  window.ODR_APP = { refreshArtifacts: loadArtifacts };

  document.addEventListener('DOMContentLoaded', init);
})();
