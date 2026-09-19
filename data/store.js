/* PN.store — 小南瓜數位筆記的資料層（雙模式）
   ────────────────────────────────────────────────────────────
   ① Supabase 模式：data/config.js 有真的 anon key → 登入、真資料、Realtime。
   ② 示範模式    ：沒有 key（或 CDN 載不到）→ data/reports.js ＋ localStorage，
                    file:// 雙擊直開也能看，不會噴錯。

   介面名稱跟 Phase 1 完全一樣，只是「會改資料的」都改成回 Promise：
     ready() / all() / get(slug) / shelves() / profiles() / tagFamilies()
     favs() / isFav(slug) / toggleFav(slug)
     reads() / isRead(slug) / markRead(slug) / getTakeaway(slug) / setTakeaway(slug,t)
     shares() / getShare(slug) / share(slug,note) / unshare(slug) / canShare(slug)
     jobs() / addJob(j) / patchJob(id,patch) / dropJob(id) / watchJobs(cb)
     me() / setMe(patch) / noteUrl(slug) / refresh()
   讀的部分一律同步（讀記憶體快取），所以畫面程式碼不用改寫成 async。
   另外附：PN.auth（登入）、PN.theme（日夜切換）、PN.dots（互動點格背景）。
*/
window.PN = window.PN || {};
(function () {
  var CFG = window.PN_CONFIG || {};
  var SB_CDN = 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/dist/umd/supabase.min.js';
  /* 佔位符（__ANON_KEY__）或太短的字串都當作「還沒填」 */
  var hasKey = !!(CFG.url && CFG.anonKey && CFG.anonKey.indexOf('__') !== 0 && CFG.anonKey.length > 20);
  var sb = null;
  PN.mode = hasKey ? 'supabase' : 'demo';

  var K = { theme: 'pnTheme', fav: 'pnFav', read: 'pnRead', share: 'pnShare', jobs: 'pnJobs', me: 'pnMe', trash: 'pnTrash', cover: 'pnCover', shelfNames: 'pnShelfNames', tagRename: 'pnTagRename' };
  function rd(k, d) { try { var v = JSON.parse(localStorage.getItem(k)); return v == null ? d : v; } catch (e) { return d; } }
  function wr(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }
  function D() { return window.PN_DATA || { reports: [], bySlug: {}, shelves: [], tagFamilies: [], profiles: [] }; }
  function warn(m, e) { console.warn('[小南瓜] ' + m, e && (e.message || e)); }

  /* ── 記憶體快取：畫面全部從這裡讀 ───────────────────────────── */
  var C = {
    user: null, profile: null, allowed: true, offline: true,
    notes: [], bySlug: {}, byId: {}, favs: [], reads: {}, jobs: [],
    profiles: [], profById: {}, roster: {}, shelves: [], chan: null
  };
  PN.cache = C;

  /* ── 小工具 ─────────────────────────────────────────────────── */
  function p2(n) { return (n < 10 ? '0' : '') + n; }
  function mmss(s) {
    s = Math.max(0, Math.round(s || 0));
    var h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), x = s % 60;
    return h ? h + ':' + p2(m) + ':' + p2(x) : m + ':' + p2(x);
  }
  function shelfMeta(id) {
    for (var i = 0; i < C.shelves.length; i++) if (C.shelves[i].id === id) return C.shelves[i];
    return { id: id || '', name: id || '未分類', sections: [], n: 0 };
  }
  function coverUrl(p, v) {
    if (!p) return '';
    if (/^(https?:|data:)/i.test(p)) return p;
    if (p.indexOf('covers/') === 0) return p;                        /* 本站靜態封面 */
    return CFG.url + '/storage/v1/object/public/covers/' + p + (v ? '?v=' + encodeURIComponent(v) : '');  /* Storage 公開桶 */
  }
  /* 換封面用：把圖縮到 maxW 寬、轉 JPEG，卡片才不會肥 */
  function shrink(file, maxW, q) {
    return new Promise(function (res, rej) {
      var img = new Image(), url = URL.createObjectURL(file);
      img.onload = function () {
        var w = Math.min(maxW, img.naturalWidth), h = Math.round(img.naturalHeight * w / img.naturalWidth);
        var c = document.createElement('canvas'); c.width = w; c.height = h;
        c.getContext('2d').drawImage(img, 0, 0, w, h); URL.revokeObjectURL(url);
        c.toBlob(function (b) { b ? res(b) : rej(new Error('壓不了圖')); }, 'image/jpeg', q);
      };
      img.onerror = function () { URL.revokeObjectURL(url); rej(new Error('讀不了這張圖')); };
      img.src = url;
    });
  }
  function blobToDataURL(b) { return new Promise(function (res) { var fr = new FileReader(); fr.onload = function () { res(fr.result); }; fr.readAsDataURL(b); }); }
  function staticPath(p) { return (p || '').indexOf('static:') === 0 ? p.slice(7) : ''; }
  function nowISO() { return new Date().toISOString(); }
  function uid() { return C.user ? C.user.id : ''; }
  function myEmail() { return ((C.user && C.user.email) || '').toLowerCase(); }
  function idOf(slug) { var r = C.bySlug[slug]; return r ? r.id : ''; }

  function ownerName(row) {
    if (row.owner_id && C.profById[row.owner_id]) return C.profById[row.owner_id].name;
    var e = (row.owner_email || '').toLowerCase();
    if (e && C.roster[e]) return C.roster[e].name;
    if (e) return e.split('@')[0];
    return '南瓜';
  }

  /* notes 的一列 → 畫面用的筆記物件（欄位名沿用 Phase 1 的 reports.js） */
  function fromRow(n) {
    var sm = shelfMeta(n.shelf), secName = '';
    (sm.sections || []).forEach(function (s) { if (s.id === n.section) secName = s.name; });
    var stat = staticPath(n.html_path);
    var tags = n.tags || [], kw = n.keywords || [];
    var r = {
      id: n.id, slug: n.slug,
      file: stat || ('#open?slug=' + encodeURIComponent(n.slug)),
      needUrl: !stat, htmlPath: n.html_path || '',
      title: n.title || '', speaker: n.speaker || '',
      shelf: n.shelf || '', shelfName: sm.name, section: n.section || '', sectionName: secName,
      source: n.source_kind || '', sourceUrl: n.source_url || '',
      duration: mmss(n.duration_sec), durationSec: n.duration_sec || 0,
      date: (n.created_at || '').slice(0, 10),
      summary: n.summary || '', cover: coverUrl(n.cover_path, n.updated_at),
      deletedAt: n.deleted_at || '', deletedBy: n.deleted_by_name || '',
      tags: tags, keywords: kw, glossary: [], headings: [], figs: 0,
      level: n.level || '', readMin: n.read_min || 0,
      ownerId: n.owner_id || '', ownerEmail: (n.owner_email || '').toLowerCase(),
      owner: ownerName(n),
      visibility: n.visibility || 'private',
      sharedAt: n.shared_at || '', sharedNote: n.shared_note || ''
    };
    r.hay = [r.title, r.speaker, r.summary, r.shelfName, r.level, r.owner]
      .concat(tags).concat(kw).join(' ').toLowerCase();
    return r;
  }

  /* 重算索引：bySlug／byId ＋ 每個書架的篇數與場次 */
  function reindex() {
    C.bySlug = {}; C.byId = {};
    C.shelves.forEach(function (s) { s.n = 0; if (!s.sections) s.sections = []; });
    C.notes.forEach(function (r) {
      C.bySlug[r.slug] = r; if (r.id) C.byId[r.id] = r;
      var s = shelfMeta(r.shelf);
      if (s.id) {
        s.n = (s.n || 0) + 1;
        if (r.section && !s.sections.some(function (x) { return x.id === r.section; }))
          s.sections.push({ id: r.section, name: r.sectionName || r.section });
      }
    });
  }

  /* ── 示範模式（也是 Supabase 模式未登入時的畫面來源） ───────── */
  function useOffline(teamOnly) {
    var d = D();
    C.offline = true;
    C.shelves = JSON.parse(JSON.stringify(d.shelves || []));
    C.notes = (d.reports || []).filter(function (r) { return !teamOnly || r.visibility === 'team'; })
      .map(function (r) { var c = Object.assign({}, r); c.needUrl = false; c.owner = c.owner || 'terry'; return c; });
    if (PN.mode === 'demo') {                 /* 示範模式：垃圾桶與自訂封面都在這台瀏覽器 */
      var tr = rd(K.trash, {}), cv = rd(K.cover, {});
      C.notes.forEach(function (c) { if (tr[c.slug]) { c.deletedAt = tr[c.slug].at; c.deletedBy = tr[c.slug].by; } if (cv[c.slug]) c.cover = cv[c.slug]; });
      var sn = rd(K.shelfNames, {}), tm = rd(K.tagRename, {});
      C.shelves.forEach(function (s) { if (sn[s.id]) s.name = sn[s.id]; });
      C.notes.forEach(function (c) {
        if (sn[c.shelf]) c.shelfName = sn[c.shelf];
        c.tags = (c.tags || []).map(function (t) { return tm[t] || t; });
      });
    }
    C.profiles = (d.profiles || []).map(function (p) { return Object.assign({}, p); });
    C.profById = {}; C.profiles.forEach(function (p) { C.profById[p.slug] = p; });
    C.favs = rd(K.fav, []);
    C.reads = rd(K.read, {});
    C.jobs = rd(K.jobs, []);
    reindex();
  }

  /* ── 載入 supabase-js（只有真的有 key 才去抓 CDN，離線也不會噴紅字） ── */
  function loadLib() {
    if (window.supabase && window.supabase.createClient) return Promise.resolve();
    return new Promise(function (res, rej) {
      var s = document.createElement('script');
      s.src = SB_CDN; s.async = true;
      s.onload = function () { res(); };
      s.onerror = function () { rej(new Error('CDN 載不到 supabase-js')); };
      document.head.appendChild(s);
    });
  }

  /* ── 從 Supabase 撈資料（每支都自己吞錯，不讓畫面掛掉） ────────── */
  function q(builder, label) {
    return Promise.resolve(builder).then(function (r) {
      if (r && r.error) { warn('讀不到 ' + label + '：' + r.error.message); return []; }
      return (r && r.data) || [];
    }, function (e) { warn('讀 ' + label + ' 出錯', e); return []; });
  }

  function loadProfiles() {
    return q(sb.from('profiles').select('id,email,display_name,department,title,avatar_url,role'), 'profiles')
      .then(function (rows) {
        C.profiles = rows.map(function (p) {
          return {
            slug: p.id, id: p.id, email: p.email,
            name: p.display_name || (p.email || '').split('@')[0],
            department: p.department || '', title: p.title || '',
            avatar: p.avatar_url || '', role: p.role || 'member', demo: false
          };
        });
        C.profById = {}; C.profiles.forEach(function (p) { C.profById[p.id] = p; });
        C.profile = C.profById[uid()] || null;
        C.allowed = !!C.profile;          /* 讀不到自己的 profile ＝ 不在名單上 */
      });
  }
  function loadRoster() {
    return q(sb.from('roster').select('email,display_name,department,title'), 'roster')
      .then(function (rows) {
        C.roster = {};
        rows.forEach(function (r) {
          C.roster[(r.email || '').toLowerCase()] =
            { name: r.display_name || '', department: r.department || '', title: r.title || '' };
        });
      });
  }
  function loadShelves() {
    return q(sb.from('shelves').select('id,name,emoji,description,sort').order('sort'), 'shelves')
      .then(function (rows) {
        C.shelves = rows.map(function (s) {
          return { id: s.id, name: s.name, emoji: s.emoji || '', desc: s.description || '', sections: [], n: 0 };
        });
        if (!C.shelves.length) C.shelves = JSON.parse(JSON.stringify(D().shelves || []));
      });
  }
  function loadNotes() {
    return q(sb.from('notes').select('*').order('created_at', { ascending: false }), 'notes')
      .then(function (rows) { C.notes = rows.map(fromRow); reindex(); });
  }
  function loadFavs() {
    return q(sb.from('favorites').select('note_id').eq('user_id', uid()), 'favorites')
      .then(function (rows) {
        C.favs = rows.map(function (f) { var r = C.byId[f.note_id]; return r ? r.slug : null; })
          .filter(Boolean);
      });
  }
  function loadReads() {
    return q(sb.from('reads').select('note_id,my_takeaway,read_at').eq('user_id', uid()), 'reads')
      .then(function (rows) {
        C.reads = {};
        rows.forEach(function (x) {
          var r = C.byId[x.note_id]; if (!r) return;
          C.reads[r.slug] = { read_at: x.read_at, my_takeaway: x.my_takeaway || '' };
        });
      });
  }

  var STEP_OF = { queued: 0, prepping: 1, writing: 2, checking: 3, publishing: 3, done: 4, failed: 0 };
  function jobRow(j) {
    var note = j.note_id && C.byId[j.note_id];
    return {
      id: j.id, url: j.source_url || '', filename: (j.upload_path || '').split('/').pop() || '',
      shelf: j.shelf || '', shelfName: shelfMeta(j.shelf).name, level: j.level || '',
      share: !!j.auto_share, status: j.status, step: STEP_OF[j.status] || 0,
      /* worker 還沒上線：卡在 queued 的單就不要跑假動畫 */
      stalled: j.status === 'queued', msg: j.progress_msg || '',
      noteSlug: note ? note.slug : '', created_at: j.created_at
    };
  }
  function loadJobs() {
    return q(sb.from('jobs').select('*').eq('owner_id', uid()).order('created_at', { ascending: false }), 'jobs')
      .then(function (rows) { C.jobs = rows.map(jobRow); });
  }

  /* 登入後把所有東西撈一輪 */
  function loadAll() {
    if (!C.user) { useOffline(true); return Promise.resolve(); }
    return Promise.all([loadProfiles(), loadRoster(), loadShelves()])
      .then(function () { return loadNotes(); })
      .then(function () { return Promise.all([loadFavs(), loadReads(), loadJobs()]); })
      .then(function () { C.offline = false; });
  }

  /* ── 起手式 ─────────────────────────────────────────────────── */
  var booted = null;
  function boot() {
    if (booted) return booted;
    if (!hasKey) { useOffline(false); booted = Promise.resolve(store); return booted; }
    booted = loadLib().then(function () {
      sb = window.supabase.createClient(CFG.url, CFG.anonKey, {
        auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true, flowType: 'implicit' }  /* implicit：信裡的連結在任何瀏覽器點都能登入 */
      });
      PN.sb = sb;
      return sb.auth.getSession();
    }).then(function (res) {
      C.user = (res && res.data && res.data.session && res.data.session.user) || null;
      /* 從信件連結進來：網址上的 token 已被讀走，清掉免得被當成路由 */
      var em = location.hash.match(/error_description=([^&]+)/);
      if (em) { PN.authError = decodeURIComponent(em[1].replace(/\+/g, ' ')); try { console.warn('登入失敗：' + PN.authError); } catch (e) {} }
      if (/access_token=|refresh_token=|error=|type=(signup|magiclink|recovery)/.test(location.hash)) { try { history.replaceState(null, '', location.pathname + '#library'); } catch (e) { location.hash = 'library'; } }
      return loadAll();
    }).catch(function (e) {
      warn('連不上 Supabase，先用離線資料', e);
      PN.mode = 'demo'; sb = null; useOffline(false);
    }).then(function () { return store; });
    return booted;
  }
  function live() { return PN.mode === 'supabase' && !!sb && !!C.user; }

  /* ── PN.store 本體 ──────────────────────────────────────────── */
  var store = {
    /* 起手式：畫面在 render 之前先 await 這個 */
    ready: function () { return boot(); },
    refresh: function () { return loadAll(); },
    mode: function () { return PN.mode; },
    isOffline: function () { return C.offline; },

    /* ── 讀（同步，全部從快取拿） ── */
    all: function () { return C.notes.filter(function (r) { return !r.deletedAt; }); },
    get: function (slug) { return C.bySlug[slug] || (D().bySlug || {})[slug] || null; },
    shelves: function () { return C.shelves; },
    profiles: function () { return C.profiles; },
    tagFamilies: function () { return D().tagFamilies || []; },

    /* ── 我的最愛 ── */
    favs: function () { return C.favs.slice(); },
    isFav: function (s) { return C.favs.indexOf(s) >= 0; },
    toggleFav: function (s) {
      var on = !this.isFav(s);
      if (on) C.favs.push(s); else C.favs = C.favs.filter(function (x) { return x !== s; });
      if (!live()) { wr(K.fav, C.favs); return Promise.resolve(on); }
      var id = idOf(s); if (!id) return Promise.resolve(on);
      var op = on
        ? sb.from('favorites').insert({ user_id: uid(), note_id: id })
        : sb.from('favorites').delete().eq('user_id', uid()).eq('note_id', id);
      return Promise.resolve(op).then(function (r) {
        if (r && r.error) warn('存不了最愛：' + r.error.message);
        return on;
      }, function (e) { warn('存不了最愛', e); return on; });
    },

    /* ── 書架與標籤改名（owner；示範模式存瀏覽器） ── */
    canManage: function () {
      if (PN.mode === 'demo') return true;
      return live() && !!C.profile && C.profile.role === 'owner';
    },
    vocab: function () {
      var out = {};
      C.notes.forEach(function (r) {
        (r.tags || []).forEach(function (t) {
          var i = t.indexOf('/'); if (i < 0) return;
          var f = t.slice(0, i), v = t.slice(i + 1);
          (out[f] = out[f] || []); if (out[f].indexOf(v) < 0) out[f].push(v);
        });
      });
      Object.keys(out).forEach(function (f) { out[f].sort(); });
      return out;
    },
    renameShelf: function (id, name) {
      C.shelves.forEach(function (s) { if (s.id === id) s.name = name; });
      C.notes.forEach(function (r) { if (r.shelf === id) r.shelfName = name; });
      if (!live()) { var sn = rd(K.shelfNames, {}); sn[id] = name; wr(K.shelfNames, sn); return Promise.resolve(true); }
      return Promise.resolve(sb.from('shelves').update({ name: name }).eq('id', id))
        .then(function (x) { if (x && x.error) { warn('書架改名失敗：' + x.error.message); return false; } return true; },
          function (e) { warn('書架改名失敗', e); return false; });
    },
    renameTag: function (family, oldV, newV) {
      var from = family + '/' + oldV, to = family + '/' + newV;
      C.notes.forEach(function (r) { r.tags = (r.tags || []).map(function (t) { return t === from ? to : t; }); });
      if (!live()) { var tm = rd(K.tagRename, {}); tm[from] = to; wr(K.tagRename, tm); return Promise.resolve(true); }
      return Promise.resolve(sb.rpc('rename_tag', { p_family: family, p_old: oldV, p_new: newV }))
        .then(function (x) { if (x && x.error) { warn('標籤改名失敗：' + x.error.message); return false; } return true; },
          function (e) { warn('標籤改名失敗', e); return false; });
    },

    /* ── 垃圾桶（保留 14 天；團隊共筆的話夥伴都能復原） ── */
    trash: function () {
      var now = Date.now();
      return C.notes.filter(function (r) { return !!r.deletedAt; }).map(function (r) {
        r.daysLeft = Math.max(0, 14 - Math.floor((now - new Date(r.deletedAt).getTime()) / 864e5)); return r;
      }).filter(function (r) { return r.daysLeft > 0; })
        .sort(function (a, b) { return (b.deletedAt || '').localeCompare(a.deletedAt || ''); });
    },
    canDelete: function (s) { return this.canShare(s); },
    canRestore: function (s) { var r = C.bySlug[s]; return !!r && (this.canShare(s) || r.visibility === 'team'); },
    trashNote: function (s) {
      var r = C.bySlug[s]; if (!r) return Promise.resolve(false);
      var at = nowISO(), by = (this.me() || {}).name || '我';
      r.deletedAt = at; r.deletedBy = by;
      if (!live()) { var t = rd(K.trash, {}); t[s] = { at: at, by: by }; wr(K.trash, t); return Promise.resolve(true); }
      return Promise.resolve(sb.from('notes').update({ deleted_at: at, deleted_by: uid(), deleted_by_name: by }).eq('slug', s))
        .then(function (x) { if (x && x.error) { warn('刪不掉：' + x.error.message); r.deletedAt = ''; return false; } return true; },
          function (e) { warn('刪不掉', e); r.deletedAt = ''; return false; });
    },
    restoreNote: function (s) {
      var r = C.bySlug[s]; if (!r) return Promise.resolve(false);
      var was = r.deletedAt; r.deletedAt = ''; r.deletedBy = '';
      if (!live()) { var t = rd(K.trash, {}); delete t[s]; wr(K.trash, t); return Promise.resolve(true); }
      return Promise.resolve(sb.from('notes').update({ deleted_at: null, deleted_by: null, deleted_by_name: null }).eq('slug', s))
        .then(function (x) { if (x && x.error) { warn('復原失敗：' + x.error.message); r.deletedAt = was; return false; } return true; },
          function (e) { warn('復原失敗', e); r.deletedAt = was; return false; });
    },

    /* ── 自訂封面（整理者可以自己換） ── */
    setCover: function (s, file) {
      var r = C.bySlug[s]; if (!r || !file) return Promise.resolve(false);
      return shrink(file, 640, 0.82).then(function (blob) {
        if (!live()) {
          return blobToDataURL(blob).then(function (u) { var c = rd(K.cover, {}); c[s] = u; wr(K.cover, c); r.cover = u; return true; });
        }
        var path = uid() + '/' + s + '.jpg';
        return Promise.resolve(sb.storage.from('covers').upload(path, blob, { upsert: true, contentType: 'image/jpeg' }))
          .then(function (x) {
            if (x && x.error) { warn('封面上傳失敗：' + x.error.message); return false; }
            return Promise.resolve(sb.from('notes').update({ cover_path: path }).eq('slug', s)).then(function (y) {
              if (y && y.error) { warn('封面存不進筆記：' + y.error.message); return false; }
              r.cover = coverUrl(path, nowISO()); return true;
            });
          });
      }, function (e) { warn(e.message || '封面處理失敗'); return false; });
    },

    /* ── 已讀 ＋ 我的一句話 ── */
    reads: function () { return C.reads; },
    isRead: function (s) { return !!C.reads[s]; },
    markRead: function (s) {
      var was = C.reads[s] || {};
      C.reads[s] = { read_at: nowISO(), my_takeaway: was.my_takeaway || '' };
      if (!live()) { wr(K.read, C.reads); return Promise.resolve(); }
      var id = idOf(s); if (!id) return Promise.resolve();
      return Promise.resolve(
        sb.from('reads').upsert({ user_id: uid(), note_id: id, read_at: nowISO() },
          { onConflict: 'user_id,note_id' })
      ).then(function (r) { if (r && r.error) warn('記不了已讀：' + r.error.message); },
        function (e) { warn('記不了已讀', e); });
    },
    getTakeaway: function (s) { return (C.reads[s] || {}).my_takeaway || ''; },
    setTakeaway: function (s, t) {
      C.reads[s] = C.reads[s] || { read_at: nowISO() };
      C.reads[s].my_takeaway = t;
      if (!live()) { wr(K.read, C.reads); return Promise.resolve(); }
      var id = idOf(s); if (!id) return Promise.resolve();
      return Promise.resolve(
        sb.from('reads').upsert({ user_id: uid(), note_id: id, my_takeaway: t },
          { onConflict: 'user_id,note_id' })
      ).then(function (r) { if (r && r.error) warn('存不了一句話：' + r.error.message); },
        function (e) { warn('存不了一句話', e); });
    },

    /* ── 團隊共筆（分享／收回） ── */
    shares: function () {
      /* 只有純示範模式才看 localStorage；接了 Supabase 就一律看筆記自己的 visibility */
      if (PN.mode === 'demo') return rd(K.share, {});
      var out = {};
      C.notes.forEach(function (r) {
        if (r.visibility === 'team')
          out[r.slug] = { note: r.sharedNote, shared_at: r.sharedAt || r.date, by: r.ownerId || r.ownerEmail };
      });
      return out;
    },
    getShare: function (s) { return this.shares()[s] || null; },
    /* 只有擁有者（或 owner_id 還是空、owner_email 是自己的種子筆記）能分享 */
    canShare: function (s) {
      if (PN.mode === 'supabase' && !live()) return false;   /* 還沒登入就別給分享 */
      if (!live()) return true;                              /* 示範模式：怎麼玩都行 */
      var r = C.bySlug[s]; if (!r) return false;
      if (r.ownerId) return r.ownerId === uid();
      return !!r.ownerEmail && r.ownerEmail === myEmail();
    },
    share: function (s, note) {
      var at = nowISO(), r = C.bySlug[s];
      if (r) { r.visibility = 'team'; r.sharedAt = at; r.sharedNote = note || ''; }
      if (!live()) {
        if (PN.mode === 'demo') {
          var h = rd(K.share, {});
          h[s] = { note: note || '', shared_at: at, by: this.me().slug };
          wr(K.share, h);
        }
        return Promise.resolve();
      }
      return Promise.resolve(
        sb.from('notes').update({ visibility: 'team', shared_at: at, shared_note: note || '' }).eq('slug', s)
      ).then(function (x) { if (x && x.error) warn('分享失敗：' + x.error.message); },
        function (e) { warn('分享失敗', e); });
    },
    unshare: function (s) {
      var r = C.bySlug[s];
      if (r) { r.visibility = 'private'; r.sharedAt = ''; r.sharedNote = ''; }
      if (!live()) {
        if (PN.mode === 'demo') { var h = rd(K.share, {}); delete h[s]; wr(K.share, h); }
        return Promise.resolve();
      }
      return Promise.resolve(
        sb.from('notes').update({ visibility: 'private', shared_at: null, shared_note: '' }).eq('slug', s)
      ).then(function (x) { if (x && x.error) warn('收回失敗：' + x.error.message); },
        function (e) { warn('收回失敗', e); });
    },

    /* ── 收件匣排隊單 ── */
    jobs: function () { return C.jobs.slice(); },
    addJob: function (j) {
      if (!live()) {
        j.id = 'j' + Date.now() + Math.floor(Math.random() * 1000);
        j.created_at = nowISO();
        C.jobs.unshift(j); wr(K.jobs, C.jobs);
        return Promise.resolve(j);
      }
      var row = {
        owner_id: uid(), source_url: j.url || null,
        source_kind: j.url ? (/youtu\.?be/i.test(j.url) ? 'youtube' : 'platform') : 'local',
        upload_path: j.filename || null, shelf: j.shelf || null, level: j.level || null,
        auto_share: !!j.share, status: 'queued', progress_msg: '排隊中'
      };
      return Promise.resolve(sb.from('jobs').insert(row).select().single())
        .then(function (r) {
          if (r && r.error) { warn('排不進收件匣：' + r.error.message); return null; }
          var m = jobRow(r.data); C.jobs.unshift(m); return m;
        }, function (e) { warn('排不進收件匣', e); return null; });
    },
    patchJob: function (id, patch) {
      C.jobs.forEach(function (x) { if (x.id === id) for (var k in patch) x[k] = patch[k]; });
      if (!live()) { wr(K.jobs, C.jobs); return Promise.resolve(); }
      var row = {};
      if (patch.status) row.status = patch.status;
      if (patch.msg) row.progress_msg = patch.msg;
      if (!Object.keys(row).length) return Promise.resolve();
      return Promise.resolve(sb.from('jobs').update(row).eq('id', id))
        .then(function () {}, function (e) { warn('更新排隊單失敗', e); });
    },
    dropJob: function (id) {
      C.jobs = C.jobs.filter(function (j) { return j.id !== id; });
      if (!live()) { wr(K.jobs, C.jobs); return Promise.resolve(); }
      return Promise.resolve(sb.from('jobs').delete().eq('id', id))
        .then(function () {}, function (e) { warn('移除排隊單失敗', e); });
    },
    /* Realtime：自己的 jobs 有動靜就重抓一次並回呼 */
    watchJobs: function (cb) {
      if (!live() || C.chan) return function () {};
      C.chan = sb.channel('pn-jobs-' + uid())
        .on('postgres_changes',
          { event: '*', schema: 'public', table: 'jobs', filter: 'owner_id=eq.' + uid() },
          function () { loadJobs().then(function () { try { cb && cb(); } catch (e) {} }); })
        .subscribe();
      return function () { try { sb.removeChannel(C.chan); } catch (e) {} C.chan = null; };
    },

    /* ── 我 ── */
    me: function () {
      if (live() && C.profile) return C.profile;
      var d = C.profiles[0] || { slug: 'terry', name: '南瓜', department: '管理層', title: '共同創辦人／美術總監' };
      return Object.assign({}, d, rd(K.me, {}));
    },
    setMe: function (p) {
      if (!live()) { wr(K.me, Object.assign(rd(K.me, {}), p)); return Promise.resolve(); }
      if (C.profile) Object.assign(C.profile, p);
      return Promise.resolve(
        sb.from('profiles').update({
          display_name: p.name, department: p.department || '', title: p.title || ''
        }).eq('id', uid())
      ).then(function (r) { if (r && r.error) warn('存不了個人設定：' + r.error.message); },
        function (e) { warn('存不了個人設定', e); });
    },

    /* 存在 Storage 的報告要先換成 1 小時簽名網址；靜態檔直接回相對路徑 */
    noteUrl: function (slug) {
      var r = this.get(slug);
      if (!r) return Promise.resolve('');
      if (!r.needUrl) return Promise.resolve(r.file);
      if (!live()) return Promise.resolve('');
      var path = (r.htmlPath || '').replace(/^notes\//, '');
      return Promise.resolve(sb.storage.from('notes').createSignedUrl(path, 3600))
        .then(function (x) { return (x && x.data && x.data.signedUrl) || ''; },
          function (e) { warn('拿不到報告網址', e); return ''; });
    }
  };
  PN.store = store;

  /* ── PN.auth：登入／登出 ────────────────────────────────────── */
  PN.auth = {
    live: function () { return PN.mode === 'supabase' && !!sb; },
    user: function () { return C.user; },
    profile: function () { return C.profile; },
    /* 登入了但讀不到自己的 profile ＝ 信箱不在名單上 */
    allowed: function () { return !C.user || C.allowed; },
    notAllowedMsg: '這個信箱還沒在名單上。請南瓜幫你加一下。',
    /* 本機開發就回本機，正式站才用 config 的 siteUrl（Supabase 的 Redirect URLs 兩個都要填） */
    redirectTo: function () {
      var here = location.origin + location.pathname;
      if (/^https?:\/\/(localhost|127\.0\.0\.1)/.test(location.origin)) return here;
      return CFG.siteUrl || here;
    },
    signInGoogle: function () {
      if (!this.live()) return Promise.reject(new Error('示範模式沒有真的登入'));
      return sb.auth.signInWithOAuth({ provider: 'google', options: { redirectTo: this.redirectTo() } })
        .then(function (r) { if (r && r.error) throw r.error; return r; });
    },
    signInEmail: function (email) {
      if (!this.live()) return Promise.reject(new Error('示範模式沒有真的登入'));
      return sb.auth.signInWithOtp({ email: email, options: { emailRedirectTo: this.redirectTo() } })
        .then(function (r) { if (r && r.error) throw r.error; return r; });
    },
    signOut: function () {
      if (!this.live()) return Promise.resolve();
      return Promise.resolve(sb.auth.signOut()).then(function () { C.user = null; C.profile = null; });
    },
    /* 登入狀態一變（含 magic link 回站）就重抓資料，再通知畫面重畫 */
    onChange: function (cb) {
      if (!this.live()) return;
      sb.auth.onAuthStateChange(function (evt, session) {
        var u = (session && session.user) || null;
        var same = (u && C.user && u.id === C.user.id) || (!u && !C.user);
        C.user = u;
        if (same && evt !== 'SIGNED_IN') return;
        loadAll().then(function () { try { cb && cb(evt); } catch (e) {} });
      });
    }
  };

  /* ── 日／夜切換：首頁與報告頁共用 localStorage.pnTheme ── */
  PN.theme = {
    get: function () {
      var t = null; try { t = localStorage.getItem(K.theme); } catch (e) {}
      return t || (matchMedia('(prefers-color-scheme: dark)').matches ? 'night' : 'day');
    },
    set: function (t) {
      document.body.setAttribute('data-theme', t);
      try { localStorage.setItem(K.theme, t); } catch (e) {}
      document.dispatchEvent(new CustomEvent('pn:theme', { detail: t }));
    },
    toggle: function () { this.set(this.get() === 'night' ? 'day' : 'night'); },
    apply: function () { this.set(this.get()); }
  };

  /* ── 互動點格背景：滑鼠 140px 內的點會變亮變大（不用金色） ── */
  PN.dots = function (cv) {
    if (!cv) return;
    var ctx = cv.getContext('2d'), w = 0, h = 0, dpr = Math.min(devicePixelRatio || 1, 2);
    var mx = -999, my = -999, R = 140, GAP = 24, raf = 0, still = matchMedia('(prefers-reduced-motion: reduce)').matches;
    function ink() { return document.body.getAttribute('data-theme') === 'night' ? '255,255,255' : '22,20,21'; }
    function base() { return document.body.getAttribute('data-theme') === 'night' ? 0.06 : 0.10; }
    function size() {
      w = cv.clientWidth; h = cv.clientHeight;
      cv.width = w * dpr; cv.height = h * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      draw();
    }
    function draw() {
      ctx.clearRect(0, 0, w, h);
      var c = ink(), b = base();
      for (var y = GAP / 2; y < h; y += GAP) {
        for (var x = GAP / 2; x < w; x += GAP) {
          var a = b, r = 1;
          if (!still) {
            var dx = x - mx, dy = y - my, d = Math.sqrt(dx * dx + dy * dy);
            if (d < R) { var k = 1 - d / R; a = b + (0.45 - b) * k; r = 1 + 0.8 * k; }
          }
          ctx.fillStyle = 'rgba(' + c + ',' + a.toFixed(3) + ')';
          ctx.beginPath(); ctx.arc(x, y, r, 0, 6.2832); ctx.fill();
        }
      }
    }
    function onMove(e) {
      mx = e.clientX; my = e.clientY;
      if (!raf) raf = requestAnimationFrame(function () { raf = 0; draw(); });
    }
    addEventListener('resize', size);
    if (!still) {
      addEventListener('pointermove', onMove, { passive: true });
      addEventListener('pointerleave', function () { mx = my = -999; draw(); });
    }
    document.addEventListener('pn:theme', draw);
    size();
  };
})();
