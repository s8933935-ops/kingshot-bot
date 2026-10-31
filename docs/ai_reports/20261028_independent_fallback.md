# Claude不在時の代替監査ルール変更

目的: Claudeに接続できない場合も作業を進め、別文脈の監査が可能なら限定状態で成果を報告する。Claude本人の監査結果とは分ける。

- 選択肢: 従来どおりClaudeを待つ／独立代替監査による限定状態を設ける。後者を採用。明示的にClaudeを必要とする案件固有条件は引き続き保留する。
- 変更対象: AGENTS.md、GEMINI.md、docs/guides/AI_MODEL_ROUTING.md、data/consortium/model_routing.json。既存の別作業の変更は保持。
- 制約: 正規FAIL／UNVERIFIEDと未解決指摘は保持する。障害証拠は同一タスク・環境セッション・対象版で最大1時間、環境・対象変更や復旧時は再確認する。代替PASSとClaude PASSを混同しない。
- 実装: 設定は方針の宣言であり、独立担当の起動や完了判定の強制は実装していない。
- 反証レビュー: 別文脈の gpt-6.1-sol が旧設定の解釈、障害証拠の鮮度、Claude必須条件の適用範囲を指摘。記述を修正したが、修正後の再監査PASSは未取得。初回独立分析とは区別する。
- 実行結果: Windowsで node --test tests/test_model_router.js tests/test_manual_claude_audit.js tests/test_claude_keiba_gate.js は72件成功。
- Claudeゲート: 対象版のゲート試行 request_id 4e6dccfe-fcd3-4265-a7ea-f7897463d88b は5秒でETIMEDOUT、プロセス停止確認済み、UNVERIFIED。実行ログと対象ハッシュは scratch/20261028_manual_audit_evidence.json に保存。キュー保存はPASSではない。
- 現在の状態: ルール変更とテストは実施済み。以前のユーザー経由Claude FAILの全指摘を新しい版について独立監査で再判定したわけではなく、ClaudeのPASSもないため、この変更自体を監査済みの限定完了とは扱わない。以前作成したClaude依頼文は今回の編集前の版であり、そのまま現行版の監査には使わない。
- ai-team-operationsの機械ゲート: クラウドスキルのCLIをこの作業環境から実行できるローカルパスが提示されていないため、start/completeの機械検査は未実施。上記は実際の作業結果の記録であり機械ゲートのPASSではない。
