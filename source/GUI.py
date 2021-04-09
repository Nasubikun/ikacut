#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
import io
import json
import sys

from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import (QAction, QApplication, QComboBox, QFileDialog,
                             QLabel, QLineEdit, QMainWindow, QPushButton,
                             QTextEdit, QProgressBar, QVBoxLayout ,QCheckBox)

from PyQt5.QtCore import pyqtSlot

from modules import whole_movie

# [TODO]CSVじゃないときにエラーを出す

# テキストフォーム中心の画面のためQMainWindowを継承する
class Example(QMainWindow):

    # settings={}

    def __init__(self):
        super().__init__()
        self.movieObj = whole_movie()
        self.movieObj.signal.connect(self.update_status)
        self.movieObj.sig_tqdm.connect(self.update_tqdm)
        self.movieObj.sig_state.connect(self.update_state)
        self.initUI()


    def initUI(self):
        # self.initSettings()
        # self.settings = self.importSettings()
        self.statusBar()
        defaultFontSize = 10
        # 左揃えのX座標
        defaultLineLeft =40
        # メニューバーのアイコン設定
        openFile = QAction('Open', self)
        # ショートカット設定
        openFile.setShortcut('Ctrl+O')
        # ステータスバー設定
        openFile.setStatusTip('Open new File')
        openFile.triggered.connect(self.showDialog)

        # メニューバー作成
        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(openFile)

        openFileButton = QPushButton("ファイルを開く", self)
        openFileButton.setFont(QFont('Arial', defaultFontSize))
        openFileButton.move(defaultLineLeft,48)
        openFileButton.clicked.connect(self.showDialog)

        self.openFileLabel = QLabel(self)
        self.openFileLabel.setFont(QFont('Arial', defaultFontSize))
        self.openFileLabel.move(160,53)
        self.openFileLabel.setText("ファイルが開かれていません")
        self.openFileLabel.adjustSize()

        self.writeWholeButton = QCheckBox('全試合を繋げた動画ファイル書き出す',self)
        self.writeWholeButton.toggle()
        self.writeWholeButton.move(defaultLineLeft,200)
        self.writeWholeButton.adjustSize()

        self.forceExecButton = QCheckBox('前回のログを無視して再実行（非推奨）',self)
        self.forceExecButton.move(defaultLineLeft,225)
        self.forceExecButton.adjustSize()

        executeButton = QPushButton("処理開始", self)
        executeButton.setFont(QFont('Arial', defaultFontSize))
        executeButton.move(315, 98)

        # クリックされたらbuttonClickedの呼び出し
        executeButton.clicked.connect(self.requestButtonClicked) 

        self.pbar = QProgressBar(self)
        # self.pbar.setTextVisible(False)
        self.pbar.setMinimumWidth(255)
        self.pbar.move(defaultLineLeft,98)

        self.ETALabel = QLabel(self)
        self.ETALabel.move(defaultLineLeft+120,138)
        self.ETALabel.setMinimumWidth(120)
        self.ETALabel.setFont(QFont('Arial', defaultFontSize-2))

        self.stateLabel = QLabel(self)
        self.stateLabel.move(defaultLineLeft,138)
        self.stateLabel.setMinimumWidth(120)
        self.stateLabel.setFont(QFont('Arial', defaultFontSize-2))

        self.setGeometry(300, 300, 450, 270)
        self.setWindowTitle('イカカット')
        self.show()

    def requestButtonClicked(self):
        # fname[0]は選択したファイルのパス（ファイル名を含む
        # self.exportSettings()
        self.exec_process()
    
        

    def showDialog(self):

        open_path = "c://"
        user_name = os.getlogin()

        # 第二引数はダイアログのタイトル、第三引数は表示するパス
        if os.path.exists("c://Users/"+user_name+"/Videos"):
            open_path = "c://Users/"+user_name+"/Videos"
        self.fname = QFileDialog.getOpenFileName(self, 'Open file', open_path,"Video files(*.mp4 *.mkv *.flv *.avi);;All files(*)")
        if self.fname[0]:
            self.openFileLabel.setText(self.fname[0])
            self.openFileLabel.adjustSize()

    # def initSettings(self):
    #     if not os.path.exists("settings.json"):
    #         self.exportSettings()

    # def importSettings(self):
    #     with open("settings.json") as sjson:
    #         try:
    #             sjson_load = json.load(sjson)
    #             return sjson_load
    #         except Exception as e:
    #             return

    # def exportSettings(self):
    #     self.settings={}
    #     with open("settings.json","w") as sjson:
    #         json.dump(self.settings,sjson)

    # def closeEvent(self, event):
        # self.exportSettings()

    @pyqtSlot(int)
    def update_status(self, progress):
        self.pbar.setValue(progress)   # progressBarを進める

    @pyqtSlot(str)
    def update_tqdm(self,output):
        self.ETALabel.setText(output)

    @pyqtSlot(str)
    def update_state(self,output):
        self.stateLabel.setText(output)

    @pyqtSlot()
    def exec_process(self):
        if self.fname[0]:
            # ファイル読み込み

            self.movieObj.initialize(src_path=self.fname[0])

            self.pbar.setValue(0)
            self.pbar.setMinimum(0)
            self.pbar.setMaximum(int(self.movieObj.num_of_frames))
            self.movieObj.setOptions(force_exec=self.forceExecButton.checkState(),write_clips=1,write_whole=self.writeWholeButton.checkState())
            self.movieObj.start()

        


if __name__ == '__main__':

    app = QApplication(sys.argv)
    ex = Example()
    sys.exit(app.exec_())