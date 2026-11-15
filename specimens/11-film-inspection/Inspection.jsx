import React, { useCallback, useEffect, useRef, useState } from "react";
import { findReels, getReel, readNote, writeNote } from "./reelApi.js";

const FIRST_REEL = "R17";
const MOD_KEY =
  typeof navigator !== "undefined" && /Mac|iPhone|iPad|iPod/.test(navigator.platform || navigator.userAgent || "")
    ? "⌘"
    : "Ctrl";

const messageOf = (error, fallback) => (error && error.message) || fallback;

// 输入法全角、小写片号、"35mm" 这类手机上常见的写法，整理成接口能匹配的样子。
function normalizeQuery(raw) {
  return raw
    .replace(/[！-～]/g, ch => String.fromCharCode(ch.charCodeAt(0) - 0xfee0))
    .replace(/　/g, " ")
    .trim()
    .replace(/^r(?=\d)/, "R")
    .replace(/(\d)\s*(m{1,2})$/i, (_, digit, unit) => `${digit} ${unit.toLowerCase()}`);
}

function readStored(id) {
  try {
    return { value: readNote(id) };
  } catch (error) {
    return { error: messageOf(error, "本机备注读不到") };
  }
}

function clock() {
  return new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", hour12: false });
}

function pickTarget(items, key) {
  const exact = items.find(item => item.id.toUpperCase() === key.toUpperCase());
  return exact || items[0] || null;
}

function isTypingTarget(node) {
  return Boolean(node) && (node.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(node.tagName || ""));
}

