#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
from datetime import datetime, timedelta

from PyQt5.QtCore import (Qt, QCoreApplication, QSettings, QUrl,
                          QTranslator, QDate, QDateTime, QTimer)
from PyQt5.QtGui import QIcon, QFont, QDesktopServices
from PyQt5.QtWidgets import (QApplication, QDialog, QMainWindow,
                             QTreeWidgetItem, QHeaderView,
                             QMessageBox)

from database import *
import contract_rc
from ui_contract import *

from database import *
from item import *
from accrediting import *

_translate = QCoreApplication.translate

class Settings(QSettings):
    pInstance = None
    
    def __init__(self, parent=None):
        super(Settings, self).__init__("config.ini", QSettings.IniFormat, parent)
    
    @classmethod
    def instance(cls):
        if cls.pInstance is None:
            cls.pInstance = cls()
        return cls.pInstance
    
    def getLastOpenDatabase(self):
        return self.value("last-open-database", None)
    
    def setLastOpenDatabase(self, database):
        self.setValue("last-open-database", database)

class Contract(QMainWindow):
    def __init__(self, parent=None):
        super(Contract, self).__init__(parent)
        self.ui = Ui_Contract()
        self.ui.setupUi(self)
        
        self.addMenus()
        
        self.database = None
        
        self.ui.itemTreeWidget.setHeaderLabels([_translate('Contract', "Date"), \
                                                _translate('Contract', "Unit"), \
                                                _translate('Contract', "Name")])
        self.ui.itemTreeWidget.header().resizeSection(0, 128)
        self.ui.itemTreeWidget.header().resizeSection(1, 32)
        self.ui.itemTreeWidget.itemClicked.connect(self.viewItemDetail)
        self.ui.itemTreeWidget.itemDoubleClicked.connect(self.editItem)
        self.ui.itemTreeWidget.setContextMenuPolicy(Qt.ActionsContextMenu)
        editAction = QAction(_translate("Contract", "Edit"), self.ui.itemTreeWidget)
        editAction.triggered.connect(self.itemContextMenuEditAction)
        self.ui.itemTreeWidget.addAction(editAction)
        deleteAction = QAction(_translate("Contract", "Delete"), self.ui.itemTreeWidget)
        deleteAction.triggered.connect(self.itemContextMenuDeleteAction)
        self.ui.itemTreeWidget.addAction(deleteAction)
        
        database = Settings.instance().getLastOpenDatabase()
        if database is not None and Database.instance().isExist(database):
            Database.instance().open(database)
            self.loadItems()
    
    def addMenus(self):
        menuBar = self.menuBar()
        self.fileMenu = menuBar.addMenu(_translate("Contract", "File"))
        self.fileMenu.addAction(_translate('Contract', 'Open Database'), self.openDatabase)
        self.fileMenu.addAction(_translate('Contract', 'New Database'), self.newDatabase)
        self.fileMenu.addAction(_translate('Contract', 'Exit'), QCoreApplication.instance().quit)
        
        self.itemMenu = menuBar.addMenu(_translate("Contract", "Item"))
        self.itemMenu.addAction(_translate('Contract', 'New Item'), self.newItem)
        self.itemMenu.setDisabled(True)
        
        self.helpMenu = menuBar.addMenu(_translate("Contract", "Help"))
        self.helpMenu.addAction(_translate('Contract', 'Tutorial'), self.tutorial)
        self.helpMenu.addAction(_translate('Contract', 'About...'), self.about)
    
    def newDatabase(self):
        dialog = NewDatabaseDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self.loadItems()
    
    def openDatabase(self):
        dialog = OpenDatabaseDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self.loadItems()
    
    def loadItems(self):
        if self.database != None:
            self.ui.itemTreeWidget.takeTopLevelItem(self.ui.itemTreeWidget.indexOfTopLevelItem(self.database))
        Settings.instance().setLastOpenDatabase(Database.instance().name())
        self.database = QTreeWidgetItem([Database.instance().name()])
        self.ui.itemTreeWidget.addTopLevelItem(self.database)
        session = Database.instance().session()
        for item in session.query(ItemModel).order_by(desc(ItemModel.startDate)):
            self.database.addChild(QTreeWidgetItem([item.startDatetoString(), str(item.quantity) \
                                                 , item.name, str(item.id)]))
        self.database.setExpanded(True)
        self.itemMenu.setEnabled(True)
        self.viewItemDetail(self.database, 0)
    
    def newItem(self):
        dialog = ItemViewDialog(None, self)
        if dialog.exec() == QDialog.Accepted:
            item = dialog.item
            self.database.addChild(QTreeWidgetItem([item.startDatetoString(), \
                                                 str(item.quantity), \
                                                 item.name, str(item.id)]))
            self.database.sortChildren(0, Qt.DescendingOrder)
            self.viewItemDetail(self.database, 0)
    
    def tutorial(self):
        QDesktopServices.openUrl(QUrl.fromEncoded("README.html"))
    
    def about(self):
        QMessageBox.about(self, _translate("Contract", "Contract Manager"), _translate("Contract", "If you have any questions please feel free to contact xlongfeng<xlongfeng@126.com>"))
    
    def viewItemDetail(self, treeWidgetItem, column):
        if "sep-rc" in sys.argv:
            baseUrl =  QUrl.fromLocalFile(QDir.currentPath() + "/")
        else:
            baseUrl =  QUrl('qrc:///')
        
        if treeWidgetItem == self.database:
            self.ui.detailWebView.setHtml(Accrediting().toSummaryHtml(), baseUrl)
        else:
            self.ui.detailWebView.setHtml(Accrediting(int(treeWidgetItem.text(3))).toItemHtml(), baseUrl)
    
    def editItem(self, treeWidgetItem, column):
        if treeWidgetItem == self.database:
            return
        dialog = ItemViewDialog(int(treeWidgetItem.text(3)), self)
        if dialog.exec() == QDialog.Accepted:
            item = dialog.item
            treeWidgetItem.setText(0, item.startDatetoString())
            treeWidgetItem.setText(1, str(item.quantity))
            treeWidgetItem.setText(2, str(item.name))
            self.database.sortChildren(0, Qt.DescendingOrder)
            self.viewItemDetail(treeWidgetItem, 0)
    
    def itemContextMenuEditAction(self):
        selectedItems = self.ui.itemTreeWidget.selectedItems()
        if len(selectedItems) > 0 and selectedItems[0] != self.database:
            self.editItem(selectedItems[0], 0)
    
    def itemContextMenuDeleteAction(self):
        selectedItems = self.ui.itemTreeWidget.selectedItems()
        if len(selectedItems) > 0 and selectedItems[0] != self.database:
            treeWidgetItem = selectedItems[0]
            if QMessageBox.question(self, "", _translate("Contract", "Continue to delete {}?").format(treeWidgetItem.text(2))) == QMessageBox.Yes:
                session = Database.instance().session()
                item = session.query(ItemModel).filter_by(id = int(treeWidgetItem.text(3))).one()
                session.delete(item)
                session.commit()
                self.database.takeChild(self.database.indexOfChild(treeWidgetItem))

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    if "sep-rc" in sys.argv:
        app.setWindowIcon(QIcon('images/contract.ico'))
    else:
        app.setWindowIcon(QIcon(':/images/contract.ico'))
    
    font = app.font()  
    font.setPointSize(10)
    app.setFont(font)
    
    translator = QTranslator(app)
    if "sep-rc" in sys.argv:
        translator.load('contract_zh_CN')
    else:
        translator.load(':/contract_zh_CN')
    app.installTranslator(translator)
    
    contract = Contract()
    contract.show()
    
    sys.exit(app.exec_())
