'use strict';
// Proposals live separately from the immutable ROM reference data.
window.createKrushaPlanner = function (host) {
  const $ = id => document.getElementById(id);
  const types = {
    single: ['Single banana', 1, 4], bunch: ['Banana bunch (5)', 5, 4],
    balloon: ['Banana balloon (10)', 10, 100], coin: ['Gray coin', 0, 4],
    gb: ['Golden Banana', 0, 20], blueprint: ['Kasplat / blueprint', 0, 5],
    bonus: ['Bonus barrel (GB reward)', 0, 60], switch: ['Weapon switch', 0, 20],
    key: ['Recruitment key', 0, 20], supply: ['Shared supply', 0, 20],
    note: ['Other / planning note', 0, 20],
  };
  const draft = window.KRUSHA_DRAFT;
  const draftMode = !!draft && new URL(location).searchParams.get('draft') === draft.draft_id;
  // Draft edits have their own namespace. Original user plans are never seeded
  // over, silently merged, replaced or written by opening the draft URL.
  const storageKey = draftMode ? 'krusha-atlas-pins-' + draft.draft_id : 'krusha-atlas-pins-v2';
  if (draft) {
    $('draft-notice').hidden = false;
    $('draft-title').textContent = draftMode ? 'Assistant Draft 1 · review/edit' : 'Assistant placement draft available';
    $('draft-description').textContent = draftMode ? 'Proposed locations, not in the ROM. This draft has separate saved edits; your original plan is preserved. Check routes/doors/props in-game before approval.' : '700 bananas, 99 coins and 40 GB reward sites. Open the draft to inspect/edit it without replacing your original plan.';
    const u = new URL(location); u.searchParams.set('draft',draft.draft_id); $('open-assistant-draft').href = u;
    u.searchParams.delete('draft'); $('open-original-plan').href = u;
  }
  let pins = [], selectedId = null, moving = false, sequence = 0;
  const undo = [], redo = [];
  const clone = x => JSON.parse(JSON.stringify(x));
  const current = () => pins.find(p => p.id === selectedId);
  const message = text => { $('placement-status').textContent = text; };

  function normalize(p, legacy = false) {
    if (!p || typeof p.id !== 'string' || !p.id || !Number.isInteger(p.map) ||
        !host.catalog.some(m => m.id === p.map) || !Array.isArray(p.xyz) ||
        p.xyz.length !== 3 || !p.xyz.every(Number.isFinite) || typeof p.label !== 'string') {
      throw Error('A proposal needs a valid ID, map, label and three numeric coordinates.');
    }
    const kind = legacy ? 'note' : p.kind;
    const quantity = legacy ? 1 : p.quantity;
    if (!Object.hasOwn(types, kind) || !Number.isInteger(quantity) || quantity < 1 || quantity > 9999 ||
        (!legacy && typeof p.notes !== 'string')) throw Error('Invalid proposal type, quantity or notes.');
    return {id: p.id, map: p.map, map_name: host.catalog.find(m => m.id === p.map).name,
      label: p.label.slice(0, 500), kind, quantity, notes: legacy ? '' : p.notes.slice(0, 5000),
      xyz: [...p.xyz], status: 'proposal'};
  }

  let storageNotice = '';
  try {
    const saved = localStorage.getItem(storageKey);
    const legacy = !draftMode && saved === null;
    const data = saved !== null ? JSON.parse(saved) : draftMode ? draft.pins : JSON.parse(localStorage.getItem('krusha-atlas-pins-v1') ?? '[]');
    if (!Array.isArray(data)) throw Error('Unexpected autosave format.');
    pins = data.map(p => normalize(p, legacy));
    if (draftMode && saved === null) storageNotice = 'Loaded assistant Draft 1; edits are separate from your original plan. ';
    if (legacy && pins.length) storageNotice = `Recovered ${pins.length} older pins as planning notes. Original autosave preserved. `;
  } catch (e) {
    storageNotice = 'Browser autosave could not be read. Original storage was left intact; load an exported plan. ';
  }

  for (const id of ['brush-kind', 'edit-kind']) {
    for (const [key, spec] of Object.entries(types)) {
      const o = document.createElement('option'); o.value = key; o.textContent = spec[0]; $(id).append(o);
    }
  }
  function remember() {
    undo.push(clone(pins)); if (undo.length > 100) undo.shift(); redo.length = 0;
  }
  function persist() {
    try {
      localStorage.setItem(storageKey, JSON.stringify(pins));
      $('storage-status').textContent = storageNotice + 'Autosaved in this browser. Save plan JSON for a portable backup.';
    } catch {
      $('storage-status').textContent = 'Browser autosave unavailable. Save plan JSON to keep your work.';
    }
  }
  function changed() { persist(); render(); host.change(); }
  function controls() {
    $('undo').disabled = !undo.length; $('redo').disabled = !redo.length;
    $('move-proposal').disabled = host.style() !== 'A';
  }
  function editorContext() {
    const p = current(); if (!p) return;
    const [lo, hi] = host.height();
    $('editor-context').textContent = `${p.map_name} · ${p.id}` +
      (p.xyz[1] < lo || p.xyz[1] > hi ? ' · outside the current height band' : '');
  }
  function fillEditor() {
    const p = current(); $('proposal-editor').hidden = !p;
    if (!p) return;
    $('edit-label').value = p.label; $('edit-kind').value = p.kind; $('edit-quantity').value = p.quantity;
    for (const [i, axis] of ['x', 'y', 'z'].entries()) $('edit-' + axis).value = p.xyz[i];
    $('edit-notes').value = p.notes;
    editorContext();
    controls();
  }
  function select(id, focus = false) {
    selectedId = id; moving = false; fillEditor(); host.change();
    if (current()) message(current().label + ' selected. Edit its fields, or move/delete it.');
    if (focus && current()) host.focus(current().xyz);
  }
  function render() {
    controls();
    const map = host.map(); if (!map) return;
    const group = map.meta.group;
    const world = pins.filter(p => host.catalog.find(m => m.id === p.map).group === group);
    const bananas = world.reduce((n, p) => n + types[p.kind][1] * p.quantity, 0);
    const sum = kind => world.filter(p => p.kind === kind).reduce((n, p) => n + p.quantity, 0);
    const main = ['Jungle Japes','Angry Aztec','Frantic Factory','Gloomy Galleon','Fungi Forest','Crystal Caves','Creepy Castle'].includes(group);
    const isles = group === 'DK Isles', targets = main || isles;
    const rewards = sum('gb') + sum('bonus') + sum('blueprint');
    const totals = $('plan-totals'); totals.replaceChildren();
    const title = document.createElement('strong'); title.textContent = 'Draft totals · ' + group; totals.append(title);
    const counts = document.createElement('p');
    counts.textContent = `${bananas}${targets ? '/' + (main ? 100 : 0) : ''} bananas · ${rewards}${targets ? '/5' : ''} GB reward sites · ${sum('blueprint')}${targets ? '/1' : ''} blueprints · ${sum('coin')} coins`;
    if (targets && (bananas > (main ? 100 : 0) || rewards > 5 || sum('blueprint') > 1)) counts.className = 'over-budget';
    totals.append(counts);
    const help = document.createElement('p'); help.className = 'small';
    help.textContent = 'A bunch counts as 5 bananas; a balloon as 10. GB reward sites include bonus barrels and blueprint hand-ins: mark each reward once. These are proposed totals, not ROM edits.';
    totals.append(help);
    const global = document.createElement('p'); global.className = 'small';
    const n = kind => pins.filter(p => p.kind===kind).reduce((s,p)=>s+p.quantity,0);
    const objects=n('single')+n('bunch')+n('balloon')+n('coin');
    const units=n('single')+5*n('bunch')+10*n('balloon');
    global.textContent=`Campaign: ${units}/700 bananas · ${n('coin')}/99 coins · ${objects}/384 colored objects · ${n('gb')+n('bonus')+n('blueprint')}/40 GB sites · ${n('blueprint')}/8 blueprints`;
    if(units>700||n('coin')>99||objects>384)global.classList.add('over-budget');
    totals.append(global);
    const scope = $('list-scope').value;
    const list = $('pins'); list.replaceChildren();
    const included = pins.filter(p => scope === 'all' || (scope === 'world' ? world.includes(p) : p.map === map.meta.id));
    const summary = document.createElement('p'); summary.className = 'small';
    summary.textContent = `${included.length} proposals listed · ${pins.length} across the full plan`; list.append(summary);
    for (const p of included) {
      const row = document.createElement('button'); row.className = 'proposal-row'; row.type = 'button'; row.dataset.pinId = p.id;
      row.textContent = `${p.label} · ${types[p.kind][0]}${p.quantity > 1 ? ' ×' + p.quantity : ''} · (${p.xyz.join(', ')})` +
        (scope !== 'area' ? ' · ' + p.map_name : '');
      row.onclick = async () => { if (host.map().meta.id !== p.map) await host.openMap(p.map); select(p.id, true); };
      list.append(row);
    }
  }

  function palette() {
    const kind = $('brush-kind').value, quantity = Number($('brush-quantity').value);
    if (!Number.isInteger(quantity) || quantity < 1 || quantity > 9999) throw Error('Choose a whole number of objects from 1 to 9999.');
    return {kind, quantity};
  }
  function placeAt(x, z) {
    try {
      const map = host.map(); if (!map || host.style() !== 'A') return;
      const selected = current();
      const spec = moving && selected ? {kind: selected.kind, quantity: selected.quantity} : palette();
      let y, floorCount = 0;
      if ($('height-mode').value === 'manual') {
        if (!$('manual-y').value.trim()) throw Error('Enter a manual Y position.');
        y = Number($('manual-y').value);
      } else {
        if (!$('height-offset').value.trim()) throw Error('Enter the height above the floor.');
        const offset = Number($('height-offset').value);
        const surfaces = host.surfaces(x, z).filter(f => f + offset >= host.height()[0] && f + offset <= host.height()[1]);
        if (!surfaces.length) throw Error('No floor under this point in the height band. Narrow/change the band, or set Y manually for water or mid-air.');
        y = surfaces[0] + offset; floorCount = surfaces.length;
      }
      if (!Number.isFinite(y)) throw Error('Enter a valid height.');
      const xyz = [x, y, z].map(n => Math.round(n * 1000) / 1000);
      remember();
      let p;
      if (moving && selected) { selected.xyz = xyz; p = selected; moving = false; }
      else {
        const labels = new Set(pins.map(p => p.label));
        let label; do { label = 'K' + String(++sequence).padStart(3, '0'); } while (labels.has(label));
        p = {id: globalThis.crypto?.randomUUID?.() || 'pin-' + Date.now() + '-' + sequence,
          map: map.meta.id, map_name: map.meta.name, label, ...spec, notes: '', xyz, status: 'proposal'};
        pins.push(p);
      }
      selectedId = p.id; changed(); fillEditor();
      message(`${p.label}: ${types[p.kind][0]} at Y ${xyz[1]}.` +
        (floorCount > 1 ? ` Highest of ${floorCount} surfaces in the band; narrow the band to choose a lower floor.` : '') +
        ' Click more points to add; click a proposal to edit.');
    } catch (e) { message(e.message); }
  }
  $('brush-kind').onchange = () => { $('height-offset').value = types[$('brush-kind').value][2]; };
  $('height-mode').onchange = () => {
    const manual = $('height-mode').value === 'manual'; $('manual-label').hidden = !manual; $('offset-label').hidden = manual;
  };
  $('edit-proposal').onsubmit = e => {
    e.preventDefault(); const p = current(); if (!p) return;
    try {
      const candidate = normalize({...p, label: $('edit-label').value, kind: $('edit-kind').value,
        quantity: Number($('edit-quantity').value), notes: $('edit-notes').value,
        xyz: ['x','y','z'].map(a => Number($('edit-' + a).value))});
      if (!candidate.label.trim()) throw Error('Enter a label.');
      remember(); pins = pins.map(q => q.id === p.id ? candidate : q); changed(); fillEditor(); message(candidate.label + ' updated.');
    } catch (e) { message(e.message); }
  };
  $('move-proposal').onclick = () => { if (!current() || host.style() !== 'A') return; moving = true; $('place').checked = false; message('Click map A to move ' + current().label + '. Height follows the palette settings. Escape cancels.'); };
  $('delete-proposal').onclick = () => { if (!current()) return; remember(); pins = pins.filter(p => p.id !== selectedId); selectedId = null; moving = false; changed(); fillEditor(); message('Proposal deleted. Undo can restore it.'); };
  $('close-editor').onclick = () => select(null);
  $('list-scope').onchange = render;
  for (const [id, from, to] of [['undo',undo,redo], ['redo',redo,undo]]) $(id).onclick = () => {
    if (!from.length) return; to.push(clone(pins)); pins = from.pop(); moving = false; if (!current()) selectedId = null; changed(); fillEditor(); message(id === 'undo' ? 'Last change undone.' : 'Change restored.');
  };
  document.addEventListener('keydown', e => { if (e.key === 'Escape') { moving = false; $('place').checked = false; message('Placement cancelled. Existing proposals kept.'); } });
  $('export').onclick = () => {
    host.download(new Blob([JSON.stringify({format:'krusha-atlas-notes-v2', source_sha1:host.sourceSha1, pins},null,2)], {type:'application/json'}), draftMode ? 'krusha-assistant-draft-edited.json' : 'krusha-placement-plan.json');
    $('storage-status').textContent = 'Plan export requested. Keep the downloaded JSON to reopen or share the plan.';
  };
  $('import').onchange = async e => {
    try {
      const file = e.target.files[0]; if (!file) return;
      const data = JSON.parse(await file.text());
      if (!['krusha-atlas-notes-v1','krusha-atlas-notes-v2'].includes(data.format) || data.source_sha1 !== host.sourceSha1 || !Array.isArray(data.pins)) throw Error('Choose a matching atlas plan/notes file for the original USA ROM.');
      const loaded = data.pins.map(p => normalize(p, data.format.endsWith('v1')));
      if (new Set(loaded.map(p => p.id)).size !== loaded.length) throw Error('The loaded file has duplicate proposal IDs.');
      const merged = new Map(pins.map(p => [p.id,p])); let added = 0, replaced = 0, kept = 0;
      for (const p of loaded) {
        if (!merged.has(p.id)) { merged.set(p.id,p); added++; }
        else if ($('import-policy').value === 'replace') { merged.set(p.id,p); replaced++; }
        else kept++;
      }
      remember(); pins = [...merged.values()]; changed(); fillEditor();
      message(`Loaded plan: ${added} added, ${replaced} updated, ${kept} current edits kept. Undo can restore the previous plan.`);
    } catch (e) { message('Load failed: ' + e.message + ' Existing proposals kept.'); }
    finally { $('import').value = ''; }
  };
  $('storage-status').textContent = storageNotice + 'Autosave stays in this browser; save plan JSON for a portable backup.';
  return {
    all: () => pins, current, moving: () => moving, select, placeAt, types,
    mapChanged() { moving = false; if (current()?.map !== host.map()?.meta.id) selectedId = null; render(); fillEditor(); },
    viewChanged() { if (host.style() !== 'A') moving = false; controls(); },
    bandChanged() { render(); editorContext(); },
    message,
  };
};
