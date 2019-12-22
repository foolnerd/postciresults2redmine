#!/usr/bin/python
# -*- coding:utf-8 -*-
from urllib.request import Request, urlopen
import urllib.parse
import os, datetime
import json
import shutil
from xml.etree.ElementTree import *
from pathlib import Path

# 個人設定画面に表示されているAPIキー
api_key = 'c16ff9813ae9bc15535afac4a9171bfd5e8f8447'
# エビデンスファイルパス(OS依存絶対パスなので要判別)
if os.name == 'nt':
    evipath = 'C:/tmp/evidence.zip'
    reportpath = 'C:/jenkins/workspace/ixsie_auto_uat/target/surefire-reports/'
    root_dir = 'C:/Users/mnt/Pictures/errorlog'
else:
    evipath = '/tmp/evidence.zip'
    reportpath = '/var/lib/jenkins/workspace/ixsie_auto_uat/target/surefire-reports/'
    root_dir = '/tmp/Pictures/errorlog'

pt = Path(reportpath)
reports =list(pt.glob("*.xml"))

# reports = [
# "TEST-jp.ixseltest.IxSelTestApplicationTests.xml",
# "TEST-jp.ixseltest.IxSelTestWeeklyApplicationTests.xml",
# "TEST-jp.ixseltest.IxSelTestMonthlyApplicationTests.xml",
# "TEST-jp.ixseltest.IxSelTestYearlyApplicationTests.xml",
# "TEST-jp.ixseltest.IxSelTestOcasionallyApplicationTests.xml",
# "TEST-jp.ixsieClass.IxsieClassRegTest.xml",
# "TEST-jp.ixsieClass.IxsieGrowthRecTest.xml",
# "TEST-jp.ixsieClass.IxsieMealTest.xml",
# "TEST-jp.ixsieClass.IxsieSleepingTest.xml",
# "TEST-jp.ixsieClass.IxsieSleepTest.xml"
# ]

#del C:\tmp\evidence.zip
os.remove(evipath) if os.path.exists(evipath) else None
#テスト実行結果エラーエビデンス画像ファイル一式をZIP圧縮して画像ディレクトリは丸ごと削除
#powershell compress-archive C:\Users\mnt\Pictures\errorlog\ C:\tmp\evidence.zip
shutil.make_archive(os.path.splitext(evipath)[0], 'zip', root_dir) if os.path.exists(root_dir) else None
#rmdir C:\Users\mnt\Pictures\errorlog\
shutil.rmtree(root_dir) if os.path.exists(root_dir) else None

#エビデンスファイルの存在チェック
if os.path.exists(evipath):
	# エビデンスファイルをアップロード
	evifile = open(evipath, 'rb')
	evicontent = evifile.read()
	evifile.close()

	uploadsUrl = 'http://redmine.uatenv.work/uploads.json'
	issueUrl = 'http://redmine.uatenv.work/projects/ixsie-uat-ci/issues.json'
	request = Request(uploadsUrl, data=evicontent)
	request.add_header('Content-Type', 'application/octet-stream')
	request.add_header('X-Redmine-API-Key', api_key)
	request.get_method = lambda: 'POST'
	response = urlopen(request)
	res = response.read()
	# レスポンスから発行されたtokenを取得
	resjson = json.loads(res.decode('utf-8'))
	token = resjson[u'upload'][u'token']

	# 登録用のデータ
	#pythonのxmlパーサを使用してUAT結果のxmlファイル(5つ)を解析し、成功件数、エラー件数を取得集計する
	sumfail = 0
	numsuccess = 0
	for report in reports:
#		if os.path.exists(reportpath + report):
		if os.path.exists(str(report)):
#			elmtree = parse(reportpath + report) # xmlをparseしてElementTree取得
			elmtree = parse(str(report)) # xmlをparseしてElementTree取得
			rootelem = elmtree.getroot() # xmlのルート要素を取得(getrootの返値がRootElement)
			# attribute(tests(全件数)/errors/skipped/failures各件数)の取得
			err = rootelem.get("errors", "0") # エラー件数(非存在時に備えてデフォ値0)
			skip = rootelem.get("skipped", "0")
			fail = rootelem.get("failures", "0")
			sumfail = sumfail + int(err) + int(skip) + int(fail)
			numsuccess = numsuccess + int(rootelem.get("tests")) # 一旦総テスト件数を集計

	numsuccess = numsuccess - sumfail # 総テスト件数-総失敗数=成功数
	#上記を元に新規チケットのタイトル(日付/件数入り)を生成する
	currentDate = datetime.date.today()
	subjectstr = "CI Result {} SUCCESS-{} FAIL-{}".format(currentDate, numsuccess, sumfail)

	issue = {}
	issue[u'project_id'] = 2 #UAT CI結果
	issue[u'subject'] = subjectstr
	issue[u'tracker_id'] = 6 #CI
	issue[u'fixed_version_id'] = 59 #ixsie
	issue[u'status_id'] = 8 if sumfail == 0 else 9 #成功=8,失敗=9
	#issue[u'description'] = u'reports from CI run'
	evidata = {}
	evidata[u'token'] = token
	evidata[u'filename'] = u'evidence.zip'
	evidata[u'content_type'] = u'application/octet-stream'
	issue[u'uploads'] = [evidata]
	data = {}
	data[u'issue'] = issue
	# JSON形式の文字列を取得
	jsonstr = json.dumps(data).encode("utf-8")
	request = Request(issueUrl, data=jsonstr)
	request.add_header('Content-Type', 'application/json')
	request.add_header('X-Redmine-API-Key', api_key)
	request.get_method = lambda: 'POST'
	# 登録実行
	response = urlopen(request)
	ret = response.read().decode("utf-8")
	#print('Res from Redmine:', ret)

	#tmpフォルダにあるエビデンスのzipファイルを削除する
	os.remove(evipath)
else:
	print("no evidence file!")