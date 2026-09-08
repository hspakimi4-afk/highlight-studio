/*
 * Highlight Studio — 軽量i18nエンジン(JA/EN)
 *
 * 使い方:
 *   1. 各HTMLページで、このファイルより前に i18n-common.js を読み込み、続けて
 *      ページ固有の window.HS_I18N_DICT を定義する。
 *      形式: { "キー": { ja: "日本語文言", en: "English text" }, ... }
 *   2. 翻訳したい要素に data-i18n="キー" を付ける(テキストがそのまま置き換わる)。
 *      内部にタグを含む場合は data-i18n-html="キー"(innerHTMLとして置き換え)。
 *      属性を翻訳したい場合は data-i18n-placeholder / data-i18n-title /
 *      data-i18n-aria-label / data-i18n-content(meta用) などを使う。
 *   3. 言語切り替えボタンには data-i18n-lang-toggle を付けておくと、
 *      現在の言語に応じたラベル("English" / "日本語")が自動で入る。
 *
 * 選択した言語は localStorage の "hs_lang" キーに保存され、他ページに遷移しても保持される。
 * 未対応ページ(dataやdata-i18n属性を持たないページ)は影響を受けない。
 *
 * ページ横断で使う文言(ナビゲーション・フッターなど)は i18n-common.js の
 * window.HS_I18N_COMMON にまとめてあり、このファイル読み込み時に自動でマージされる
 * (キーが重複する場合はページ側の window.HS_I18N_DICT が優先される)。
 * 読み込み順序: i18n-common.js → (ページ固有の HS_I18N_DICT を定義する script) → i18n.js
 */
(function () {
  'use strict';

  var LANG_KEY = 'hs_lang';
  var DICT = Object.assign({}, window.HS_I18N_COMMON || {}, window.HS_I18N_DICT || {});

  function getLang() {
    try {
      var saved = localStorage.getItem(LANG_KEY);
      if (saved === 'en' || saved === 'ja') return saved;
    } catch (e) { /* localStorage無効な環境向けフォールバック */ }
    return 'ja';
  }

  function setLang(lang) {
    try { localStorage.setItem(LANG_KEY, lang); } catch (e) { /* noop */ }
  }

  function t(key, lang) {
    var entry = DICT[key];
    if (!entry) return null;
    var val = entry[lang];
    if (val == null) val = entry.ja; // 未翻訳キーは日本語にフォールバック
    return val;
  }

  var ATTR_MAP = ['placeholder', 'title', 'aria-label', 'content', 'value'];

  function apply(lang) {
    document.documentElement.setAttribute('lang', lang === 'en' ? 'en' : 'ja');

    var nodes = document.querySelectorAll('[data-i18n]');
    for (var i = 0; i < nodes.length; i++) {
      var key = nodes[i].getAttribute('data-i18n');
      var val = t(key, lang);
      if (val != null) nodes[i].textContent = val;
    }

    var htmlNodes = document.querySelectorAll('[data-i18n-html]');
    for (var j = 0; j < htmlNodes.length; j++) {
      var hkey = htmlNodes[j].getAttribute('data-i18n-html');
      var hval = t(hkey, lang);
      if (hval != null) htmlNodes[j].innerHTML = hval;
    }

    for (var a = 0; a < ATTR_MAP.length; a++) {
      var attr = ATTR_MAP[a];
      var sel = '[data-i18n-' + attr + ']';
      var attrNodes = document.querySelectorAll(sel);
      for (var k = 0; k < attrNodes.length; k++) {
        var akey = attrNodes[k].getAttribute('data-i18n-' + attr);
        var aval = t(akey, lang);
        if (aval != null) attrNodes[k].setAttribute(attr, aval);
      }
    }

    var toggles = document.querySelectorAll('[data-i18n-lang-toggle]');
    for (var b = 0; b < toggles.length; b++) {
      toggles[b].textContent = lang === 'en' ? '日本語' : 'English';
      toggles[b].setAttribute(
        'aria-label',
        lang === 'en' ? '日本語表示に切り替え' : 'Switch to English'
      );
    }

    document.dispatchEvent(new CustomEvent('hs:langchange', { detail: { lang: lang } }));
  }

  function toggle() {
    var next = getLang() === 'en' ? 'ja' : 'en';
    setLang(next);
    apply(next);
  }

  window.HS_I18N = { getLang: getLang, setLang: setLang, t: t, apply: apply, toggle: toggle };

  function init() {
    apply(getLang());
    var toggles = document.querySelectorAll('[data-i18n-lang-toggle]');
    for (var i = 0; i < toggles.length; i++) {
      toggles[i].addEventListener('click', toggle);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
