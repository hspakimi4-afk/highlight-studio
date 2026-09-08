/*
 * Highlight Studio — 共通i18n辞書(全ページ横断で使うキー)
 *
 * ナビゲーション・フッターなど、複数ページで同じ文言を使うキーをここに集約する。
 * 各ページはこのファイルを i18n.js より前に読み込んだうえで、ページ固有の
 * window.HS_I18N_DICT を定義する(共通キーと重複するキーをページ側に書いた場合は
 * ページ側の値が優先される)。
 *
 * 読み込み順序:
 *   <script src="./i18n-common.js"></script>
 *   <script> window.HS_I18N_DICT = { ...ページ固有のキー... }; </script>
 *   <script src="./i18n.js"></script>
 *
 * 新しくページ横断の文言を追加する場合は、まずここに追記し、各ページの
 * ローカル辞書からは対応するキーを削除すること(重複管理を避けるため)。
 */
window.HS_I18N_COMMON = {
  "common.navSteps": { ja: "使い方", en: "How it works" },
  "common.navFeatures": { ja: "機能", en: "Features" },
  "common.navPricing": { ja: "料金", en: "Pricing" },
  "common.earlyAccess": { ja: "早期アクセス", en: "Early access" },
  "common.login": { ja: "ログイン", en: "Log in" },
  "common.startFree": { ja: "無料で始める", en: "Start for free" },
  "common.backToTop": { ja: "トップに戻る", en: "Back to top" },
  "common.footerTagline": { ja: "配信アーカイブの切り抜きを、ブラウザだけで自動化。動画は一度も外部に送信されません。", en: "Automate stream-archive clipping, right in your browser. Your video is never sent anywhere." },
  "common.footerColProduct": { ja: "製品", en: "Product" },
  "common.footerPricing": { ja: "料金プラン", en: "Pricing" },
  "common.footerColAccount": { ja: "アカウント", en: "Account" },
  "common.footerMypage": { ja: "マイページ", en: "My page" },
  "common.footerColSupport": { ja: "サポート", en: "Support" },
  "common.footerTerms": { ja: "利用規約", en: "Terms of Service" },
  "common.footerPrivacy": { ja: "プライバシー", en: "Privacy" },
  "common.footerPrivacyFull": { ja: "プライバシーポリシー", en: "Privacy Policy" },
  "common.footerContact": { ja: "お問い合わせ", en: "Contact" },
  "common.footerCopyright": { ja: "© 2026 HighlightStudio", en: "© 2026 HighlightStudio" }
};