export default function Inspection() {
  // 查找：query 是输入框里的字，term 是输入法提交后的查找词；shelf 只收最后一次查找的结果。
  const [query, setQuery] = useState("");
  const [term, setTerm] = useState("");
  const [searchRun, setSearchRun] = useState(0);
  const [shelf, setShelf] = useState({ key: null, run: -1, status: "ready", items: [], error: "" });
  const [known, setKnown] = useState({});

  // 读数：一律按片号存，显示时只取当前片号那一格，迟到的旧请求落不到别的拷贝上。
  const [selected, setSelected] = useState(FIRST_REEL);
  const [records, setRecords] = useState({});

  // 备注：stored 是本机已存内容，drafts 是每盘各自的未写回草稿。
  const [stored, setStored] = useState(() => ({ [FIRST_REEL]: readStored(FIRST_REEL) }));
  const [drafts, setDrafts] = useState({});
  const [writes, setWrites] = useState({});

  // 只有真接了键盘（Tab、方向键、组合键）才在窄屏和触屏上露出键帽提示。
  const [keyboardSeen, setKeyboardSeen] = useState(false);

  const searchRef = useRef(null);
  const listRef = useRef(null);
  const headingRef = useRef(null);
  const composing = useRef(false);
  const searchSeq = useRef(0);
  const enterIntent = useRef(null);
  const recordTokens = useRef({});
  const rescueFocus = useRef(null);
  const keyHandler = useRef(null);

  const key = normalizeQuery(term);

  useEffect(() => {
    const seq = ++searchSeq.current;
    const run = searchRun;
    findReels(key).then(
      items => {
        if (seq !== searchSeq.current) return;
        setShelf({ key, run, status: "ready", items, error: "" });
        setKnown(prev => {
          const next = { ...prev };
          for (const item of items) next[item.id] = item;
          return next;
        });
      },
      error => {
        if (seq !== searchSeq.current) return;
        setShelf({ key, run, status: "error", items: [], error: messageOf(error, "查找没有完成") });
      }
    );
  }, [key, searchRun]);

  const loadRecord = useCallback(id => {
    const token = (recordTokens.current[id] || 0) + 1;
    recordTokens.current[id] = token;
    setRecords(prev => {
      const before = prev[id];
      const error = before && before.status === "error" ? before.error : "";
      return { ...prev, [id]: { status: "loading", error } };
    });
    getReel(id)
      .then(data => {
        if (!data || data.id !== id) throw new Error(`返回的记录不属于 ${id}`);
        if (recordTokens.current[id] === token) {
          setRecords(prev => ({ ...prev, [id]: { status: "ready", data } }));
        }
      })
      .catch(error => {
        if (recordTokens.current[id] === token) {
          setRecords(prev => ({ ...prev, [id]: { status: "error", error: messageOf(error, "读取片检记录失败") } }));
        }
      });
  }, []);

  useEffect(() => {
    if (!recordTokens.current[selected]) loadRecord(selected);
  }, [selected, loadRecord]);

  const choose = useCallback(id => {
    const entry = readStored(id);
    setStored(prev => ({ ...prev, [id]: entry }));
    setSelected(id);
  }, []);

  const focusReel = useCallback(id => {
    const button = listRef.current && listRef.current.querySelector(`button[data-reel="${id}"]`);
    if (button) button.focus();
  }, []);

  // 扫码枪或快速回车：结果还没回来时先记住意图，结果到了再选中。
  useEffect(() => {
    const wanted = enterIntent.current;
    if (wanted === null || shelf.key !== wanted) return;
    enterIntent.current = null;
    if (shelf.status !== "ready") return;
    const target = pickTarget(shelf.items, shelf.key);
    if (target) {
      choose(target.id);
      focusReel(target.id);
    }
  }, [shelf, choose, focusReel]);

  const record = records[selected];

  // 重试成功后重试按钮会消失，把焦点交给记录标题，键盘用户不会掉回页首。
  useEffect(() => {
    if (rescueFocus.current !== selected || !record || record.status === "loading") return;
    rescueFocus.current = null;
    const active = document.activeElement;
    if (record.status === "ready" && (!active || active === document.body) && headingRef.current) {
      headingRef.current.focus();
    }
  }, [record, selected]);

  const storedValueOf = id => (stored[id] && !stored[id].error ? stored[id].value : "");
  const isDirty = id => drafts[id] !== undefined && drafts[id] !== storedValueOf(id);
  const dirtyIds = Object.keys(drafts).filter(isDirty);
  const anyDirty = dirtyIds.length > 0;

  useEffect(() => {
    if (!anyDirty) return undefined;
    const warn = event => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [anyDirty]);

  function saveNote(id) {
    const entry = stored[id];
    const value = drafts[id];
    if (!entry || entry.error || value === undefined || value === entry.value) return;
    try {
      writeNote(id, value);
    } catch (error) {
      setWrites(prev => ({ ...prev, [id]: { status: "error", error: messageOf(error, "本机存储拒绝写入") } }));
      return;
    }
    setStored(prev => ({ ...prev, [id]: { value } }));
    setDrafts(prev => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
    setWrites(prev => ({ ...prev, [id]: { status: "saved", at: clock() } }));
  }

  keyHandler.current = event => {
    if (event.isComposing) return;
    const pressed = (event.key || "").toLowerCase();
    const mod = event.ctrlKey || event.metaKey;
    if (!keyboardSeen && (mod || pressed === "tab" || pressed.startsWith("arrow") || (pressed === "/" && !isTypingTarget(event.target)))) {
      setKeyboardSeen(true);
    }
    if (mod &&!event.altKey && !event.shiftKey && pressed === "s") {
      event.preventDefault();
      saveNote(selected);
      return;
    }
    if (pressed === "/" && !mod && !event.altKey && !isTypingTarget(event.target) && searchRef.current) {
      event.preventDefault();
      searchRef.current.focus();
      searchRef.current.select();
    }
  };

  useEffect(() => {
    const listener = event => keyHandler.current && keyHandler.current(event);
    document.addEventListener("keydown", listener);
    return () => document.removeEventListener("keydown", listener);
  }, []);

  const pending = shelf.key !== key || shelf.run !== searchRun;
  const items = shelf.items;
  const rovingId = items.some(item => item.id === selected) ? selected : items[0] && items[0].id;

  function clearSearch() {
    composing.current = false;
    enterIntent.current = null;
    setQuery("");
    setTerm("");
    if (searchRef.current) searchRef.current.focus();
  }

  function onQueryChange(event) {
    const value = event.target.value;
    setQuery(value);
    if (!composing.current && !event.nativeEvent.isComposing) setTerm(value);
  }

  function onCompositionEnd(event) {
    composing.current = false;
    setTerm(event.currentTarget.value);
  }

  function onSearchKeyDown(event) {
    if (event.nativeEvent.isComposing) return;
    if (event.key === "ArrowDown" && rovingId) {
      event.preventDefault();
      focusReel(rovingId);
    } else if (event.key === "Escape" && query) {
      event.preventDefault();
      clearSearch();
    }
  }

  function onSearchSubmit(event) {
    event.preventDefault();
    if (pending) {
      enterIntent.current = key;
      return;
    }
    const target = pickTarget(items, key);
    if (target) {
      choose(target.id);
      focusReel(target.id);
    }
  }

  function onListKeyDown(event) {
    const buttons = Array.from(listRef.current ? listRef.current.querySelectorAll("button[data-reel]") : []);
    const index = buttons.indexOf(document.activeElement);
    if (index < 0) return;
    let next;
    switch (event.key) {
      case "ArrowDown":
      case "ArrowRight":
        next = Math.min(index + 1, buttons.length - 1);
        break;
      case "ArrowUp":
        if (index === 0) {
          event.preventDefault();
          if (searchRef.current) searchRef.current.focus();
          return;
        }
        next = index - 1;
        break;
      case "ArrowLeft":
        next = Math.max(index - 1, 0);
        break;
      case "Home":
        next = 0;
        break;
      case "End":
        next = buttons.length - 1;
        break;
      default:
        return;
    }
    event.preventDefault();
    buttons[next].focus();
    choose(buttons[next].dataset.reel);
  }

  function onNoteChange(event) {
    const id = event.currentTarget.dataset.reel;
    const value = event.currentTarget.value;
    setDrafts(prev => ({ ...prev, [id]: value }));
  }

  // —— 当前这一盘 ——
  const ident = (record && record.status === "ready" && record.data) || known[selected] || null;
  const reading = record && record.status === "ready" ? record.data : null;
  const faulted = Boolean(record && record.status !== "ready" && record.error);
  const retrying = faulted && record.status === "loading";

  function retryRecord() {
    if (retrying) return;
    rescueFocus.current = selected;
    loadRecord(selected);
  }

  const storedEntry = stored[selected] || { value: "" };
  const storedValue = storedValueOf(selected);
  const draft = drafts[selected];
  const noteValue = draft !== undefined ? draft : storedValue;
  const dirty = isDirty(selected);
  const write = writes[selected];
  const canSave = dirty && !storedEntry.error;

  let noteTone = "idle";
  let noteText = storedValue ? "与本机记录一致" : "这盘还没有备注";
  if (write && write.status === "error" && dirty) {
    noteTone = "fault";
    noteText = `写回失败：${write.error}。草稿还在，可以再试。`;
  } else if (dirty) {
    noteTone = "dirty";
    noteText = "有未写回的修改";
  } else if (write && write.status === "saved") {
    noteTone = "saved";
    noteText = `已写回 ${selected} · ${write.at}`;
  }

  let shelfText;
  if (shelf.key === null) shelfText = "正在载入拷贝…";
  else if (shelf.status === "error") shelfText = "查找没有完成";
  else if (shelf.key) shelfText = `「${shelf.key}」找到 ${items.length} 盘`;
  else shelfText = `全部 ${items.length} 盘`;

  return (
    <main aria-label="电影拷贝检查台" data-keys={keyboardSeen ? "on" : undefined}>
      <header className="desk-head">
        <h1>电影拷贝检查台</h1>
        <p className="keys">
          <span><kbd>/</kbd> 查找</span>
          <span><kbd>↑</kbd><kbd>↓</kbd> 列表内换盘</span>
          <span><kbd>{MOD_KEY}</kbd><kbd>S</kbd> 写回备注</span>
        </p>
      </header>

      <div className="bench">
        <section className="shelf" aria-label="拷贝列表">
          <form className="finder" role="search" onSubmit={onSearchSubmit}>
            <div className="finder__head">
              <label htmlFor="reel-query">查找拷贝</label>
              <span role="status">{shelfText}</span>
              {pending && shelf.key !== null && <span className="pending" aria-hidden="true">查找中…</span>}
              {anyDirty && <span className="draft-count">{dirtyIds.length} 盘草稿未写回</span>}
            </div>
            <input
              ref={searchRef}
              id="reel-query"
              type="search"
              value={query}
              placeholder="片号、片名或规格"
              autoComplete="off"
              spellCheck={false}
              enterKeyHint="search"
              aria-describedby="reel-query-hint"
              aria-controls="reel-list"
              onChange={onQueryChange}
              onCompositionStart={() => { composing.current = true; }}
              onCompositionEnd={onCompositionEnd}
              onKeyDown={onSearchKeyDown}
            />
            <p id="reel-query-hint" className="hint">例：R42、放映会、16 mm；回车选中第一盘</p>
          </form>

          {shelf.status === "error" && (
            <div className="shelf-note" role="alert" aria-busy={pending}>
              <p>{shelf.error}</p>
              <button
                type="button"
                className="btn"
                aria-disabled={pending || undefined}
                onClick={() => { if (!pending) setSearchRun(n => n + 1); }}
              >
                {pending ? "正在重新查找…" : "重新查找"}
              </button>
            </div>
          )}

          {shelf.status === "ready" && shelf.key !== null && items.length === 0 && (
            <div className="shelf-note" aria-busy={pending}>
              <p>没有片号、片名或规格包含「{shelf.key}」的拷贝。</p>
              <button type="button" className="btn" onClick={clearSearch}>清除查找，回到全部拷贝</button>
            </div>
          )}

          {items.length > 0 && (
            <ul id="reel-list" ref={listRef} className="reels" aria-busy={pending} onKeyDown={onListKeyDown}>
              {items.map(item => {
                const flags = [];
                if (isDirty(item.id)) flags.push(["draft", "草稿"]);
                if (records[item.id] && records[item.id].status === "error") flags.push(["fault", "读取失败"]);
                if (writes[item.id] && writes[item.id].status === "error" && isDirty(item.id)) flags.push(["fault", "写回失败"]);
                return (
                  <li key={item.id}>
                    <button
                      type="button"
                      className="reel"
                      data-reel={item.id}
                      aria-current={item.id === selected ? "true" : undefined}
                      aria-controls="reel-record"
                      tabIndex={item.id === rovingId ? 0 : -1}
                      onClick={() => choose(item.id)}
                    >
                      <span className="reel__id">{item.id}</span>
                      <span className="reel__meta">{item.gauge} · {item.bay} 区</span>
                      {flags.length > 0 && (
                        <span className="reel__flags">
                          {flags.map(([tone, text]) => <span key={text} className={`flag flag--${tone}`}>{text}</span>)}
                        </span>
                      )}
                      <span className="reel__title">{item.title}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </section>

        <section id="reel-record" className="record" aria-labelledby="record-heading">
          <header className="can-label">
            <h2 id="record-heading" ref={headingRef} tabIndex={-1}>
              <span className="can-label__id">{selected}</span>
              <span className={ident ? "can-label__title" : "can-label__title is-waiting"}>
                {ident ? ident.title : "片名读取中"}
              </span>
            </h2>
            <p className="can-label__meta">
              <span>规格 {ident ? ident.gauge : "—"}</span>
              <span>库区 {ident ? ident.bay : "—"}</span>
            </p>
          </header>

          {faulted ? (
            <div className="fault" role="alert">
              <div>
                <p className="fault__title">{selected} · {record.error}</p>
                <p className="fault__msg">读数暂时不可用，备注仍可照常编辑和写回。</p>
              </div>
              <button type="button" className="btn" aria-disabled={retrying || undefined} onClick={retryRecord}>
                {retrying ? "正在重试…" : "重试读取"}
              </button>
            </div>
          ) : (
            <div className="readings-wrap" aria-busy={!reading}>
              {!reading && <div className="loadbar" aria-hidden="true" />}
              <dl className="readings">
                <div className="reading reading--frames">
                  <dt>格数</dt>
                  <dd>
                    {reading && Number.isFinite(reading.frames)
                      ? <>{reading.frames.toLocaleString("zh-CN")}<span className="unit">格</span></>
                      : "—"}
                  </dd>
                </div>
                <div className="reading">
                  <dt>测读时间</dt>
                  <dd>{reading && reading.measured ? reading.measured : "—"}</dd>
                </div>
              </dl>
              <div className={reading ? "finding" : "finding is-waiting"}>
                <span className="finding__label">检出问题</span>
                <p>{reading ? reading.defect || "未记录问题" : `正在读取 ${selected} 的片检记录…`}</p>
              </div>
            </div>
          )}

          <div className="notes">
            <div className="notes__head">
              <label htmlFor="reel-note">检片备注</label>
              <span className="notes__target">写回至 <b>{selected}</b></span>
            </div>
            {storedEntry.error && (
              <div className="fault fault--inline" role="alert">
                <p className="fault__msg">本机备注读不到（{storedEntry.error}），为免覆盖原有备注，暂不能编辑。</p>
                <button type="button" className="btn" onClick={() => choose(selected)}>重新读取</button>
              </div>
            )}
            <textarea
              key={selected}
              id="reel-note"
              data-reel={selected}
              data-dirty={dirty ? "true" : undefined}
              value={noteValue}
              rows={6}
              readOnly={Boolean(storedEntry.error)}
              placeholder="写下这盘的检查发现与处理意见"
              aria-describedby="reel-note-state"
              onChange={onNoteChange}
            />
            <div className="notes__foot">
              <p id="reel-note-state" className={`note-state note-state--${noteTone}`} role="status">
                {noteTone === "dirty" && <span className="dot" aria-hidden="true" />}
                {noteTone === "saved" && <span className="tick" aria-hidden="true">✓</span>}
                {noteText}
              </p>
              <span className="keys-inline" aria-hidden="true"><kbd>{MOD_KEY}</kbd><kbd>S</kbd></span>
              <button
                type="button"
                className="btn btn--primary"
                aria-disabled={!canSave || undefined}
                onClick={() => saveNote(selected)}
              >
                {noteTone === "fault" ? `重试写回 ${selected}` : `写回 ${selected}`}
              </button>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
