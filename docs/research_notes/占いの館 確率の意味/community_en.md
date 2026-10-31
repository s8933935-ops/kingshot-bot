# 神秘の占い屋：英語圏コミュニティ投稿（2026-10-03調査）

対象は Kingshot の Mystic Divination（神秘の占い屋）。以下の Reddit コメントは個人投稿であり、ゲーム仕様の確定情報ではない。サンプル数は投稿者が明示した場合のみ記す。同じスレッド内の返信は独立した検証とは扱わない。

## Wish Reward 1.79% と「10枚だから初回1/10」の対立

### Takeaway
1.79%の表示を示して初回10%説を疑問視した一次投稿がある。均等な10枚シャッフル説を支持する計測報告は見つからず、10%と置いた数式投稿は確認できたが前提が表示確率と衝突する。

### Cited Findings
- 2026-05-02、Reddit 投稿者 philmn はゲーム画面の「Wish Reward 1.79%」を提示し、初回が10分の1ではなく1.79%なのか質問。サンプル数は表示1画面で、実測試行なし。[元投稿](https://www.reddit.com/r/KingShot/comments/1t1gin0/mystic_divination_question/)
- 同スレッドの返信2件は、選択時に重み付き抽選をしているように見える、盤面は均等選択の錯覚だ、と主張。ただし内部実装を検証した証拠と試行数はない（2026-05頃）。[元投稿と返信](https://www.reddit.com/r/KingShot/comments/1t1gin0/mystic_divination_question/)
- 2026-06-01、同じ philmn は別スレッドで、ゲーム内の「!」から確率を見られ、初回は1.79%で10%ではないと説明。「約半分は10枚目」とも述べるが、後者の母数は不明。[返信](https://www.reddit.com/r/KingShot/comments/1trt735/pretty_much_sums_up_this_game/)
- 反対側の明示的前提として、2026年春の数式投稿は初回1/10、k枚までの当選確率k/10を用いてリセット最適化を計算した。これは実測ではなく仮定であり、1.79%表示を説明しない。[数式コメント](https://www.reddit.com/r/KingShot/comments/1qy1q2q/any_strategy_for_mystic_divination_as_f2p/)
- コミュニティ制作ガイドは初期 wish 確率を約0.5%と記す（2026-06-03更新）。1.79%とは数値が異なり、報酬種類・サーバー・更新時期による差かどうか不明。[Kingshot Wiki ガイド](https://www.kingshot.wiki/events/mystic-divination)

### Inferences
- 1.79%が当該画面・当該条件での初回当選率なら、初回10%の均等配置とは整合しない。表示の条件や後続抽選への変化を確認する必要がある。

### Gaps
- 1.79%の元画像の細字・適用範囲、全10段階の公式確率表、条件別の変化は確認できていない。公式ヘルプの公開カテゴリは見つかったが、この点の説明は取得できなかった。[公式ヘルプ](https://centurygames.helpshift.com/hc/en/140-kingshot/section/1394-mystic-divination/)

## リセット戦略と実体験

### Takeaway
4～5枚でリセットする助言と、wish 狙いなら最後まで開く助言が併存する。狙う評価指標が「無料の小報酬を集める」か「wish 1個あたりのチケット」かで議論がずれる。

### Cited Findings
- 2026-05-30頃、Real_Temporary_922 は5枚でリセットを20回試し、前半10回でwish 1回、後半10回で2回（合計3/20盤面）と自己報告。さらに完走した4盤面連続で最後の2枚にwishがあったと報告。スクリーンショット付きの試行ログはなく、事後選択と報告バイアスに注意。[本人の連続コメント](https://www.reddit.com/r/KingShot/comments/1trt735/pretty_much_sums_up_this_game/)
- 同スレッドで Bobby_feta は、無課金の小報酬狙いなら4枚、4枚目が倍率なら5枚で更新と勧める。一方 ducarian は初期のwish確率が低いため更新の繰り返しは不利で、wish狙いなら完走を勧める。双方とも数値付き検証なし（2026-05-30～31）。[対立する返信](https://www.reddit.com/r/KingShot/comments/1trt735/pretty_much_sums_up_this_game/)
- 2026-06-11～12のスレッドでは、「次のカード代とリセット代が同額になったら更新、直前が倍率ならもう1枚」という助言が複数。別の返信は4枚開けて更新を支持。各助言の実測母数は未記載。[戦略スレッド](https://www.reddit.com/r/KingShot/comments/1u31w00/how_do_you_maximise_rewards_from_mystic_divination/)
- 2026-02-07の戦略スレッドで eri q-p は「正確な確率を入れた数十万回のシミュレーションでは5枚更新が最良」と自己報告。ただしコード、入力確率表、目的関数、結果表を本文から検証できない。同スレッドには4枚最適と断言する反論もある。[戦略スレッド](https://www.reddit.com/r/KingShot/comments/1qy1q2q/any_strategy_for_mystic_divination_as_f2p/)
- 2026-08-22の投稿では、公開された確率表を根拠に「wishを見つけるまで全部開くしかない」とする返信と、4枚更新を続ける返信が対立。双方の母数はない。[変更議論](https://www.reddit.com/r/KingShot/comments/1vvjz8k/mystic_divination_changed/)

### Inferences
- 4～5枚更新の経験談をwish最短獲得の証明としては扱えない。倍率や副報酬の価値、リセット費用、段階別の条件付き当選率が必要。

### Gaps
- 同条件で「4枚更新」「5枚更新」「wishまで完走」を比較した公開の生ログ・再現可能なシミュレーションは確認できていない。

## Pity・重み・盤面固定か抽選時決定か

### Takeaway
重み付き抽選という見解は1.79%表示と整合的だが、内部抽選の時点を示す証拠はない。pity（回数による救済）も、最後の1枚で確実に取得できるという有限盤面上の保証を超える仕様は確認できない。

### Cited Findings
- 2025-06-28の Reddit 投稿では「カードは事前固定か」との問いに、表示確率があるのであらかじめプログラムされていると返信。別の投稿者は「どの位置を押しても同じ結果」と断言したが、試行数は記さず、倍率が遅く出た個人体験を根拠にしている。[旧スレッド](https://www.reddit.com/r/KingShot/comments/1lmfkpa/really_kingshot_thats_unfair/)
- 2026-05-02の返信は「選んだ時に odds を振るように見える」と推測し、別返信は盤面が均等選択の錯覚と主張。いずれも内部コードや再現実験はない。[1.79%スレッド](https://www.reddit.com/r/KingShot/comments/1t1gin0/mystic_divination_question/)
- 2026-05-31の ducarian は「位置は事前決定ではない」と断言。2026-05-30の CrystalizedC は「リフレッシュごとに報酬は決まっている、押す位置は無関係」と主張する。どちらも抽選時点の検証データを示していない。[相反する説明](https://www.reddit.com/r/KingShot/comments/1trt735/pretty_much_sums_up_this_game/)
- 2026-08-22のスレッドでは「full odds & loot groupings table が公開されたようだ」との個人コメントがあるが、表の写しと公開主体は確認できない。[変更議論](https://www.reddit.com/r/KingShot/comments/1vvjz8k/mystic_divination_changed/)
- ガイドは10枚全てを開けばwishを得る構造と記載するが、これは盤面内の確定取得であり、次の盤面に持ち越す pity の証拠ではない。[コミュニティガイド](https://www.kingshot.wiki/events/mystic-divination)

### Inferences
- 重み付き抽選は「各段階で残り報酬から抽選」でも「盤面生成時に重み付きで順序を確定」でも実現できるため、表示確率だけで抽選時点は判別できない。

### Gaps
- resetをまたぐpity、課金・残チケット数に連動する重み、抽選時点を示す公式説明や検証ログは発見できていない。公式サポートへの仕様確認が有効。[公式ヘルプ](https://centurygames.helpshift.com/hc/en/140-kingshot/section/1394-mystic-divination/)
- Discord公開ページとYouTubeコメントを対象に検索したが、この4論点について直接引用できる投稿は見つからなかった。非公開Discordの会話は調査対象外。
