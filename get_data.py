#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import os
import sys
import serial
import time
from dotenv import load_dotenv

# .envファイルの内容を読み込見込む
load_dotenv()

# Bルート認証ID（東京電力パワーグリッドから郵送で送られてくるヤツ）
rbid = os.environ['B_ROUTE_AUTHENTICATION_ID']
# Bルート認証パスワード（東京電力パワーグリッドからメールで送られてくるヤツ）
rbpwd = os.environ['B_ROUTE_AUTHENTICATION_PASSWORD']
# シリアルポートデバイス名
serialPortDev = '/dev/ttyUSB0'  # Linux(ラズパイなど）の場合

# シリアルポート初期化
ser = serial.Serial(serialPortDev, 115200)

# とりあえずバージョンを取得してみる（やらなくてもおｋ）
ser.write("SKVER\r\n")
print(ser.readline(), end="") # エコーバック
print(ser.readline(), end="") # バージョン

# Bルート認証パスワード設定
ser.write("SKSETPWD C " + rbpwd + "\r\n")
print(ser.readline(), end="") # エコーバック
print(ser.readline(), end="") # OKが来るはず（チェック無し）

# Bルート認証ID設定
ser.write("SKSETRBID " + rbid + "\r\n")
print(ser.readline(), end="") # エコーバック
print(ser.readline(), end="") # OKが来るはず（チェック無し）

scanDuration = 4;   # スキャン時間。サンプルでは6なんだけど、4でも行けるので。（ダメなら増やして再試行）
scanRes = {} # スキャン結果の入れ物

# スキャンのリトライループ（何か見つかるまで）
while not scanRes.has_key("Channel") :
	# アクティブスキャン（IE あり）を行う
	# 時間かかります。10秒ぐらい？
	ser.write("SKSCAN 2 FFFFFFFF " + str(scanDuration) + "\r\n")

	# スキャン1回について、スキャン終了までのループ
	scanEnd = False
	while not scanEnd :
		line = ser.readline()
		print(line, end="")

		if line.startswith("EVENT 22") :
			# スキャン終わったよ（見つかったかどうかは関係なく）
			scanEnd = True
		elif line.startswith("  ") :
			# スキャンして見つかったらスペース2個あけてデータがやってくる
			# 例
			#  Channel:39
			#  Channel Page:09
			#  Pan ID:FFFF
			#  Addr:FFFFFFFFFFFFFFFF
			#  LQI:A7
			#  PairID:FFFFFFFF
			cols = line.strip().split(':')
			scanRes[cols[0]] = cols[1]
	scanDuration+=1

	if 7 < scanDuration and not scanRes.has_key("Channel"):
		# 引数としては14まで指定できるが、7で失敗したらそれ以上は無駄っぽい
		print("スキャンリトライオーバー")
		sys.exit()  #### 糸冬了 ####

# スキャン結果からChannelを設定。
ser.write("SKSREG S2 " + scanRes["Channel"] + "\r\n")
print(ser.readline(), end="") # エコーバック
print(ser.readline(), end="") # OKが来るはず（チェック無し）

# スキャン結果からPan IDを設定
ser.write("SKSREG S3 " + scanRes["Pan ID"] + "\r\n")
print(ser.readline(), end="") # エコーバック
print(ser.readline(), end="") # OKが来るはず（チェック無し）

# MACアドレス(64bit)をIPV6リンクローカルアドレスに変換。
# (BP35A1の機能を使って変換しているけど、単に文字列変換すればいいのではという話も？？)
ser.write("SKLL64 " + scanRes["Addr"] + "\r\n")
print(ser.readline(), end="") # エコーバック
ipv6Addr = ser.readline().strip()
print(ipv6Addr)

# PANA 接続シーケンスを開始します。
ser.write("SKJOIN " + ipv6Addr + "\r\n");
print(ser.readline(), end="") # エコーバック
print(ser.readline(), end="") # OKが来るはず（チェック無し）

# PANA 接続完了待ち（10行ぐらいなんか返してくる）
bConnected = False
while not bConnected :
	line = ser.readline()
	print(line, end="")
	if line.startswith("EVENT 24") :
		print("PANA 接続失敗")
		sys.exit()  #### 糸冬了 ####
	elif line.startswith("EVENT 25") :
		# 接続完了！
		bConnected = True
		print("PANA 接続成功")

# これ以降、シリアル通信のタイムアウトを設定
ser.timeout = 2

# スマートメーターがインスタンスリスト通知を投げてくる
# (ECHONET-Lite_Ver.1.12_02.pdf p.4-16)
print(ser.readline(), end="") #無視

# TODO:積算電力量を出すための情報を先に取得

