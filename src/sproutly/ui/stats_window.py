from sproutly import db
import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter, QFrame, QPushButton,
)


def _make_stat_card(title: str, value: str) -> QWidget:
    """전체 요약용 카드 위젯"""
    box = QFrame()
    box.setFrameShape(QFrame.Shape.StyledPanel)
    box.setStyleSheet("""
        QFrame {
            background-color: #2a2a2a;
            border-radius: 6px;
            padding: 8px;
        }
    """)
    layout = QVBoxLayout(box)
    layout.setContentsMargins(10, 6, 10, 6)

    title_label = QLabel(title)
    title_label.setStyleSheet("color: #aaa; font-size: 11px;")

    value_label = QLabel(value)
    value_label.setStyleSheet("color: #fff; font-size: 18px; font-weight: bold;")

    layout.addWidget(title_label)
    layout.addWidget(value_label)
    return box


class StatsWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("통계")
        self.resize(1280, 720)

        self._build_ui()
        self.refresh()

    def _build_ui(self):
        root = QVBoxLayout(self)

        # 상단: 새로고침 버튼
        top_bar = QHBoxLayout()
        top_bar.addStretch(1)
        self.refresh_btn = QPushButton("새로고침")
        self.refresh_btn.clicked.connect(self.refresh)
        top_bar.addWidget(self.refresh_btn)
        root.addLayout(top_bar)

        # 전체 요약 카드들
        self.summary_layout = QHBoxLayout()
        self.summary_layout.setSpacing(8)
        root.addLayout(self.summary_layout)

        # 본문: 좌(테이블) / 우(그래프)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 좌측: 곡별 테이블
        self.song_table = QTableWidget(0, 5)
        self.song_table.setHorizontalHeaderLabels(
            ["곡명", "Buttons", "최고점", "평균점", "플레이"]
        )
        self.song_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        for i in range(1, 5):
            self.song_table.horizontalHeader().setSectionResizeMode(
                i, QHeaderView.ResizeMode.ResizeToContents
            )
        self.song_table.verticalHeader().setVisible(False)
        self.song_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.song_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.song_table.itemSelectionChanged.connect(self._on_song_selected)
        splitter.addWidget(self.song_table)

        # 우측: 그래프
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(8, 0, 0, 0)

        self.graph_title = QLabel("곡을 선택하면 점수 추이가 표시됩니다")
        self.graph_title.setStyleSheet("font-size: 14px; font-weight: bold; padding: 4px;")
        right_layout.addWidget(self.graph_title)

        # PyQtGraph 위젯
        pg.setConfigOptions(antialias=True, background='#1a1a1a', foreground='#ddd')
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel('left', 'Score')
        self.plot_widget.setLabel('bottom', 'Play #')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        right_layout.addWidget(self.plot_widget)

        splitter.addWidget(right_panel)
        splitter.setSizes([550, 730])
        root.addWidget(splitter, 1)

    def refresh(self):
        # 전체 요약
        # 기존 카드 제거
        while self.summary_layout.count():
            item = self.summary_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)

        s = db.get_overall_stats()
        cards = [
            ("총 플레이", f"{s['total_plays']:,}"),
            ("등록 곡 수", f"{s['unique_songs']:,}"),
            ("평균 정확도", f"{s['avg_accuracy']:.2f}%"),
            ("점수 갱신", f"{s['score_grown_count']:,}회"),
        ]
        for title, value in cards:
            self.summary_layout.addWidget(_make_stat_card(title, value))
        self.summary_layout.addStretch(1)

        # 곡별 테이블
        songs = db.get_per_song_stats()
        self.song_table.setRowCount(len(songs))
        for i, song in enumerate(songs):
            self.song_table.setItem(i, 0, QTableWidgetItem(song['title']))
            self.song_table.setItem(i, 1, QTableWidgetItem(str(song['buttons'])))
            self.song_table.setItem(i, 2, QTableWidgetItem(f"{song['best_score']:,}"))
            self.song_table.setItem(i, 3, QTableWidgetItem(f"{int(song['avg_score']):,}"))
            self.song_table.setItem(i, 4, QTableWidgetItem(str(song['play_count'])))

        # 그래프 초기화
        self.plot_widget.clear()
        self.graph_title.setText("곡을 선택하면 점수 추이가 표시됩니다")

    def _on_song_selected(self):
        items = self.song_table.selectedItems()
        if not items:
            return
        row = items[0].row()
        title = self.song_table.item(row, 0).text()
        buttons = int(self.song_table.item(row, 1).text())

        history = db.get_song_history(title, buttons)
        self._draw_graph(title, buttons, history)

    def _draw_graph(self, title: str, buttons: int, history: list[dict]):
        self.plot_widget.clear()
        self.graph_title.setText(f"{title} ({buttons}B) — {len(history)}회 플레이")

        if not history:
            return

        x = list(range(1, len(history) + 1))
        y = [h['score'] for h in history]

        # 선 + 점
        pen = pg.mkPen(color='#4a9eff', width=2)
        self.plot_widget.plot(
            x, y,
            pen=pen,
            symbol='o',
            symbolSize=8,
            symbolBrush='#4a9eff',
            symbolPen=None,
        )

        # 최고점 라인
        best = max(y)
        best_line = pg.InfiniteLine(
            pos=best,
            angle=0,
            pen=pg.mkPen('#ff6b6b', width=1, style=Qt.PenStyle.DashLine),
            label=f'Best: {best:,}',
            labelOpts={'color': '#ff6b6b', 'position': 0.05},
        )
        self.plot_widget.addItem(best_line)

        # X축 라벨을 날짜로 (호버 툴팁)
        # 단순화: 그냥 인덱스로 표시. 호버 시 날짜 보여주려면 ScatterPlotItem 따로 처리 필요
        self.plot_widget.setLabel('bottom',
                                  f'Play # ({history[0]["created_at"][:10]} ~ {history[-1]["created_at"][:10]})')
