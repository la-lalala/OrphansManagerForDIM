# OrphansManagerForDIM 0.2alpha

### 概要
* 野良Projectの管理が面倒だったので、DAZ Install Manager(DIM)で認識できるzipに変換するn番煎じ

### 対象
* DAZ Studio使ってる人
* mac使ってる人（winは動作検証してない）
* python使える人

### HowToUse（てきとう）
1. "Content"が直下に含まれる"行儀の良い"野良Projectのディレクトリ達をInputsにぶちこむ
1. コンソールでOrphansManagerのディレクトリに移動、python genzip.py
1. Outputsにzipファイルができてるので、DIMのDownloadディレクトリにぶち込む
1. DIMの更新ボタンを押すとReadyToInstallの一覧に出てくるはず

### 注意事項
1. 作りたてなのでコード読める人だけ使ってね
1. このコードが原因で起きたあらゆる損害には一切の責任を負わないよ
1. 既存のものがあるか調べずに作っちゃったからもっといいツールがあるかもよ（あったら教えてね）
1. ツッコミ待ちです、クソみたいな部分があるはずだから教えてね

### 今後の予定
1. ~~すでに変換済みのディレクトリを再度変換しないようにする~~
1. zipファイルをそのまま変換できるようにする
1. Contentが直下に含まれないヤンチャなProjectも拾えるようにする
1. 誰にでも使えるGUIのやつにする