# 無限ループで情報取得
while True:
	# ECHONET Lite フレーム作成
	echonetLiteFrame = ""
	echonetLiteFrame += "\x10\x81"	    # EHD　EHD1:「0x10」固定、EHD2:0x81:ECHONET Lite規格書に記載された電文形式
	echonetLiteFrame += "\x00\x01"	    # TID　Transaction IDは任意の値でOK
	# ここから EDATA
	echonetLiteFrame += "\x05\xFF\x01"  # SEOJ　0x05,0xFF,0x01=コントローラクラス(送信元オブジェクト)
	echonetLiteFrame += "\x02\x88\x01"  # DEOJ　0x02,0x88,0x01=低圧スマート電力量メーター(相手先オブジェクト)
	echonetLiteFrame += "\x62"		    # ESV　0x62:プロパティ値読み出し要求
	echonetLiteFrame += "\x03"		    # OPC　0x01:要求数3個
	echonetLiteFrame += "\xE7"		    # EPC　0xE7:瞬時電力計測値
	echonetLiteFrame += "\x00"		    # PDC　0x00:読み出し要求の場合は0x00固定でOK
										# EDT　null:読み出し要求のためPDC=0となりEDTは不要
	echonetLiteFrame += "\xE8"		    # EPC　0xE8:瞬時電流計測値
	echonetLiteFrame += "\x00"		    # PDC　0x00:読み出し要求の場合は0x00固定でOK
										# EDT　null:読み出し要求のためPDC=0となりEDTは不要
	echonetLiteFrame += "\xE0"		    # EPC　0xE0:積算電力量計測値(正方向計測値)
	echonetLiteFrame += "\x00"		    # PDC　0x00:読み出し要求の場合は0x00固定でOK
										# EDT　null:読み出し要求のためPDC=0となりEDTは不要

	# コマンド送信
	command = "SKSENDTO 1 {0} 0E1A 1 {1:04X} {2}".format(ipv6Addr, len(echonetLiteFrame), echonetLiteFrame)
	ser.write(command)

	print(ser.readline(), end="") # エコーバック
	print(ser.readline(), end="") # EVENT 21 が来るはず（チェック無し）
	print(ser.readline(), end="") # OKが来るはず（チェック無し）
	line = ser.readline()		  # ERXUDPが来るはず
	print(line, end="")

	# 無限ループ脱出用カウンタ
	debugCount = 0

	# 受信データはたまに違うデータが来たり、
	# 取りこぼしたりして変なデータを拾うことがあるので
	# チェックを厳しめにしてます。
	if line.startswith("ERXUDP") :
		# ↓こういうレスポンスが戻ってくるので最後の計測値部分のみ使う
		# ERXUDP FE80:0000:0000:0000:021C:6400:0364:831F FE80:0000:0000:0000:1207:23FF:FEA0:7898 0E1A 0E1A 001C64000364831F 1 001E 1081000102880105FF017203E7040000055EE80400000082E00400052155
		cols = line.strip().split(' ')
		res = cols[8]   # UDP受信データ部分
		tid = res[4:4+4]
		seoj = res[8:8+6]
		deoj = res[14:14+6]
		ESV = res[20:20+2]
		OPC = res[22:22+2]
		EPC = res[24:24+2] # 最初に処理するEPCを設定　各ブロックの最後で更新する
		print(U"res:{0}".format(res)) # debug
		if seoj == "028801" and ESV == "72" : # スマートメーター(028801)から来た応答が(0x72:プロパティ値読み出し応答(0x62の応答))なら解析に進む
			# 実際の各計測値が入っている部分を取得
			dataBlock = res[26:]

			# dataBlockが無くなるまでループ
			while len(dataBlock) != 0 :
				print(U"EPC:{0}".format(EPC)) # debug
				print(U"dataBlock:{0}".format(dataBlock)) # debug
				debugCount += 1

				if EPC == "E7" : # 瞬時電力計測値(0xE7)
					dataSize = int(dataBlock[0:2], 16)
					print(U"dataSize:{0}".format(dataSize)) # debug
					print(U"data:{0}".format(dataBlock[2:2+dataSize*2])) # debug
					intPower = int(dataBlock[2:2+dataSize*2], 16)
					print(u"瞬時電力計測値:{0}[W]".format(intPower))

					# 次の処理のためにEPCとdataBlockを更新
					EPC = dataBlock[2+dataSize*2:2+dataSize*2+2]
					dataBlock = dataBlock[2+dataSize*2+2:]

				elif EPC == "E8" : # 瞬時電流(0xE8)
					dataSize = int(dataBlock[0:2], 16)
					ampereData = dataBlock[2:2+dataSize*2]
					hexAmpereR = ampereData[0:4]
					hexAmpereT = ampereData[4:8]
#					print(U"hexAmpereR:{0}".format(hexAmpereR)) # debug
#					print(U"hexAmpereT:{0}".format(hexAmpereT)) # debug
					intAmpereR = int(hexAmpereR, 16)
					intAmpereT = int(hexAmpereT, 16)
#					print(U"intAmpereR:{0}".format(intAmpereR)) # debug
#					print(U"intAmpereT:{0}".format(intAmpereT)) # debug
					intAmpereR = float(intAmpereR)
					intAmpereT = float(intAmpereT)
					intAmpereR = intAmpereR / 10 # 0.1A固定で送られてくるため
					intAmpereT = intAmpereT / 10 # 0.1A固定で送られてくるため

					print(u"瞬時電流計測値 R相:{0}[A]、T相:{1}[A]、計:{2}[A]".format(intAmpereR, intAmpereT, intAmpereR + intAmpereT)) 

					# 次の処理のためにdataBlockを更新
					EPC = dataBlock[2+dataSize*2:2+dataSize*2+2]
					dataBlock = dataBlock[2+dataSize*2+2:]

				elif EPC == "E0" : # 積算電力量(0xE0)
					dataSize = int(dataBlock[0:2], 16)
					intPower = int(dataBlock[2:2+dataSize*2], 16)
					print(u"積算電力量:{0}[kWh]".format(intPower))

					# 次の処理のためにdataBlockを更新
					EPC = dataBlock[2+dataSize*2:2+dataSize*2+2]
					dataBlock = dataBlock[2+dataSize*2+2:]

				if debugCount > 5 : # 無限ループ脱出用デバッグ処理
					break
				
		

# 無限ループだからここには来ないけどな
ser.close()