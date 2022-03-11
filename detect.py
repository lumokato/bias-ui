import sys
from Ui_main import Ui_MainWindow
from PyQt5.QtWidgets import QMainWindow, QApplication, QFileDialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FC
from calib_check import plot_bias_simple


class MyWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super(MyWindow, self).__init__(parent)
        self.setupUi(self)
        self.lineEdit.setText("G:/calib-data/0208-A2")  # 演示路径
        plt.rcParams['font.sans-serif'] = ['SimHei']
        plt.rcParams['axes.unicode_minus'] = False
        plt.rcParams['font.size'] = 15  # 字体大小
        self.fig1 = plt.figure(figsize=(5, 5), dpi=80)
        self.fig2 = plt.figure(figsize=(10, 5), dpi=80)
        self.widget1 = FC(self.fig1)
        # self.widget.setObjectName("widget")
        self.figLayout1.addWidget(self.widget1)
        self.widget2 = FC(self.fig2)
        # self.widget.setObjectName("widget")
        self.figLayout2.addWidget(self.widget2)

    def mybutton(self):
        options = QFileDialog.Options()
        self.path_dir = QFileDialog.getExistingDirectory(self, "打开", "", options=options)
        # self.path_dir = QFileDialog.getExistingDirectory(self, "打开", "G:/calib-data", options=options)    # 默认位置
        self.lineEdit.setText(self.path_dir)

    def draw_cmd(self):
        try:
            self.fig1.clear()
            self.fig2.clear()
            self.path_dir = self.lineEdit.text()
            path_l = self.path_dir + "/L/"
            path_r = self.path_dir + "/R/"
            if self.sender() == self.draw_multi:
                pathc_l = path_l
                pathc_r = path_r
            elif self.sender() == self.draw_left:
                pathc_l = path_l
                pathc_r = None
            elif self.sender() == self.draw_right:
                pathc_l = None
                pathc_r = path_r
            text_show = plot_bias_simple(path_l, path_r, pathc_l, pathc_r, self.fig1, self.fig2)
            self.widget1.draw()
            self.widget2.draw()
            self.textBrowser.setText(text_show)
        except Exception as e:
            print(e)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    myWin = MyWindow()
    myWin.show()
    sys.exit(app.exec_())
