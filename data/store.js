/* PN.store — 小南瓜數位筆記的資料層（Phase 1：reports.js ＋ localStorage）
   ────────────────────────────────────────────────────────────
   Phase 2 接 Supabase 時，只要把這一支換成 Supabase 版、介面維持一樣，
   首頁與報告頁的程式碼都不用動：
     list(q) / get(slug) / create(job) / update(slug,patch)
     toggleFav(slug) / isFav / markRead(slug) / isRead
     share(slug,note) / unshare(slug) / getShare(slug)
     getTakeaway(slug) / setTakeaway(slug,text)
     jobs() / addJob(job) / patchJob(id,patch)
     me() / setMe(patch)
   另外附兩個共用小工具：PN.theme（日夜切換）、PN.dots（互動點格背景）。
*/
window.PN = window.PN || {};
(function () {
  var K = { theme: 'pnTheme', fav: 'pnFav', read: 'pnRead', share: 'pnShare', jobs: 'pnJobs', me: 'pnMe' };
  function rd(k, d) { try { var v = JSON.parse(localStorage.getItem(k)); return v == null ? d : v; } catch (e) { return d; } }
  function wr(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }
  function D() { return window.PN_DATA || { reports: [], bySlug: {}, shelves: [], tagFamilies: [], profiles: [] }; }

  var store = {
    /* ── 讀 ── */
    all: function () { return D().reports.slice(); },
    get: function (slug) { return D().bySlug[slug] || null; },
    shelves: function () { return D().shelves; },
    profiles: function () { return D().profiles; },
    tagFamilies: function () { return D().tagFamilies; },

    /* ── 我的最愛 ── */
    favs: function () { return rd(K.fav, []); },
    isFav: function (s) { return this.favs().indexOf(s) >= 0; },
    toggleFav: function (s) {
      var f = this.favs(), i = f.indexOf(s);
      if (i >= 0) f.splice(i, 1); else f.push(s);
      wr(K.fav, f); return i < 0;
    },

    /* ── 已讀 ＋ 我的一句話 ── */
    reads: function () { return rd(K.read, {}); },
    isRead: function (s) { return !!this.reads()[s]; },
    markRead: function (s) {
      var r = this.reads();
      r[s] = r[s] || {}; r[s].read_at = new Date().toISOString();
      wr(K.read, r);
    },
    getTakeaway: function (s) { return (this.reads()[s] || {}).my_takeaway || ''; },
    setTakeaway: function (s, t) {
      var r = this.reads(); r[s] = r[s] || {}; r[s].my_takeaway = t; wr(K.read, r);
    },

    /* ── 團隊共筆（Phase 1 是這台瀏覽器的示範狀態） ── */
    shares: function () { return rd(K.share, {}); },
    getShare: function (s) { return this.shares()[s] || null; },
    share: function (s, note) {
      var h = this.shares();
      h[s] = { note: note || '', shared_at: new Date().toISOString(), by: this.me().slug };
      wr(K.share, h);
    },
    unshare: function (s) { var h = this.shares(); delete h[s]; wr(K.share, h); },

    /* ── 收件匣排隊單 ── */
    jobs: function () { return rd(K.jobs, []); },
    addJob: function (j) {
      var js = this.jobs();
      j.id = 'j' + Date.now() + Math.floor(Math.random() * 1000);
      j.created_at = new Date().toISOString();
      js.unshift(j); wr(K.jobs, js); return j;
    },
    patchJob: function (id, patch) {
      var js = this.jobs();
      for (var i = 0; i < js.length; i++) if (js[i].id === id) { for (var k in patch) js[i][k] = patch[k]; }
      wr(K.jobs, js);
    },
    dropJob: function (id) { wr(K.jobs, this.jobs().filter(function (j) { return j.id !== id; })); },

    /* ── 我（Phase 1 固定是南瓜，Phase 2 換成登入帳號） ── */
    me: function () {
      var d = D().profiles[0] || { slug: 'terry', name: '南瓜', department: '管理層', title: '共同創辦人／美術總監' };
      return Object.assign({}, d, rd(K.me, {}));
    },
    setMe: function (p) { wr(K.me, Object.assign(rd(K.me, {}), p)); }
  };
  PN.store = store;

  /* ── 日／夜切換：兩邊頁面共用 localStorage.pnTheme ── */
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
