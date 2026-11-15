/* ==========================================================================
   motion.js · 无依赖的小型动效运行库（约 4KB 压缩前）
   --------------------------------------------------------------------------
   配合 assets/motion.css。用法：

   <head> 里尽早放这一行（避免内容先闪一下再被藏起来；页面解析完 0.6 秒内本库没跑起来就全部直接显示，6 秒封顶）：
     document.documentElement.classList.add('js');(function(){function f(){if(!window.Motion)document.documentElement.classList.add('no-motion')}document.addEventListener('DOMContentLoaded',function(){setTimeout(f,600)});setTimeout(f,6000)})()
   网络字体的样式表要异步加载（media="print" onload="this.media='all'"），否则字体慢时会挡住本文件执行。
   <body> 末尾内联本文件。注意：本文件和它的注释里都不能出现字面的 script 结束标签。默认在 DOMContentLoaded 时自动执行 Motion.auto()；
          若要手动控制，在本文件之前设 window.MOTION_MANUAL = true。

   Motion.auto()                 一次装好下面所有能力
   Motion.reveal(root?)          [data-reveal] [data-split] .draw 进入视口时加 .is-in；
                                 同一个 [data-stagger] 容器里的子项自动编号 --i
   Motion.split(el)              把标题按 <br> 拆成行（data-split），或 data-split="words" 按词
   Motion.count(el, opts?)       数字滚动到目标值：<span data-count="4113.6" data-decimals="2" data-delay="600">
   Motion.spring(el, kf, name?)  用弹簧缓动跑 WAAPI 动画，name = snappy|smooth|bouncy|gentle
   Motion.flip(els, mutate, name?) 布局变化动画（FLIP）：先记位置→改 DOM→从旧位置弹到新位置
   Motion.swap(fn)               用 View Transition 包住一次 DOM 更新，不支持时直接执行
   Motion.spotlight(sel?)        .spotlight 元素跟随指针写入 --mx / --my
   Motion.reduced                当前绘制是否启用减弱动效

   下面这些只要写属性，auto() 会自动装好：
   data-parallax="0.15"          随滚动轻微位移（系数 0.05–0.25；主视觉物件用）
   data-tilt="6"                 指针移上去时朝指针方向倾斜（最大角度；放在主视觉或一张卡上）
   [data-tabs]                   标签页：里面一个 role=tablist（按钮 role=tab）和同样多个 role=tabpanel；切换带过渡、支持方向键
   .seg / role=tablist           选中项下面自动有一个会滑动的选中块
   .bar                          进度条进入视口时从 0 长到 --v
   data-copy="#id"               复制按钮：复制目标元素的文字，按钮上短暂显示"已复制"

   默认不理会系统的"减少动态效果"，动效照常播放。<html> 加 data-respect-reduced-motion 后才遵守：
   此时所有函数在减弱动效时退化为直接到终态（或只做透明度）。
   ========================================================================== */
