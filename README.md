# nyanko_automation

Mac の iPhone Mirroring を画面認識しながら操作するためのローカル自動化プロジェクトです。

## 前提

- macOS の「iPhone ミラーリング」を使って、Mac 上にゲーム画面を表示する
- 自動操作は Mac のマウス・スクリーンショット経由で行う
- Terminal または実行に使うアプリへ、macOS の `アクセシビリティ` と `画面収録` 権限を付与する

利用先アプリの規約や保護機構を確認し、禁止されている自動化や回避行為には使わないでください。

## セットアップ

```bash
uv sync --extra dev
```

## 動作確認

```bash
uv run nyanko-auto doctor
uv run nyanko-auto windows
uv run nyanko-auto capture
uv run nyanko-auto snippets
uv run nyanko-auto routines
uv run nyanko-auto run-snippet tap_battle_start
uv run nyanko-auto run-snippet detect_stamina_recover_popup
uv run nyanko-auto run-snippet detect_extra_stage
uv run nyanko-auto run --cycles 1
```

`capture` は iPhone Mirroring らしきウィンドウ領域を探して `assets/screenshots/latest.png` に保存します。見つからない場合は画面全体のスクリーンショットを保存します。

## 周回ループ

周回は `config/snippets.json` の `routines` で制御します。各ルーチンは汎用スニペットを組み合わせた遷移表です。

初期状態では `packman` が既定ルーチンです。

```text
detect_stamina_recover_available
-> tap_battle_start
-> wait_battle_start
-> wait_initial_money
-> deploy_unit_slot_4
-> wait_battle_progress
-> detect_drop_reward
-> detect_extra_stage
-> return_to_map
-> detect_stamina_recover_available
```

主な分岐:

- `detect_stamina_recover_available`: true なら `tap_stamina_recover_button` へ、false なら `tap_battle_start` へ
- `detect_stamina_recover_popup`: true なら `accept_stamina_recover` へ、false なら `tap_battle_start` へ
- `detect_extra_stage`: true なら `accept_extra_stage` へ、false なら `return_to_map` へ
- `return_to_map`: 戦闘終了画面の右上ボタンを押してマップへ戻る

座標は iPhone Mirroring ウィンドウ左上を原点にした現在の表示サイズ（ポイント）です。`uv run nyanko-auto capture` の画像で表示サイズを変えた場合は、座標を取り直してください。

各スニペットは、判定だけ、1クリックだけ、待機だけ、のいずれかに寄せています。

別ステージの周回を追加するときは `snippets` の部品を増やすか再利用し、`routines` に新しい `id` / `start` / `transitions` を追加します。

クリック座標や画像テンプレートが未確定のステップは `enabled: false` にしてあります。動作確認しながら `x` / `y` / `template` を埋め、必要なものだけ `enabled: true` にしてください。

実クリックを有効にする場合だけ `--live` を付けます。

```bash
uv run nyanko-auto run-snippet tap_battle_start --live
uv run nyanko-auto run-snippet return_to_map --repeat 2 --live
uv run nyanko-auto run --routine packman --cycles 1 --live
```

ライブ実行時は `[live] tap x,y` の後ろに、画面上のウィンドウ位置を加えた実座標が表示されます。実座標がミラーリング画面の外なら、設定座標が現在のウィンドウ表示サイズと合っていません。`capture` で現在画像を取り直し、座標はウィンドウ左上基準のポイントで指定します。

スニペット単体の調整中は `run-snippet` を使います。指定したスニペットだけを実行し、次のスニペットには遷移しません。

判定だけを行うスニペットは `kind: "condition"` で定義します。ルーチン側ではその判定結果を `if_result` で受けて遷移を分けます。

## 次にやること

1. iPhone Mirroring を起動してゲーム画面を表示する
2. `uv run nyanko-auto windows` でウィンドウ名を確認する
3. `uv run nyanko-auto capture` の画像で座標・テンプレートを調整する
4. `config/snippets.json` の該当ステップを有効化する
