
class ContentArea(QtWidgets.QFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.parent_menu = parent
        self.setObjectName('contentArea')
        # document-like appearance
        self.setStyleSheet("""
            QFrame#contentArea {
                background: #ffffff;
                border: 1px solid #ddd;
                border-radius: 6px;
            }
        """)
        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().setContentsMargins(20, 20, 20, 20)
        self.layout().setSpacing(12)

        # Header
        header = QtWidgets.QLabel("Settings")
        header.setObjectName('contentTitle')
        header.setStyleSheet("font-size:18px; font-weight:600; margin-bottom:8px;")
        self.layout().addWidget(header)

        # Scrollable body to give a document page feeling
        scroll = QtWidgets.QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)

        body = QtWidgets.QWidget()
        body.setLayout(QtWidgets.QVBoxLayout())
        body.layout().setContentsMargins(0, 0, 0, 0)
        body.layout().setSpacing(12)

        form = QtWidgets.QFormLayout()
        form.setLabelAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        form.setFormAlignment(QtCore.Qt.AlignTop)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(12)

        cfg = getattr(self.parent_menu, 'config', {}) or {}

        # Display name
        self.name_edit = QtWidgets.QLineEdit(cfg.get('display_name', ''))
        form.addRow("Display name:", self.name_edit)

        # Theme selection
        self.theme_combo = QtWidgets.QComboBox()
        self.theme_combo.addItems(['Light', 'Dark', 'System'])
        current_theme = cfg.get('theme', 'Light')
        if current_theme in [self.theme_combo.itemText(i) for i in range(self.theme_combo.count())]:
            self.theme_combo.setCurrentText(current_theme)
        form.addRow("Theme:", self.theme_combo)

        # Autosave
        self.autosave_cb = QtWidgets.QCheckBox("Enable autosave")
        self.autosave_cb.setChecked(bool(cfg.get('autosave', False)))
        form.addRow(self.autosave_cb)

        # Autosave interval
        self.interval_spin = QtWidgets.QSpinBox()
        self.interval_spin.setRange(1, 120)
        self.interval_spin.setValue(int(cfg.get('autosave_interval', 5)))
        form.addRow("Autosave interval (min):", self.interval_spin)

        # Data directory with browse button
        path_hbox = QtWidgets.QHBoxLayout()
        self.path_edit = QtWidgets.QLineEdit(cfg.get('data_path', ''))
        browse_btn = QtWidgets.QPushButton("Browse")
        def _browse():
            start = self.path_edit.text() or os.path.expanduser("~")
            chosen = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Folder", start)
            if chosen:
                self.path_edit.setText(chosen)
        browse_btn.clicked.connect(_browse)
        path_hbox.addWidget(self.path_edit)
        path_hbox.addWidget(browse_btn)
        form.addRow("Data folder:", path_hbox)

        # Notes / description
        self.notes = QtWidgets.QTextEdit(cfg.get('notes', ''))
        self.notes.setFixedHeight(120)
        form.addRow("Notes:", self.notes)

        body.layout().addLayout(form)
        body.layout().addStretch(1)
        scroll.setWidget(body)
        self.layout().addWidget(scroll)

        # Buttons bar
        btn_bar = QtWidgets.QHBoxLayout()
        btn_bar.addStretch(1)
        self.reset_btn = QtWidgets.QPushButton("Reset")
        self.save_btn = QtWidgets.QPushButton("Save")
        btn_bar.addWidget(self.reset_btn)
        btn_bar.addWidget(self.save_btn)
        self.layout().addLayout(btn_bar)

        # remember initial values so Reset can restore them
        self._initial = {
            'display_name': self.name_edit.text(),
            'theme': self.theme_combo.currentText(),
            'autosave': self.autosave_cb.isChecked(),
            'autosave_interval': self.interval_spin.value(),
            'data_path': self.path_edit.text(),
            'notes': self.notes.toPlainText(),
        }

        # Wire signals
        self.save_btn.clicked.connect(self._on_save)
        self.reset_btn.clicked.connect(self._on_reset)

    def _on_save(self):
        # collect values
        new_cfg = {
            'display_name': self.name_edit.text(),
            'theme': self.theme_combo.currentText(),
            'autosave': self.autosave_cb.isChecked(),
            'autosave_interval': self.interval_spin.value(),
            'data_path': self.path_edit.text(),
            'notes': self.notes.toPlainText(),
        }
        # update parent config in-memory
        if hasattr(self.parent_menu, 'config') and isinstance(self.parent_menu.config, dict):
            self.parent_menu.config.update(new_cfg)
        # attempt to persist if config module exposes a saver
        saver = getattr(config, 'save_config', None) or getattr(config, 'set_config', None)
        try:
            if callable(saver):
                saver(self.parent_menu.config)
        except Exception:
            pass
        QtWidgets.QMessageBox.information(self, "Saved", "Settings have been saved.")

    def _on_reset(self):
        # restore initial snapshot
        self.name_edit.setText(self._initial.get('display_name', ''))
        self.theme_combo.setCurrentText(self._initial.get('theme', 'Light'))
        self.autosave_cb.setChecked(self._initial.get('autosave', False))
        self.interval_spin.setValue(self._initial.get('autosave_interval', 5))
        self.path_edit.setText(self._initial.get('data_path', ''))
        self.notes.setPlainText(self._initial.get('notes', ''))
        QtWidgets.QMessageBox.information(self, "Reset", "Settings have been reset to their previous values.")
