# FCDEV transfer utility
fcdevutyは、FC開発機 NF-FCDEV-100 とのデータ送受信を行うためのツールです。

# Features
主に下記のような処理を行う事が出来ます。

* nesファイルの書き込み
* EX RAMへのデータ書き込み
* PRG ROMへのデータ書き込み
* CHR ROMへの書き込み
* PRG ROMまたはEX RAMからのデータ読み込み

# Install
```
pip install git+https://github.com/h-o-soft/fcdevuty
```


# Usage

```
usage: fcdevuty [-h] [-r] [-m {nes,chr,bin,read}] [-a ADDR] [-s SIZE] [-p PORT] [-b BANK] [-v] [path [path ...]]

FCDEV transfer utility Version 0.1.0 Copyright 2022 H.O SOFT Inc.

positional arguments:
  path                  file path(s)

optional arguments:
  -h, --help            show this help message and exit
  -r, --reset           manual reset mode
  -m {nes,chr,bin,read}, --mode {nes,chr,bin,read}
                        transfer mode (default = nes)
  -a ADDR, --addr ADDR  transfer address (default = 0x6000)
  -s SIZE, --size SIZE  read size (default = 0x2000)
  -p PORT, --port PORT  serial port name (auto search if not present)
  -b BANK, --bank BANK  bank number (default = 0)
  -v, --verbose         verbose mode
```

## mode: nes / ファイルの転送

```
fcdevuty nes-file-path
```
または
```
fcdevuty -m nes nes-file-path
```

nes形式のファイルをFC開発機に転送します。転送出来る形式はFC開発機の制限により、mapper 0またはmapper 3のみとなります。それ以外のnesファイルを指定した場合の動作は不定です。

## mode: chr / CHR ROMの書き換え

例1: 指定ファイルをバンク0に書き込む
```
fcdevuty -m chr chr-file-path [chr-file-path2 ...]
```

例2: 指定ファイルをバンク1に書き込む
```
fcdevuty -m chr -b 1 chr-file-path [chr-file-path2 ...]
```

指定したファイルをCHR ROMに書き込みます。

8kb単位で書き込み、8kbをオーバーした場合、次のバンクに書き込みます。

32kbのファイルを指定する事で、4バンクに対して書き込みを行えます(が、チェックが甘いので動くかどうか不明です)。

また、複数ファイルを指定した場合は、指定したファイルを全て連結した上で転送処理を行います。例えば4kbのファイル2つを指定すると、1バンクぶんのCHR ROMを書き換えます。

## mode: bin / EX RAMへの書き込みまたはPRG ROMへの書き込み

例1: 指定ファイルを 0x6000 に書き込む
```
fcdevuty -m bin file-path [file-path2 ...]
```

例2: 指定ファイルを バンク1の 0x7000 から書き込む
```
fcdevuty -m bin -b 1 -a 0x7000 file-path [file-path2 ...]
```

例3: 指定ファイルを PRG ROMの0x8000 から書き込む
```
fcdevuty -m bin -a 0x8000 file-path [file-path2 ...]
```

任意のバイナリファイルをEX RAMまたはPRG ROMに書き込みます。

デフォルトでは 0x6000 から書き込みを行います。ファイルサイズはチェックしていないので、注意してください。

EX RAMへの書き込みの場合、8kbを超えた場合は次のバンクに切り替えて書き込みを行います。

アドレスを0x8000以降にする事でPRG ROMも書き換える事が出来ます

## mode: read / メモリからデータを読み込みファイルに保存する

```
fcdevuty -m read -a 0x6000 -s 0x2000 file-path
```

指定したアドレスから指定したサイズだけデータを読み込み、指定ファイルにバイナリデータとして保存します。

読み込むサイズは ```-s```オプションで指定してください。

## アドレス指定

```-a``` オプションのあとにアドレス値を指定する事で、mode binでの書き込み先、readでの読み込み先を指定出来ます。

アドレスは10進数または、接頭辞に「0x」を付与した16進数で指定してください。

## バンク指定

```-b``` オプションのあとにバンク値を指定する事で、mode chrでのCHR ROM書き込みバンク、mode binでのEX RAM書き込みバンク、mode readでのEX RAM読み込みバンクを指定出来ます。

## シリアルポートの指定

本ツールは、何も指定しないと、起動時にFC開発機が存在するシリアルポートを検索し、そちらを使うようになっていますが、検索に時間がかかるため、シリアルポートが判明している場合は、直接指定してやる事で起動時間を短縮出来ます。

```
-p port名
```

port名はWindowsの場合は COM3 など、Macの場合は /dev/tty.usbmodemFC_DEV1 などになるでしょう。

## 手動リセット指定

FC本体をリセット改造していない場合は ```-r``` オプションをつけて起動してください。

必要なタイミングでリセットを押下するよう指示が出ますので、指示が出たタイミングにてリセットを手動で押す事で、正常にデータの転送/nesファイルの実行が出来ます。


# Note

明らかにチェックが甘いのでバンク関連などマトモに動かない部分が多いと思います。注意してお使いください。

# Author

* OGINO Hiroshi
* H.O SOFT Inc.
* twitter: @honda_ken

# License

"fcdevuty" is under [MIT license](LICENSE)
