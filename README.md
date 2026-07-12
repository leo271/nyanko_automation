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
uv run nyanko-auto run --cycles 1
```

`capture` は iPhone Mirroring らしきウィンドウ領域を探して `assets/screenshots/latest.png` に保存します。見つからない場合は画面全体のスクリーンショットを保存します。

## 周回ループ

周回は `config/snippets.json` のスニペット遷移で制御します。初期状態では以下の順番です。

```text
check_energy -> start_battle -> deploy_units -> finish_battle -> check_energy
```

- `check_energy`: 統率力確認&統率力回復
- `start_battle`: 戦闘開始
- `deploy_units`: キャラクター出動
- `finish_battle`: 戦闘終了→マップ帰還

クリック座標や画像テンプレートが未確定のステップは `enabled: false` にしてあります。動作確認しながら `x` / `y` / `template` を埋め、必要なものだけ `enabled: true` にしてください。

実クリックを有効にする場合だけ `--live` を付けます。

```bash
uv run nyanko-auto run --cycles 1 --live
```

## 次にやること

1. iPhone Mirroring を起動してゲーム画面を表示する
2. `uv run nyanko-auto windows` でウィンドウ名を確認する
3. `uv run nyanko-auto capture` の画像で座標・テンプレートを調整する
4. `config/snippets.json` の該当ステップを有効化する
