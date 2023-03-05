# Wi-Sun_RL7023_Test
Raspberry Piに繋いだRL7023でスマートメーターから情報を取得する

## 参考サイト
- [スマートメーターの情報を最安ハードウェアで引っこ抜く - Qiita](https://qiita.com/rukihena/items/82266ed3a43e4b652adb)
- [Wi-SUNで使用電力を可視化 - いんくらyochさんの日記](https://inqra-yoch.hatenablog.jp/entry/20210423/1619107578)
- [シリアル通信でスマートメーター（Bルートサービス）から電力測定値を読む (r271-635)](https://netlog.jpn.org/r271-635/2020/11/echonet-smartmeter-serialaccess.html)
- [電気スマートメーターに替えて自作で電気の見える化装置製作 | ページ 2 | Beヨンド](https://bey.jp/?p=72123&page=2)
- [ECHONET Liteの電文　作成方法 - Qiita](https://qiita.com/miyazawa_shi/items/725bc5eb6590be72970d)

- [ECHONET Lite規格書 Ver.1.14](https://echonet.jp/spec_v114_lite/)
- [APPENDIX ECHONET機器オブジェクト詳細規定Release Q](https://echonet.jp/spec_object_rq/)

## 準備するもの
```ruby:.env
B_ROUTE_AUTHENTICATION_ID  = "【電力会社からもらうBルートID】"
B_ROUTE_AUTHENTICATION_PASSWORD = "【電力会社からもらうBルートPASS】"
```