(function () {
  'use strict';
  var root = document.documentElement;
  root.classList.add('js');
  // Keep existing showcase pages in full-motion mode. Opted-in pages share one flag across CSS and JS.
  if (window.MOTION_RESPECT_REDUCED) root.setAttribute('data-respect-reduced-motion', '');
  var sys = window.matchMedia ? matchMedia('(prefers-reduced-motion: reduce)') : null;
  var mq = {
    get matches() { return !!sys && sys.matches && root.hasAttribute('data-respect-reduced-motion'); },
    addEventListener: function (t, f) { if (sys && sys.addEventListener) sys.addEventListener(t, f); },
    removeEventListener: function (t, f) { if (sys && sys.removeEventListener) sys.removeEventListener(t, f); }
  };

  function css(name, fallback) {
    var v = getComputedStyle(root).getPropertyValue(name).trim();
    return v || fallback;
  }
  function springOf(name) {
    name = name || 'smooth';
    return {
      easing: css('--spring-' + name, 'cubic-bezier(0.2, 0.8, 0.2, 1)'),
      duration: parseFloat(css('--spring-' + name + '-dur', '600')) || 600
    };
  }

  /* ---------------------------------------------------------------- 拆行 */
  function split(el) {
    if (!el || el.dataset.splitDone) return;
    el.dataset.splitDone = '1';
    var mode = el.getAttribute('data-split');
    var label = el.textContent.replace(/\s+/g, ' ').trim();
    if (!el.getAttribute('aria-label')) el.setAttribute('aria-label', label);
    var parts;
    if (mode === 'words') {
      // 中文按字、西文按词（有 Intl.Segmenter 时用它）
      var text = el.textContent;
      if (window.Intl && Intl.Segmenter) {
        parts = Array.from(new Intl.Segmenter(undefined, { granularity: 'word' }).segment(text), function (s) { return s.segment; });
      } else {
        parts = text.split(/(\s+)/);
      }
      el.innerHTML = '';
      var n = 0;
      parts.forEach(function (p) {
        if (/^\s+$/.test(p)) { el.appendChild(document.createTextNode(p)); return; }
        var line = document.createElement('span'); line.className = 'line'; line.style.display = 'inline-block';
        var inner = document.createElement('span'); inner.textContent = p; inner.style.setProperty('--i', n++);
        line.appendChild(inner); el.appendChild(line);
      });
    } else {
      var html = el.innerHTML.split(/<br\s*\/?>/i);
      el.innerHTML = html.map(function (h, i) {
        return '<span class="line" aria-hidden="true"><span style="--i:' + i + '">' + h.trim() + '</span></span>';
      }).join('');
    }
  }

  /* ---------------------------------------------------------------- 进入视口 */
  var io = null;
  function onEnter(entries) {
    entries.forEach(function (e) {
      if (!e.isIntersecting) return;
      var t = e.target;
      t.classList.add('is-in');
      if (t.hasAttribute('data-count')) count(t);
      t.querySelectorAll && t.querySelectorAll('[data-count]').forEach(function (c) { count(c); });
      io.unobserve(t);
    });
  }
  function reveal(scope) {
    scope = scope || document;
    scope.querySelectorAll('[data-split]').forEach(split);
    scope.querySelectorAll('[data-stagger]').forEach(function (box) {
      var kids = box.querySelectorAll(':scope > [data-reveal], :scope > * > [data-reveal]');
      kids.forEach(function (k, i) { if (!k.style.getPropertyValue('--i')) k.style.setProperty('--i', i); });
    });
    scope.querySelectorAll('.draw').forEach(function (p) {
      if (p.getTotalLength) { try { p.style.setProperty('--len', Math.ceil(p.getTotalLength()) + 1); } catch (e) {} }
    });
    var targets = scope.querySelectorAll('[data-reveal], [data-split], [data-count], .draw, [data-observe], .bar');
    if (!('IntersectionObserver' in window)) { targets.forEach(function (t) { t.classList.add('is-in'); }); return; }
    // 阈值用 0 + 底部收进 6%：元素上沿一进入可视区下方 94% 就开始入场。
    // 不用比例阈值——高的卡片要露出 12% 才触发，会在首屏留下一块空白。
    io = io || new IntersectionObserver(onEnter, { rootMargin: '0px 0px -6% 0px', threshold: 0 });
    targets.forEach(function (t) { io.observe(t); });
  }

  /* ---------------------------------------------------------------- 数字滚动 */
  var counts = new WeakMap();
  function stopCount(el) {
    var pending = counts.get(el);
    if (!pending) return;
    clearTimeout(pending.timer);
    cancelAnimationFrame(pending.frame);
    counts.delete(el);
  }
  function count(el, opts) {
    opts = opts || {};
    if (el.dataset.counted && opts.to == null) return;
    var to = parseFloat(opts.to != null ? opts.to : el.dataset.count);
    if (!Number.isFinite(to)) return;
    var previous = counts.get(el);
    var from = parseFloat(opts.from != null ? opts.from : previous ? previous.value : el.dataset.from || 0);
    var dec = opts.decimals != null ? opts.decimals : parseInt(el.dataset.decimals || '0', 10);
    var dur = opts.duration != null ? opts.duration : parseInt(el.dataset.duration || '1100', 10);
    var wait = opts.delay != null ? opts.delay : parseInt(el.dataset.delay || '0', 10);
    var fmt = new Intl.NumberFormat(opts.locale || undefined, { minimumFractionDigits: dec, maximumFractionDigits: dec });
    stopCount(el);
    el.dataset.counted = '1';
    el.style.fontVariantNumeric = 'tabular-nums';
    var job = { timer: 0, frame: 0, value: from };
    counts.set(el, job);
    if (mq.matches || !(dur > 0)) { job.value = to; el.textContent = fmt.format(to); return; }
    function start() {
      var t0 = performance.now();
      function frame(now) {
        if (counts.get(el) !== job) return;
        var p = mq.matches ? 1 : Math.min(1, (now - t0) / dur);
        job.value = from + (to - from) * (1 - Math.pow(1 - p, 4));
        el.textContent = fmt.format(job.value);
        if (p < 1) job.frame = requestAnimationFrame(frame);
        else job.frame = 0;
      }
      frame(t0);
    }
    if (wait > 0) { job.timer = setTimeout(start, wait); return job.timer; }
    start();
  }

  /* ---------------------------------------------------------------- 弹簧动画 */
  function spring(el, keyframes, name, extra) {
    if (!el || !el.animate) return null;
    var s = springOf(name);
    if (mq.matches) {
      var last = Array.isArray(keyframes) ? keyframes[keyframes.length - 1] : keyframes;
      return el.animate([last, last], { duration: 1, fill: 'forwards' });
    }
    var o = { duration: s.duration, easing: s.easing, fill: 'both' };
    for (var k in extra || {}) o[k] = extra[k];
    return el.animate(keyframes, o);
  }

  /* ---------------------------------------------------------------- FLIP 布局动画 */
  var layoutAnimations = new WeakMap();
  function flip(els, mutate, name) {
    els = Array.prototype.slice.call(els);
    var first = els.map(function (e) { return e.getBoundingClientRect(); });
    // Measure the visible position before cancelling our previous layout pass.
    els.forEach(function (el) {
      var previous = layoutAnimations.get(el);
      if (previous) { previous.cancel(); layoutAnimations.delete(el); }
    });
    mutate();
    if (mq.matches) return;
    els.forEach(function (e, i) {
      if (!e.isConnected) return;
      var last = e.getBoundingClientRect(), f = first[i];
      var dx = f.left - last.left, dy = f.top - last.top;
      var sx = last.width ? f.width / last.width : 1, sy = last.height ? f.height / last.height : 1;
      if (!dx && !dy && sx === 1 && sy === 1) return;
      var animation = spring(e, [
        { transformOrigin: '0 0', transform: 'translate(' + dx + 'px,' + dy + 'px) scale(' + sx + ',' + sy + ')' },
        { transformOrigin: '0 0', transform: 'none' }
      ], name || 'smooth', { fill: 'none' });
      if (animation) {
        layoutAnimations.set(e, animation);
        animation.finished.then(function () {
          if (layoutAnimations.get(e) === animation) layoutAnimations.delete(e);
        }, function () {});
      }
    });
  }

  /* ---------------------------------------------------------------- View Transition */
  function swap(fn) {
    if (document.startViewTransition && !mq.matches) return document.startViewTransition(fn);
    fn(); return null;
  }

  /* ---------------------------------------------------------------- 指针光斑 */
  function spotlight(sel) {
    if (!matchMedia('(hover: hover)').matches) return;
    document.querySelectorAll(sel || '.spotlight').forEach(function (el) {
      el.addEventListener('pointermove', function (e) {
        if (mq.matches) return;
        var r = el.getBoundingClientRect();
        el.style.setProperty('--mx', (e.clientX - r.left) + 'px');
        el.style.setProperty('--my', (e.clientY - r.top) + 'px');
      });
    });
  }

  /* ---------------------------------------------------------------- 滚动视差：data-parallax="0.15" */
  function parallax() {
    var els = Array.prototype.slice.call(document.querySelectorAll('[data-parallax]'));
    if (!els.length) return;
    var ticking = false;
    var ks = els.map(function (el) { return parseFloat(el.getAttribute('data-parallax')) || 0.12; });
    var last = els.map(function () { return ''; });
    function update() {
      ticking = false;
      if (mq.matches) return;
      var vh = innerHeight;
      // 先一次读完所有位置，再统一写：交替读写会让浏览器每个元素都重新布局一次
      // 读的是布局位置（offsetTop 链），不受自己的 transform 影响，也不会被上一帧的位移带偏
      var tops = els.map(function (el) {
        var y = 0, n = el;
        while (n) { y += n.offsetTop; n = n.offsetParent; }
        return [y - scrollY, el.offsetHeight];
      });
      tops.forEach(function (t, i) {
        if (t[0] + t[1] < -200 || t[0] > vh + 200) return;
        var v = (Math.round((t[0] + t[1] / 2 - vh / 2) * -ks[i] * 2) / 2) + 'px';   // 半像素取整，值不变就不写
        if (v !== last[i]) { last[i] = v; els[i].style.setProperty('--py', v); }
      });
    }
    addEventListener('scroll', function () { if (!mq.matches && !ticking) { ticking = true; requestAnimationFrame(update); } }, { passive: true });
    addEventListener('resize', update);
    mq.addEventListener('change', update);
    update();
  }

  /* ---------------------------------------------------------------- 指针倾斜：data-tilt（可写最大角度，默认 6） */
  function tilt() {
    if (!matchMedia('(hover: hover)').matches) return;
    document.querySelectorAll('[data-tilt]').forEach(function (el) {
      var max = parseFloat(el.getAttribute('data-tilt')) || 6;
      var area = el.closest('[data-tilt-area]') || el;
      var pending = null, rect = null;
      area.addEventListener('pointerenter', function () { rect = el.getBoundingClientRect(); });
      addEventListener('scroll', function () { rect = null; }, { passive: true });
      area.addEventListener('pointermove', function (e) {
        if (mq.matches) return;
        // 每帧最多处理一次；位置只在进入和滚动后重新读
        if (pending) { pending = e; return; }
        pending = e;
        requestAnimationFrame(function () {
          var p = pending; pending = null;
          var r = rect || (rect = el.getBoundingClientRect());
          var x = (p.clientX - r.left) / r.width - 0.5, y = (p.clientY - r.top) / r.height - 0.5;
          el.style.setProperty('--ry', (x * max * 2).toFixed(2) + 'deg');
          el.style.setProperty('--rx', (-y * max * 2).toFixed(2) + 'deg');
        });
      });
      area.addEventListener('pointerleave', function () { el.style.setProperty('--rx', '0deg'); el.style.setProperty('--ry', '0deg'); });
    });
  }

  /* ---------------------------------------------------------------- 滑动的选中块：.seg 与 [role=tablist] 自动获得 */
  function ink() {
    document.querySelectorAll('.seg, [role="tablist"]').forEach(function (bar) {
      if (bar.querySelector(':scope > .tab-ink')) return;
      var i = document.createElement('i'); i.className = 'tab-ink'; i.setAttribute('aria-hidden', 'true');
      bar.insertBefore(i, bar.firstChild); bar.classList.add('has-ink');
      function place() {
        var on = bar.querySelector(':scope > [aria-selected="true"], :scope > [aria-pressed="true"], :scope > .on');
        if (!on) { i.style.opacity = '0'; return; }
        i.style.opacity = '1';
        i.style.setProperty('--ink-x', on.offsetLeft + 'px');
        i.style.setProperty('--ink-w', on.offsetWidth + 'px');
      }
      place();
      requestAnimationFrame(function () { i.classList.add('ready'); });
      new MutationObserver(place).observe(bar, { subtree: true, attributes: true, attributeFilter: ['aria-selected', 'aria-pressed', 'class'] });
      addEventListener('resize', place);
      if (document.fonts && document.fonts.ready) document.fonts.ready.then(place);
    });
  }

  /* ---------------------------------------------------------------- 标签页：[data-tabs] 里放 role=tablist 和若干 role=tabpanel */
  function tabs() {
    document.querySelectorAll('[data-tabs]').forEach(function (box, n) {
      var list = box.querySelector('[role="tablist"]');
      if (!list) return;
      var btns = Array.prototype.slice.call(list.querySelectorAll('[role="tab"]'));
      var panels = Array.prototype.slice.call(box.querySelectorAll('[role="tabpanel"]'));
      btns.forEach(function (b, k) {
        var p = panels[k]; if (!p) return;
        b.id = b.id || 'tab-' + n + '-' + k; p.id = p.id || 'panel-' + n + '-' + k;
        b.setAttribute('aria-controls', p.id); p.setAttribute('aria-labelledby', b.id);
        if (b.tagName !== 'BUTTON') b.setAttribute('tabindex', '0');
      });
      function select(k, focus) {
        btns.forEach(function (b, j) { b.setAttribute('aria-selected', String(j === k)); b.tabIndex = j === k ? 0 : -1; });
        panels.forEach(function (p, j) {
          var show = j === k;
          if (show && p.hidden) { p.hidden = false; spring(p, [{ opacity: 0, translate: '0 10px' }, { opacity: 1, translate: '0 0' }], 'smooth', { fill: 'none' }); reveal(p); }
          else p.hidden = !show;
        });
        if (focus) btns[k].focus();
      }
      var start = Math.max(0, btns.findIndex(function (b) { return b.getAttribute('aria-selected') === 'true'; }));
      select(start);
      btns.forEach(function (b, k) {
        b.addEventListener('click', function (e) { e.preventDefault(); select(k); });
        b.addEventListener('keydown', function (e) {
          var d = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0;
          if (d) { e.preventDefault(); select((k + d + btns.length) % btns.length, true); }
        });
      });
    });
  }

  /* ---------------------------------------------------------------- 复制按钮：data-copy="#元素id"，不写就复制紧挨着的上一个元素 */
  function copy() {
    document.querySelectorAll('[data-copy]').forEach(function (btn) {
      btn.hidden = false;
      btn.addEventListener('click', function () {
        var sel = btn.getAttribute('data-copy');
        var src = sel ? document.querySelector(sel) : btn.previousElementSibling;
        var text = src ? (src.value != null && src.tagName !== 'BUTTON' ? src.value : src.innerText).trim() : '';
        var label = btn.querySelector('span') || btn, old = label.textContent;
        function done(ok) { label.textContent = ok ? '已复制' : '复制失败，请手动选中'; btn.classList.toggle('done', ok); setTimeout(function () { label.textContent = old; btn.classList.remove('done'); }, 1600); }
        if (navigator.clipboard && text) navigator.clipboard.writeText(text).then(function () { done(true); }, function () { done(false); });
        else done(false);
      });
    });
  }

  /* Custom direct manipulation. Native buttons and sliders keep their own input
     semantics. Attach this helper to a dedicated grip and supply model callbacks. */
  function drag(handle, callbacks, options) {
    var threshold = Math.max(0, options && options.threshold != null ? options.threshold : 5);
    var gesture = null;
    var suppressClick = false;
    function sample(event) {
      return { x: gesture.x, y: gesture.y, startX: gesture.startX, startY: gesture.startY,
               dx: gesture.x - gesture.startX, dy: gesture.y - gesture.startY, event: event };
    }
    function finish(event, commit) {
      if (!gesture) return;
      var id = gesture.id, active = gesture.active, point = sample(event);
      gesture = null;
      handle.removeAttribute('data-dragging');
      if (handle.hasPointerCapture(id)) handle.releasePointerCapture(id);
      if (active) {
        suppressClick = true;
        var callback = commit ? callbacks.commit : callbacks.cancel;
        if (callback) callback(point);
      }
    }
    function down(event) {
      if (gesture || !event.isPrimary || event.button !== 0) return;
      suppressClick = false;
      gesture = { id: event.pointerId, startX: event.clientX, x: event.clientX,
                  startY: event.clientY, y: event.clientY, active: false };
      handle.setPointerCapture(event.pointerId);
    }
    function move(event) {
      if (!gesture || gesture.id !== event.pointerId) return;
      gesture.x = event.clientX;
      gesture.y = event.clientY;
      var point = sample(event);
      if (!gesture.active) {
        if (Math.hypot(point.dx, point.dy) < threshold) return;
        gesture.active = true;
        handle.setAttribute('data-dragging', '');
        if (callbacks.start) callbacks.start(point);
      }
      if (gesture && callbacks.move) callbacks.move(point);
    }
    function up(event) {
      if (!gesture || gesture.id !== event.pointerId) return;
      if (gesture.active && (event.clientX !== gesture.x || event.clientY !== gesture.y)) move(event);
      finish(event, true);
    }
    function pointerCancel(event) {
      if (gesture && gesture.id === event.pointerId) finish(event, false);
    }
    function lost(event) {
      if (!handle.hasPointerCapture(event.pointerId)) pointerCancel(event);
    }
    function escape(event) {
      if (gesture && event.key === 'Escape') {
        event.preventDefault(); event.stopPropagation(); finish(event, false);
      }
    }
    function blur(event) { finish(event, false); }
    function visibility(event) { if (document.hidden) finish(event, false); }
    function click(event) {
      if (!suppressClick || event.detail === 0) return;
      suppressClick = false;
      event.preventDefault(); event.stopImmediatePropagation();
    }
    handle.addEventListener('pointerdown', down);
    handle.addEventListener('pointermove', move);
    handle.addEventListener('pointerup', up);
    handle.addEventListener('pointercancel', pointerCancel);
    handle.addEventListener('lostpointercapture', lost);
    handle.addEventListener('click', click, true);
    window.addEventListener('keydown', escape, true);
    window.addEventListener('blur', blur);
    document.addEventListener('visibilitychange', visibility);
    function dispose() {
      finish(null, false);
      handle.removeEventListener('pointerdown', down);
      handle.removeEventListener('pointermove', move);
      handle.removeEventListener('pointerup', up);
      handle.removeEventListener('pointercancel', pointerCancel);
      handle.removeEventListener('lostpointercapture', lost);
      handle.removeEventListener('click', click, true);
      window.removeEventListener('keydown', escape, true);
      window.removeEventListener('blur', blur);
      document.removeEventListener('visibilitychange', visibility);
    }
    return { cancel: function () { finish(null, false); }, dispose: dispose };
  }

  /* A native scroll chapter. The document owns scrolling; CSS owns the artwork.
     init returns a disposer so routed components can remove their listeners. */
  var sceneDisposers = new WeakMap();
  function scene(section) {
    if (sceneDisposers.has(section)) return sceneDisposers.get(section);
    if (section.hasAttribute('data-scene-still')) return;
    var pin = section.querySelector(':scope > [data-scene-pin]');
    if (!pin || !window.ResizeObserver || !window.IntersectionObserver || !window.matchMedia) return;
    var eligible = matchMedia('(min-width: 48em) and (min-height: 32em), (min-width: 20em) and (min-height: 40em)');
    var frame = 0;
    var active = false;
    var near = false;
    var last = '';

    function paint() {
      frame = 0;
      if (!active) return;
      var span = section.offsetHeight - pin.offsetHeight;
      var value = Math.max(0, Math.min(1, -section.getBoundingClientRect().top / Math.max(1, span))).toFixed(4);
      if (value === last) return;
      last = value;
      section.style.setProperty('--scene-progress', value);
    }
    function schedule() {
      if (!frame && active) frame = requestAnimationFrame(paint);
    }
    function listen() {
      window.removeEventListener('scroll', schedule);
      if (active && near) window.addEventListener('scroll', schedule, { passive: true });
    }
    function layout() {
      // Zoom, larger text, and landscape phones can make a pinned frame too tall.
      active = eligible.matches && !mq.matches && pin.scrollHeight <= document.documentElement.clientHeight + 2;
      section.toggleAttribute('data-scene-active', active);
      listen();
      if (active) paint();
      else {
        last = '';
        section.style.removeProperty('--scene-progress');
      }
    }
    var visibility = new IntersectionObserver(function (entries) {
      near = entries[0].isIntersecting;
      listen();
      // Also settle the endpoint after a large jump out of the chapter.
      schedule();
    }, { rootMargin: '20% 0px' });
    var geometry = new ResizeObserver(layout);
    visibility.observe(section);
    geometry.observe(pin);
    window.addEventListener('resize', layout);
    window.addEventListener('pageshow', layout);
    eligible.addEventListener('change', layout);
    mq.addEventListener('change', layout);
    layout();
    function dispose() {
      active = false;
      window.removeEventListener('scroll', schedule);
      window.removeEventListener('resize', layout);
      window.removeEventListener('pageshow', layout);
      eligible.removeEventListener('change', layout);
      mq.removeEventListener('change', layout);
      visibility.disconnect();
      geometry.disconnect();
      cancelAnimationFrame(frame);
      section.removeAttribute('data-scene-active');
      section.style.removeProperty('--scene-progress');
      sceneDisposers.delete(section);
    }
    sceneDisposers.set(section, dispose);
    return dispose;
  }

  // A native range keeps pointer, touch and keyboard behavior in sync with the
  // divider. Until the listener is ready, CSS shows an unambiguous 50/50 still.
  var compareDisposers = new WeakMap();
  function compare(board) {
    if (compareDisposers.has(board)) return compareDisposers.get(board);
    var slider = board.querySelector(':scope > input[type="range"]');
    if (!slider || !board.querySelector(':scope > [data-compare-before]') ||
        !board.querySelector(':scope > [data-compare-after]')) return;
    var previousText = slider.getAttribute('aria-valuetext');
    var touchStart = null;
    function update() {
      var min = Number(slider.min || 0), max = Number(slider.max || 100);
      var percent = Math.min(100, Math.max(0, (slider.valueAsNumber - min) * 100 / (max - min || 1)));
      board.style.setProperty('--split', percent + '%');
      if (percent === 0 || percent === 100) {
        board.dataset.compareEndpoint = percent === 0 ? 'after' : 'before';
      } else {
        delete board.dataset.compareEndpoint;
      }
      if (board.dataset.beforeLabel && board.dataset.afterLabel) {
        slider.setAttribute('aria-valuetext', board.dataset.beforeLabel + ' ' + Math.round(percent) + '% · ' +
          board.dataset.afterLabel + ' ' + Math.round(100 - percent) + '%');
      }
    }
    function rememberTouch(event) {
      if (event.pointerType === 'touch' && event.isPrimary) {
        touchStart = { id: event.pointerId, value: slider.value };
      }
    }
    function finishTouch(event) {
      if (!touchStart || touchStart.id !== event.pointerId) return;
      // A native range can seek on contact before the browser takes over a vertical pan.
      if (event.type === 'pointercancel' && slider.value !== touchStart.value) {
        slider.value = touchStart.value;
        slider.dispatchEvent(new Event('input', { bubbles: true }));
      }
      touchStart = null;
    }
    update();
    slider.addEventListener('input', update);
    slider.addEventListener('pointerdown', rememberTouch);
    slider.addEventListener('pointerup', finishTouch);
    slider.addEventListener('pointercancel', finishTouch);
    window.addEventListener('pageshow', update);
    board.setAttribute('data-compare-ready', '');
    function dispose() {
      slider.removeEventListener('input', update);
      slider.removeEventListener('pointerdown', rememberTouch);
      slider.removeEventListener('pointerup', finishTouch);
      slider.removeEventListener('pointercancel', finishTouch);
      window.removeEventListener('pageshow', update);
      board.removeAttribute('data-compare-ready');
      delete board.dataset.compareEndpoint;
      board.style.removeProperty('--split');
      if (previousText === null) slider.removeAttribute('aria-valuetext');
      else slider.setAttribute('aria-valuetext', previousText);
      compareDisposers.delete(board);
    }
    compareDisposers.set(board, dispose);
    return dispose;
  }

  function auto() {
    reveal(); spotlight(); parallax(); tilt(); tabs(); ink(); copy();
    document.querySelectorAll('[data-scroll-scene]').forEach(scene);
    document.querySelectorAll('[data-compare]').forEach(compare);
  }

  window.Motion = { auto: auto, reveal: reveal, split: split, count: count, stopCount: stopCount, spring: spring, flip: flip, drag: drag,
                    swap: swap, spotlight: spotlight, parallax: parallax, tilt: tilt, tabs: tabs, ink: ink, scene: scene, compare: compare,
                    get reduced() { return mq.matches; } };

  if (!window.MOTION_MANUAL) {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', auto);
    else auto();
  }
})();
