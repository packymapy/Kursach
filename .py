import sys
import psycopg2
from psycopg2 import sql
import pandas as pd
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
import hashlib
from datetime import datetime, date
import csv

DARK_STYLE = """
QWidget {
    background-color: #2b2b2b;
    color: #ffffff;
    font-family: Segoe UI;
    font-size: 11px;
}

QPushButton {
    background-color: #3c3c3c;
    border: 1px solid #555;
    border-radius: 3px;
    padding: 5px;
    min-width: 80px;
}

QPushButton:hover {
    background-color: #4a4a4a;
    border: 1px solid #666;
}

QPushButton:pressed {
    background-color: #2a2a2a;
}

QLineEdit, QComboBox, QTextEdit, QSpinBox, QDoubleSpinBox {
    background-color: #353535;
    border: 1px solid #555;
    border-radius: 3px;
    padding: 3px;
    selection-background-color: #505050;
}

QTableView {
    background-color: #353535;
    alternate-background-color: #3a3a3a;
    gridline-color: #555;
    border: 1px solid #555;
}

QHeaderView::section {
    background-color: #3c3c3c;
    padding: 5px;
    border: 1px solid #555;
}

QTabWidget::pane {
    border: 1px solid #555;
    background-color: #2b2b2b;
}

QTabBar::tab {
    background-color: #3c3c3c;
    padding: 8px 15px;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background-color: #505050;
}

QMenuBar {
    background-color: #3c3c3c;
}

QMenuBar::item:selected {
    background-color: #505050;
}

QMenu {
    background-color: #3c3c3c;
    border: 1px solid #555;
}

QMenu::item:selected {
    background-color: #505050;
}

QLabel {
    color: #ffffff;
}

QGroupBox {
    border: 1px solid #555;
    border-radius: 5px;
    margin-top: 10px;
    padding-top: 10px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px 0 5px;
}

QStatusBar {
    background-color: #3c3c3c;
    color: #ffffff;
}
"""


class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.current_user = None
        self.current_role = None

    def connect(self):
        try:
            self.connection = psycopg2.connect(
                database="photo_studio",
                user="postgres",
                password="pgadmin",
                host="localhost",
                port="5432"
            )
            return True
        except Exception as e:
            QMessageBox.critical(None, "Ошибка подключения", f"Не удалось подключиться к базе данных:\n{str(e)}")
            return False

    def login(self, username, password):
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT user_id, username, password_hash, role, name 
                FROM users 
                WHERE username = %s
            """, (username,))
            user_data = cursor.fetchone()
            cursor.close()
            if user_data:
                password_hash = hashlib.sha256(password.encode()).hexdigest()
                if user_data[2] == password_hash:
                    self.current_user = {
                        'id': user_data[0],
                        'username': user_data[1],
                        'role': user_data[3],
                        'name': user_data[4]
                    }
                    self.current_role = user_data[3]
                    return True
        except Exception as e:
            print(f"Ошибка при входе: {e}")
        return False

    def get_table_permissions(self, role):
        permissions = {
            'owner': {
                'post': ['select', 'insert', 'update', 'delete'],
                'employee': ['select', 'insert', 'update', 'delete'],
                'client': ['select', 'insert', 'update', 'delete'],
                'payment_method': ['select', 'insert', 'update', 'delete'],
                'contact_method': ['select', 'insert', 'update', 'delete'],
                'service': ['select', 'insert', 'update', 'delete'],
                'order_info': ['select', 'insert', 'update', 'delete'],
                'orders': ['select', 'insert', 'update', 'delete'],
                'users': ['select', 'insert', 'update', 'delete']
            },
            'administrator': {
                'post': ['select', 'insert', 'update'],
                'employee': ['select', 'insert', 'update'],
                'client': ['select', 'insert', 'update', 'delete'],
                'payment_method': ['select', 'insert', 'update'],
                'contact_method': ['select', 'insert', 'update'],
                'service': ['select', 'insert', 'update'],
                'order_info': ['select', 'insert', 'update'],
                'orders': ['select', 'insert', 'update', 'delete'],
                'users': ['select', 'insert', 'update']
            },
            'worker': {
                'client': ['select', 'insert', 'update'],
                'service': ['select'],
                'order_info': ['select', 'insert'],
                'orders': ['select', 'insert']
            },
            'accountant': {
                'client': ['select'],
                'service': ['select'],
                'order_info': ['select'],
                'orders': ['select'],
                'payment_method': ['select'],
                'employee': ['select']
            }
        }
        return permissions.get(role, {})

    def execute_query(self, query, params=None):
        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            if query.strip().upper().startswith('SELECT'):
                data = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                cursor.close()
                return data, columns
            else:
                self.connection.commit()
                cursor.close()
                return None
        except Exception as e:
            self.connection.rollback()
            raise e

    def execute_query_with_return(self, query, params=None):
        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            if query.strip().upper().startswith('INSERT') and 'RETURNING' in query.upper():
                data = cursor.fetchone()
                self.connection.commit()
                cursor.close()
                return data
            else:
                self.connection.commit()
                cursor.close()
                return None
        except Exception as e:
            self.connection.rollback()
            raise e

    def get_all_data(self, table_name):
        query = "SELECT * FROM {}".format(table_name)
        return self.execute_query(query)


class LoginWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Вход в систему - Фотостудия')
        self.setFixedSize(300, 200)
        layout = QVBoxLayout()
        title_label = QLabel('ФОТОСТУДИЯ')
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 20px;")
        form_layout = QFormLayout()
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText('Введите логин')
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText('Введите пароль')
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow('Логин:', self.username_input)
        form_layout.addRow('Пароль:', self.password_input)
        button_layout = QHBoxLayout()
        self.login_button = QPushButton('Войти')
        self.login_button.clicked.connect(self.attempt_login)
        self.cancel_button = QPushButton('Выход')
        self.cancel_button.clicked.connect(self.close)
        button_layout.addWidget(self.login_button)
        button_layout.addWidget(self.cancel_button)
        layout.addWidget(title_label)
        layout.addLayout(form_layout)
        layout.addLayout(button_layout)
        self.setLayout(layout)

    def attempt_login(self):
        username = self.username_input.text()
        password = self.password_input.text()
        if not username or not password:
            QMessageBox.warning(self, 'Ошибка', 'Введите логин и пароль')
            return
        if not self.db_manager.connect():
            return
        if self.db_manager.login(username, password):
            self.accept()
        else:
            QMessageBox.critical(self, 'Ошибка', 'Неверный логин или пароль')


class ReceiptDialog(QDialog):
    def __init__(self, order_id, client_info, payment_method, contact_method, cart_items, total_sum, parent=None):
        super().__init__(parent)
        self.order_id = order_id
        self.client_info = client_info
        self.payment_method = payment_method
        self.contact_method = contact_method
        self.cart_items = cart_items
        self.total_sum = total_sum
        self.initUI()

    def initUI(self):
        self.setWindowTitle(f'Чек заказа #{self.order_id}')
        self.setFixedSize(500, 600)
        layout = QVBoxLayout()
        header_label = QLabel('ФОТОСТУДИЯ')
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setMaximumHeight(150)
        current_time = datetime.now()
        receipt_text = f"""ЧЕК #{self.order_id}
{'-' * 40}
Дата: {current_time.strftime('%d.%m.%Y')}
Время: {current_time.strftime('%H:%M:%S')}
{'-' * 40}
Клиент: {self.client_info}
Способ оплаты: {self.payment_method}
Способ связи: {self.contact_method}
{'-' * 40}
ПОЗИЦИИ:
"""
        for item in self.cart_items:
            receipt_text += f"\n{item['name']}"
            receipt_text += f"\n{item['quantity']} x {item['price']:.2f} = {item['total']:.2f} руб."
        receipt_text += f"""
{'-' * 40}
ИТОГО: {self.total_sum:.2f} руб.
{'-' * 40}
СПАСИБО ЗА ПОКУПКУ!
"""
        info_text.setPlainText(receipt_text)
        info_text.setFont(QFont("Courier New", 10))
        button_layout = QHBoxLayout()
        save_csv_button = QPushButton('Сохранить в CSV')
        save_csv_button.clicked.connect(self.save_to_csv)
        print_button = QPushButton('Печать')
        print_button.clicked.connect(self.print_receipt)
        close_button = QPushButton('Закрыть')
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(save_csv_button)
        button_layout.addWidget(print_button)
        button_layout.addWidget(close_button)
        layout.addWidget(header_label)
        layout.addWidget(info_text)
        layout.addLayout(button_layout)
        self.setLayout(layout)

    def save_to_csv(self):
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, 'Сохранить чек в CSV',
                f'чек_{self.order_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
                'CSV Files (*.csv)'
            )
            if file_path:
                if not file_path.endswith('.csv'):
                    file_path += '.csv'
                current_time = datetime.now()
                data = [
                    ['ФОТОСТУДИЯ', ''],
                    ['ЧЕК', f'#{self.order_id}'],
                    ['Дата', current_time.strftime('%d.%m.%Y')],
                    ['Время', current_time.strftime('%H:%M:%S')],
                    ['Клиент', self.client_info],
                    ['Способ оплаты', self.payment_method],
                    ['Способ связи', self.contact_method],
                    ['', ''],
                    ['Позиции', 'Количество', 'Цена за ед.', 'Сумма']
                ]
                for item in self.cart_items:
                    data.append([
                        item['name'],
                        str(item['quantity']),
                        f"{item['price']:.2f}",
                        f"{item['total']:.2f}"
                    ])
                data.append(['', '', '', ''])
                data.append(['ИТОГО', '', '', f"{self.total_sum:.2f} руб."])
                data.append(['', '', '', ''])
                data.append(['СПАСИБО ЗА ПОКУПКУ!', '', '', ''])
                with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                    writer = csv.writer(csvfile, delimiter=';')
                    writer.writerows(data)
                QMessageBox.information(self, 'Успех', f'Чек сохранен в файл:\n{file_path}')
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Не удалось сохранить чек:\n{str(e)}')

    def print_receipt(self):
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, 'Сохранить чек для печати',
                f'чек_печать_{self.order_id}.txt',
                'Text Files (*.txt)'
            )
            if file_path:
                current_time = datetime.now()
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('=' * 40 + '\n')
                    f.write(' ' * 15 + 'ФОТОСТУДИЯ\n')
                    f.write('=' * 40 + '\n')
                    f.write(f'ЧЕК #{self.order_id}\n')
                    f.write('-' * 40 + '\n')
                    f.write(f'Дата: {current_time.strftime("%d.%m.%Y")}\n')
                    f.write(f'Время: {current_time.strftime("%H:%M:%S")}\n')
                    f.write('-' * 40 + '\n')
                    f.write(f'Клиент: {self.client_info}\n')
                    f.write(f'Способ оплаты: {self.payment_method}\n')
                    f.write(f'Способ связи: {self.contact_method}\n')
                    f.write('-' * 40 + '\n')
                    f.write('ПОЗИЦИИ:\n\n')
                    for item in self.cart_items:
                        f.write(f"{item['name']}\n")
                        f.write(f"{item['quantity']} x {item['price']:.2f} = {item['total']:.2f} руб.\n\n")
                    f.write('-' * 40 + '\n')
                    f.write(f'ИТОГО: {self.total_sum:.2f} руб.\n')
                    f.write('-' * 40 + '\n')
                    f.write('СПАСИБО ЗА ПОКУПКУ!\n')
                    f.write('=' * 40 + '\n')
                QMessageBox.information(self, 'Успех', f'Чек для печати сохранен:\n{file_path}')
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Не удалось сохранить для печати:\n{str(e)}')


class RecordDialog(QDialog):
    def __init__(self, db_manager, table_name, mode='add', record_id=None):
        super().__init__()
        self.db_manager = db_manager
        self.table_name = table_name
        self.mode = mode
        self.record_id = record_id
        self.fields = []
        self.initUI()
        self.load_record_data()

    def initUI(self):
        title = 'Редактировать запись' if self.mode == 'edit' else 'Добавить запись'
        self.setWindowTitle(f'{title} - {self.table_name}')
        self.setFixedSize(400, 400)
        layout = QVBoxLayout()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        form_widget = QWidget()
        self.form_layout = QFormLayout(form_widget)
        scroll.setWidget(form_widget)
        layout.addWidget(scroll)
        button_layout = QHBoxLayout()
        self.save_button = QPushButton('Сохранить')
        self.save_button.clicked.connect(self.save_record)
        self.cancel_button = QPushButton('Отмена')
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        self.setLayout(layout)

    def load_record_data(self):
        try:
            cursor = self.db_manager.connection.cursor()
            cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position
            """, (self.table_name,))
            columns_info = cursor.fetchall()
            cursor.close()
            for col_info in columns_info:
                column_name = col_info[0]
                data_type = col_info[1]
                is_nullable = col_info[2] == 'YES'
                if self.mode == 'add' and column_name.endswith('_id') and column_name != f"{self.table_name}_id":
                    if self.table_name == 'orders' and column_name == 'order_id':
                        continue
                    if not column_name.startswith(('client_', 'order_', 'payment_', 'service_', 'post_', 'contact_')):
                        continue
                label_text = column_name.replace('_', ' ').title()
                label = QLabel(label_text)
                widget = None
                if 'int' in data_type:
                    widget = QSpinBox()
                    widget.setRange(-1000000, 1000000)
                    if not is_nullable:
                        widget.setValue(0)
                elif 'numeric' in data_type or 'decimal' in data_type or 'float' in data_type:
                    widget = QDoubleSpinBox()
                    widget.setRange(-1000000, 1000000)
                    widget.setDecimals(2)
                    if not is_nullable:
                        widget.setValue(0.0)
                elif 'date' in data_type or 'timestamp' in data_type:
                    widget = QDateTimeEdit()
                    widget.setCalendarPopup(True)
                    widget.setDisplayFormat('yyyy-MM-dd HH:mm:ss')
                    widget.setDateTime(QDateTime.currentDateTime())
                elif 'bool' in data_type:
                    widget = QComboBox()
                    widget.addItems(['Нет', 'Да'])
                elif column_name.endswith('_id') and column_name != f"{self.table_name}_id":
                    widget = QComboBox()
                    self.load_foreign_key_data(column_name, widget)
                else:
                    widget = QLineEdit()
                    if not is_nullable and column_name != 'id':
                        widget.setPlaceholderText('Обязательное поле')
                if widget:
                    self.fields.append((column_name, widget, is_nullable, data_type))
                    self.form_layout.addRow(label, widget)
            if self.mode == 'edit' and self.record_id:
                if self.table_name == 'orders':
                    id_column = 'order_id'
                elif self.table_name == 'users':
                    id_column = 'user_id'
                else:
                    id_column = f"{self.table_name}_id"
                query = f"SELECT * FROM {self.table_name} WHERE {id_column} = %s"
                data, _ = self.db_manager.execute_query(query, (self.record_id,))
                if data and data[0]:
                    record = data[0]
                    for idx, (col_name, widget, is_nullable, data_type) in enumerate(self.fields):
                        if idx < len(record):
                            value = record[idx]
                            if value is not None:
                                self.set_widget_value(widget, value, data_type)

        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Не удалось загрузить данные:\n{str(e)}')

    def load_foreign_key_data(self, column_name, combo_box):
        try:
            ref_table = column_name.replace('_id', '')
            if ref_table == 'post':
                query = "SELECT post_id, name FROM post ORDER BY name"
            elif ref_table == 'client':
                query = "SELECT client_id, surname || ' ' || name as full_name FROM client ORDER BY surname"
            elif ref_table == 'service':
                query = "SELECT service_id, name FROM service ORDER BY name"
            elif ref_table == 'payment_method':
                query = "SELECT payment_method_id, name FROM payment_method ORDER BY name"
            elif ref_table == 'employee':
                query = "SELECT employee_id, surname || ' ' || name as full_name FROM employee ORDER BY surname"
            elif ref_table == 'contact_method':
                query = "SELECT contact_method_id, name FROM contact_method ORDER BY name"
            else:
                return
            data, _ = self.db_manager.execute_query(query)
            combo_box.addItem('-- Выберите --', None)
            for row in data:
                display_value = str(row[1]) if row[1] else f"ID: {row[0]}"
                combo_box.addItem(display_value, row[0])
        except Exception as e:
            print(f"Ошибка загрузки внешнего ключа {column_name}: {e}")

    def set_widget_value(self, widget, value, data_type):
        if isinstance(widget, QLineEdit):
            widget.setText(str(value))
        elif isinstance(widget, QSpinBox):
            widget.setValue(int(value))
        elif isinstance(widget, QDoubleSpinBox):
            widget.setValue(float(value))
        elif isinstance(widget, QDateTimeEdit):
            if isinstance(value, datetime):
                widget.setDateTime(QDateTime(value.year, value.month, value.day,
                                             value.hour, value.minute, value.second))
            else:
                try:
                    dt = QDateTime.fromString(str(value), 'yyyy-MM-dd HH:mm:ss')
                    if dt.isValid():
                        widget.setDateTime(dt)
                except:
                    pass
        elif isinstance(widget, QComboBox):
            if 'bool' in data_type:
                index = 1 if value else 0
                widget.setCurrentIndex(index)
            else:
                for i in range(widget.count()):
                    if widget.itemData(i) == value:
                        widget.setCurrentIndex(i)
                        break

    def save_record(self):
        try:
            columns = []
            values = []
            for col_name, widget, is_nullable, data_type in self.fields:
                value = self.get_widget_value(widget, data_type)
                if value is None and not is_nullable:
                    label = self.form_layout.labelForField(widget).text()
                    QMessageBox.warning(self, 'Ошибка', f'Поле "{label}" не может быть пустым')
                    return
                columns.append(col_name)
                values.append(value)
            if self.mode == 'add':
                filtered_columns = []
                filtered_values = []
                for col, val in zip(columns, values):
                    if val is not None:
                        filtered_columns.append(col)
                        filtered_values.append(val)
                placeholders = ', '.join(['%s'] * len(filtered_values))
                column_names = ', '.join(filtered_columns)
                query = f"INSERT INTO {self.table_name} ({column_names}) VALUES ({placeholders})"
                self.db_manager.execute_query(query, tuple(filtered_values))
            else:
                set_parts = []
                update_values = []
                for col, val in zip(columns, values):
                    set_parts.append(f"{col} = %s")
                    update_values.append(val)
                set_clause = ', '.join(set_parts)
                if self.table_name == 'orders':
                    id_column = 'order_id'
                elif self.table_name == 'users':
                    id_column = 'user_id'
                else:
                    id_column = f"{self.table_name}_id"
                query = f"UPDATE {self.table_name} SET {set_clause} WHERE {id_column} = %s"
                update_values.append(self.record_id)
                self.db_manager.execute_query(query, tuple(update_values))
            QMessageBox.information(self, 'Успех', 'Данные сохранены')
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Не удалось сохранить данные:\n{str(e)}')

    def get_widget_value(self, widget, data_type):
        if isinstance(widget, QLineEdit):
            text = widget.text().strip()
            return text if text else None
        elif isinstance(widget, QSpinBox):
            return widget.value()
        elif isinstance(widget, QDoubleSpinBox):
            return widget.value()
        elif isinstance(widget, QDateTimeEdit):
            return widget.dateTime().toString('yyyy-MM-dd HH:mm:ss')
        elif isinstance(widget, QComboBox):
            if 'bool' in data_type:
                return widget.currentText() == 'Да'
            else:
                return widget.currentData()
        return None


class DailySummaryDialog(QDialog):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.initUI()
        self.load_today_summary()

    def initUI(self):
        self.setWindowTitle('Ежедневный итог продаж')
        self.setFixedSize(600, 500)
        layout = QVBoxLayout()
        header_label = QLabel('ЕЖЕДНЕВНЫЙ ИТОГ ПРОДАЖ')
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 15px;")
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.dateChanged.connect(self.load_summary_by_date)
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel('Дата:'))
        date_layout.addWidget(self.date_edit)
        date_layout.addStretch()
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setFont(QFont("Courier New", 10))
        button_layout = QHBoxLayout()
        refresh_button = QPushButton('Обновить')
        refresh_button.clicked.connect(self.load_today_summary)
        export_csv_button = QPushButton('Экспорт в CSV')
        export_csv_button.clicked.connect(self.export_to_csv)
        print_button = QPushButton('Печать')
        print_button.clicked.connect(self.print_summary)
        close_button = QPushButton('Закрыть')
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(refresh_button)
        button_layout.addWidget(export_csv_button)
        button_layout.addWidget(print_button)
        button_layout.addWidget(close_button)
        layout.addWidget(header_label)
        layout.addLayout(date_layout)
        layout.addWidget(self.summary_text)
        layout.addLayout(button_layout)
        self.setLayout(layout)

    def load_today_summary(self):
        today = QDate.currentDate().toString('yyyy-MM-dd')
        self.load_summary(today)

    def load_summary_by_date(self):
        selected_date = self.date_edit.date().toString('yyyy-MM-dd')
        self.load_summary(selected_date)

    def load_summary(self, date_str):
        try:
            query = """
                SELECT 
                    COUNT(*) as orders_count,
                    SUM(total_sum) as total_revenue,
                    COUNT(DISTINCT client_id) as unique_clients
                FROM orders 
                WHERE date::date = %s
            """
            data, _ = self.db_manager.execute_query(query, (date_str,))
            orders_count = data[0][0] if data[0][0] else 0
            total_revenue = float(data[0][1]) if data[0][1] else 0.0
            unique_clients = data[0][2] if data[0][2] else 0
            service_query = """
                SELECT 
                    s.name as service_name,
                    SUM(oi.quantity) as total_quantity,
                    SUM(oi.quantity * s.service_price) as service_revenue
                FROM orders o
                JOIN order_info oi ON o.order_id = oi.order_id
                JOIN service s ON oi.service_id = s.service_id
                WHERE o.date::date = %s
                GROUP BY s.service_id, s.name
                ORDER BY service_revenue DESC
            """
            service_data, _ = self.db_manager.execute_query(service_query, (date_str,))
            report_lines = []
            report_lines.append("=" * 50)
            report_lines.append(f"ОТЧЕТ О ПРОДАЖАХ ЗА {date_str}")
            report_lines.append("=" * 50)
            report_lines.append("")
            report_lines.append("ОБЩАЯ СТАТИСТИКА:")
            report_lines.append("-" * 30)
            report_lines.append(f"Количество заказов: {orders_count}")
            report_lines.append(f"Уникальных клиентов: {unique_clients}")
            report_lines.append(f"Общая выручка: {total_revenue:.2f} руб.")
            report_lines.append("")
            if service_data:
                report_lines.append("СТАТИСТИКА ПО УСЛУГАМ:")
                report_lines.append("-" * 30)
                for service in service_data:
                    name = service[0] if service[0] else "Неизвестная услуга"
                    quantity = service[1] if service[1] else 0
                    revenue = float(service[2]) if service[2] else 0.0
                    report_lines.append(f"{name}:")
                    report_lines.append(f"  Количество: {quantity}")
                    report_lines.append(f"  Выручка: {revenue:.2f} руб.")
                    report_lines.append("")
            details_query = """
                SELECT 
                    o.order_id,
                    c.surname || ' ' || c.name as client_name,
                    o.total_sum,
                    pm.name as payment_method,
                    cm.name as contact_method,
                    o.date
                FROM orders o
                JOIN client c ON o.client_id = c.client_id
                JOIN payment_method pm ON o.payment_method_id = pm.payment_method_id
                JOIN contact_method cm ON o.contact_method_id = cm.contact_method_id
                WHERE o.date::date = %s
                ORDER BY o.date
            """
            details_data, _ = self.db_manager.execute_query(details_query, (date_str,))
            if details_data:
                report_lines.append("ДЕТАЛИ ЗАКАЗОВ:")
                report_lines.append("-" * 30)
                for order in details_data:
                    order_id = order[0]
                    client = order[1] if order[1] else "Неизвестный клиент"
                    total = float(order[2]) if order[2] else 0.0
                    payment = order[3] if order[3] else "Неизвестно"
                    contact = order[4] if order[4] else "Неизвестно"
                    order_time = order[5].strftime('%H:%M') if order[5] else "??:??"
                    report_lines.append(f"Заказ #{order_id} - {order_time}")
                    report_lines.append(f"  Клиент: {client}")
                    report_lines.append(f"  Сумма: {total:.2f} руб.")
                    report_lines.append(f"  Оплата: {payment}")
                    report_lines.append(f"  Способ связи: {contact}")
                    report_lines.append("")
            report_lines.append("=" * 50)
            report_lines.append(f"ИТОГО ЗА ДЕНЬ: {total_revenue:.2f} руб.")
            report_lines.append("=" * 50)
            self.summary_text.setPlainText("\n".join(report_lines))
        except Exception as e:
            self.summary_text.setPlainText(f"Ошибка загрузки данных:\n{str(e)}")

    def export_to_csv(self):
        try:
            selected_date = self.date_edit.date().toString('yyyy-MM-dd')
            file_path, _ = QFileDialog.getSaveFileName(
                self, 'Экспорт ежедневного отчета',
                f'ежедневный_отчет_{selected_date}.csv',
                'CSV Files (*.csv)'
            )
            if file_path:
                if not file_path.endswith('.csv'):
                    file_path += '.csv'
                report_text = self.summary_text.toPlainText()
                lines = report_text.split('\n')
                data = []
                for line in lines:
                    if line.strip():
                        if ':' in line:
                            parts = line.split(':', 1)
                            data.append([parts[0].strip(), parts[1].strip()])
                        else:
                            data.append([line.strip(), ''])
                with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                    writer = csv.writer(csvfile, delimiter=';')
                    writer.writerow(['Ежедневный отчет', f'Дата: {selected_date}'])
                    writer.writerow([])
                    for row in data:
                        writer.writerow(row)
                QMessageBox.information(self, 'Успех', f'Отчет сохранен в файл:\n{file_path}')
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Не удалось сохранить отчет:\n{str(e)}')

    def print_summary(self):
        try:
            selected_date = self.date_edit.date().toString('yyyy-MM-dd')
            file_path, _ = QFileDialog.getSaveFileName(
                self, 'Сохранить отчет для печати',
                f'ежедневный_отчет_{selected_date}.txt',
                'Text Files (*.txt)'
            )
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.summary_text.toPlainText())
                QMessageBox.information(self, 'Успех', f'Отчет для печати сохранен:\n{file_path}')
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Не удалось сохранить для печати:\n{str(e)}')


class MainWindow(QMainWindow):
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.current_table = None
        self.cart_items = []
        self.initUI()
        self.load_initial_data()

    def initUI(self):
        user_name = self.db_manager.current_user["name"]
        user_role = self.db_manager.current_user["role"]
        role_translations = {
            'owner': 'Владелец',
            'administrator': 'Администратор',
            'worker': 'Работник',
            'accountant': 'Бухгалтер'
        }
        role_display = role_translations.get(user_role, user_role)
        self.setWindowTitle(f'Фотостудия - {user_name} ({role_display})')
        self.setGeometry(100, 100, 1200, 700)
        self.setStyleSheet(DARK_STYLE)
        self.create_menu()
        self.statusBar().showMessage(f'Пользователь: {user_name} | Роль: {role_display}')
        self.central_widget = QTabWidget()
        self.setCentralWidget(self.central_widget)
        self.create_tabs_by_role()

    def create_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu('Файл')
        daily_summary_action = QAction('Ежедневный итог', self)
        daily_summary_action.triggered.connect(self.show_daily_summary)
        file_menu.addAction(daily_summary_action)
        file_menu.addSeparator()
        exit_action = QAction('Выход', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        data_menu = menubar.addMenu('Данные')
        refresh_action = QAction('Обновить данные', self)
        refresh_action.triggered.connect(self.refresh_data)
        data_menu.addAction(refresh_action)
        help_menu = menubar.addMenu('Помощь')
        about_action = QAction('О программе', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def create_tabs_by_role(self):
        role = self.db_manager.current_role
        permissions = self.db_manager.get_table_permissions(role)
        self.create_data_tab(permissions)
        if role in ['worker', 'administrator', 'owner']:
            self.create_order_tab()
        if role in ['accountant', 'administrator', 'owner']:
            self.create_finance_tab()
        if role in ['administrator', 'owner']:
            self.create_admin_tab()
        if role == 'owner':
            self.create_owner_tab()

    def create_data_tab(self, permissions):
        tab = QWidget()
        layout = QVBoxLayout()
        table_layout = QHBoxLayout()
        table_label = QLabel('Таблица:')
        self.table_combo = QComboBox()
        table_translations = {
            'post': 'Должности',
            'employee': 'Сотрудники',
            'client': 'Клиенты',
            'payment_method': 'Способы оплаты',
            'contact_method': 'Способы связи',
            'service': 'Услуги',
            'order_info': 'Информация о заказах',
            'orders': 'Заказы',
            'users': 'Пользователи'
        }
        for table in permissions.keys():
            display_name = table_translations.get(table, table)
            self.table_combo.addItem(display_name, table)
        self.table_combo.currentIndexChanged.connect(self.on_table_changed)
        table_layout.addWidget(table_label)
        table_layout.addWidget(self.table_combo)
        button_layout = QHBoxLayout()
        self.add_button = QPushButton('Добавить')
        self.add_button.clicked.connect(self.add_record)
        self.edit_button = QPushButton('Редактировать')
        self.edit_button.clicked.connect(self.edit_record)
        self.delete_button = QPushButton('Удалить')
        self.delete_button.clicked.connect(self.delete_record)
        self.update_buttons_state()
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addStretch()
        self.data_table = QTableWidget()
        self.data_table.setAlternatingRowColors(True)
        self.data_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.data_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addLayout(table_layout)
        layout.addLayout(button_layout)
        layout.addWidget(self.data_table)
        tab.setLayout(layout)
        self.central_widget.addTab(tab, 'Данные')

    def on_table_changed(self, index):
        table_name = self.table_combo.itemData(index)
        if table_name:
            self.load_table_data(table_name)

    def create_order_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        add_product_group = QGroupBox('Добавление товара/услуги')
        form_layout = QFormLayout()
        self.service_combo = QComboBox()
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setMinimum(1)
        self.quantity_spin.setMaximum(100)
        self.quantity_spin.setValue(1)
        self.add_to_cart_button = QPushButton('Добавить в корзину')
        self.add_to_cart_button.clicked.connect(self.add_to_cart)
        form_layout.addRow('Услуга:', self.service_combo)
        form_layout.addRow('Количество:', self.quantity_spin)
        form_layout.addRow('', self.add_to_cart_button)
        add_product_group.setLayout(form_layout)
        cart_group = QGroupBox('Корзина товаров')
        cart_layout = QVBoxLayout()
        self.cart_table = QTableWidget()
        self.cart_table.setColumnCount(5)
        self.cart_table.setHorizontalHeaderLabels(['ID услуги', 'Название', 'Цена за ед.', 'Количество', 'Сумма'])
        self.cart_table.setAlternatingRowColors(True)
        self.cart_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        cart_buttons_layout = QHBoxLayout()
        self.remove_from_cart_button = QPushButton('Удалить выбранное')
        self.remove_from_cart_button.clicked.connect(self.remove_from_cart)
        self.clear_cart_button = QPushButton('Очистить корзину')
        self.clear_cart_button.clicked.connect(self.clear_cart)
        cart_buttons_layout.addWidget(self.remove_from_cart_button)
        cart_buttons_layout.addWidget(self.clear_cart_button)
        cart_buttons_layout.addStretch()
        cart_layout.addWidget(self.cart_table)
        cart_layout.addLayout(cart_buttons_layout)
        cart_group.setLayout(cart_layout)
        order_group = QGroupBox('Оформление заказа')
        order_layout = QFormLayout()
        self.client_combo = QComboBox()
        self.payment_combo = QComboBox()
        self.contact_combo = QComboBox()
        self.total_label = QLabel('0.00 руб.')
        self.total_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #4CAF50;")
        self.create_order_button = QPushButton('Оформить заказ')
        self.create_order_button.clicked.connect(self.create_order)
        self.create_order_button.setEnabled(False)
        order_layout.addRow('Клиент:', self.client_combo)
        order_layout.addRow('Способ оплаты:', self.payment_combo)
        order_layout.addRow('Способ связи:', self.contact_combo)
        order_layout.addRow('Итоговая сумма:', self.total_label)
        order_layout.addRow('', self.create_order_button)
        order_group.setLayout(order_layout)
        layout.addWidget(add_product_group)
        layout.addWidget(cart_group)
        layout.addWidget(order_group)
        tab.setLayout(layout)
        self.central_widget.addTab(tab, 'Создание заказа')
        self.load_order_form_data()

    def create_finance_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        filter_group = QGroupBox('Фильтры отчета')
        filter_layout = QHBoxLayout()
        self.date_from = QDateEdit()
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        self.date_from.setCalendarPopup(True)
        self.date_to = QDateEdit()
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        filter_layout.addWidget(QLabel('С:'))
        filter_layout.addWidget(self.date_from)
        filter_layout.addWidget(QLabel('По:'))
        filter_layout.addWidget(self.date_to)
        self.generate_report_button = QPushButton('Сгенерировать отчет')
        self.generate_report_button.clicked.connect(self.generate_report)
        filter_layout.addWidget(self.generate_report_button)
        filter_group.setLayout(filter_layout)
        self.report_table = QTableWidget()
        export_layout = QHBoxLayout()
        self.export_excel_button = QPushButton('Экспорт в Excel')
        self.export_excel_button.clicked.connect(self.export_to_excel)
        self.export_csv_button = QPushButton('Экспорт в CSV')
        self.export_csv_button.clicked.connect(self.export_to_csv)
        export_layout.addWidget(self.export_excel_button)
        export_layout.addWidget(self.export_csv_button)
        export_layout.addStretch()
        layout.addWidget(filter_group)
        layout.addLayout(export_layout)
        layout.addWidget(self.report_table)
        tab.setLayout(layout)
        self.central_widget.addTab(tab, 'Финансовые отчеты')

    def create_admin_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        user_group = QGroupBox('Управление пользователями')
        user_layout = QVBoxLayout()
        user_form_layout = QFormLayout()
        self.new_username = QLineEdit()
        self.new_password = QLineEdit()
        self.new_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_role = QComboBox()
        self.new_role.addItems(['worker', 'administrator', 'accountant'])
        self.new_name = QLineEdit()
        user_form_layout.addRow('Логин:', self.new_username)
        user_form_layout.addRow('Пароль:', self.new_password)
        user_form_layout.addRow('Роль:', self.new_role)
        user_form_layout.addRow('Имя:', self.new_name)
        self.add_user_button = QPushButton('Добавить пользователя')
        self.add_user_button.clicked.connect(self.add_user)
        user_form_layout.addRow(self.add_user_button)
        user_group.setLayout(user_form_layout)
        layout.addWidget(user_group)
        layout.addStretch()
        tab.setLayout(layout)
        self.central_widget.addTab(tab, 'Администрирование')

    def create_owner_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        stats_group = QGroupBox('Статистика')
        stats_layout = QVBoxLayout()
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        self.load_stats_button = QPushButton('Загрузить статистику')
        self.load_stats_button.clicked.connect(self.load_statistics)
        stats_layout.addWidget(self.stats_text)
        stats_layout.addWidget(self.load_stats_button)
        stats_group.setLayout(stats_layout)
        backup_group = QGroupBox('Резервное копирование')
        backup_layout = QVBoxLayout()
        self.backup_button = QPushButton('Создать резервную копию БД')
        self.backup_button.clicked.connect(self.create_backup)
        backup_layout.addWidget(self.backup_button)
        backup_group.setLayout(backup_layout)
        layout.addWidget(stats_group)
        layout.addWidget(backup_group)
        layout.addStretch()
        tab.setLayout(layout)
        self.central_widget.addTab(tab, 'Владелец')

    def show_daily_summary(self):
        dialog = DailySummaryDialog(self.db_manager, self)
        dialog.exec()

    def load_initial_data(self):
        if self.table_combo.count() > 0:
            table_name = self.table_combo.itemData(0)
            if table_name:
                self.load_table_data(table_name)

    def load_table_data(self, table_name):
        try:
            data, columns = self.db_manager.get_all_data(table_name)
            self.current_table = table_name
            self.data_table.setRowCount(len(data))
            self.data_table.setColumnCount(len(columns))
            formatted_columns = []
            for col in columns:
                formatted = col.replace('_', ' ').title()
                formatted_columns.append(formatted)
            self.data_table.setHorizontalHeaderLabels(formatted_columns)
            for row_idx, row in enumerate(data):
                for col_idx, value in enumerate(row):
                    item = QTableWidgetItem(str(value) if value is not None else '')
                    self.data_table.setItem(row_idx, col_idx, item)
            self.data_table.resizeColumnsToContents()
            self.update_buttons_state()
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Не удалось загрузить данные:\n{str(e)}')

    def update_buttons_state(self):
        if not self.current_table:
            return
        role = self.db_manager.current_role
        permissions = self.db_manager.get_table_permissions(role)
        table_permissions = permissions.get(self.current_table, [])
        self.add_button.setEnabled('insert' in table_permissions)
        self.edit_button.setEnabled('update' in table_permissions)
        self.delete_button.setEnabled('delete' in table_permissions)

    def add_record(self):
        dialog = RecordDialog(self.db_manager, self.current_table, 'add')
        if dialog.exec():
            self.load_table_data(self.current_table)

    def edit_record(self):
        selected = self.data_table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, 'Ошибка', 'Выберите запись для редактирования')
            return
        record_id = self.data_table.item(selected, 0).text()
        dialog = RecordDialog(self.db_manager, self.current_table, 'edit', record_id)
        if dialog.exec():
            self.load_table_data(self.current_table)

    def delete_record(self):
        selected = self.data_table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, 'Ошибка', 'Выберите запись для удаления')
            return
        record_id = self.data_table.item(selected, 0).text()
        column_name = self.data_table.horizontalHeaderItem(0).text()
        original_column_name = column_name.lower().replace(' ', '_')
        if self.current_table == 'orders' and original_column_name == 'order id':
            original_column_name = 'order_id'
        reply = QMessageBox.question(self, 'Подтверждение',
                                     f'Вы уверены, что хотите удалить запись с ID {record_id}?',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                query = f"DELETE FROM {self.current_table} WHERE {original_column_name} = %s"
                self.db_manager.execute_query(query, (record_id,))
                self.load_table_data(self.current_table)
                QMessageBox.information(self, 'Успех', 'Запись удалена')
            except Exception as e:
                QMessageBox.critical(self, 'Ошибка', f'Не удалось удалить запись:\n{str(e)}')

    def load_order_form_data(self):
        try:
            query = "SELECT client_id, surname, name, patronymic, phone, email FROM client ORDER BY surname, name"
            data, _ = self.db_manager.execute_query(query)
            self.client_combo.clear()
            self.client_combo.addItem('-- Выберите клиента --', None)
            for row in data:
                client_id = row[0]
                surname = row[1] if row[1] else ""
                name = row[2] if row[2] else ""
                patronymic = row[3] if row[3] else ""
                phone = row[4] if row[4] else ""
                email = row[5] if row[5] else ""
                parts = []
                if surname:
                    parts.append(surname)
                if name:
                    parts.append(name)
                if patronymic:
                    parts.append(patronymic)
                display_name = " ".join(parts)
                if not display_name:
                    display_name = f"Клиент ID: {client_id}"
                contact_info = []
                if phone:
                    contact_info.append(f"тел: {phone}")
                if email:
                    contact_info.append(f"email: {email}")
                if contact_info:
                    display_name += f" ({', '.join(contact_info)})"
                self.client_combo.addItem(display_name, client_id)
            query = "SELECT service_id, name, service_price FROM service ORDER BY name"
            data, _ = self.db_manager.execute_query(query)
            self.service_combo.clear()
            for row in data:
                service_id = row[0]
                service_name = row[1] if row[1] else ""
                service_price = row[2] if row[2] else 0
                display_name = f"{service_name} - {float(service_price):.2f} руб."
                self.service_combo.addItem(display_name, service_id)
            data, _ = self.db_manager.get_all_data('payment_method')
            self.payment_combo.clear()
            self.payment_combo.addItem('-- Выберите способ оплаты --', None)
            for row in data:
                self.payment_combo.addItem(row[1], row[0])
            data, _ = self.db_manager.get_all_data('contact_method')
            self.contact_combo.clear()
            self.contact_combo.addItem('-- Выберите способ связи --', None)
            for row in data:
                self.contact_combo.addItem(row[1], row[0])
        except Exception as e:
            print(f"Ошибка загрузки данных формы: {e}")

    def add_to_cart(self):
        try:
            service_id = self.service_combo.currentData()
            quantity = self.quantity_spin.value()
            if not service_id:
                QMessageBox.warning(self, 'Ошибка', 'Выберите услугу')
                return
            query = "SELECT service_id, name, service_price FROM service WHERE service_id = %s"
            data, _ = self.db_manager.execute_query(query, (service_id,))
            if not data:
                QMessageBox.warning(self, 'Ошибка', 'Услуга не найдена')
                return
            service = data[0]
            service_price = float(service[2])
            total = service_price * quantity
            for i, item in enumerate(self.cart_items):
                if item['service_id'] == service_id:
                    self.cart_items[i]['quantity'] += quantity
                    self.cart_items[i]['total'] = self.cart_items[i]['quantity'] * service_price
                    self.update_cart_display()
                    self.quantity_spin.setValue(1)
                    return
            cart_item = {
                'service_id': service_id,
                'name': service[1],
                'price': service_price,
                'quantity': quantity,
                'total': total
            }
            self.cart_items.append(cart_item)
            self.update_cart_display()
            self.quantity_spin.setValue(1)
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Не удалось добавить в корзину:\n{str(e)}')

    def update_cart_display(self):
        self.cart_table.setRowCount(len(self.cart_items))
        total_sum = 0
        for row_idx, item in enumerate(self.cart_items):
            id_item = QTableWidgetItem(str(item['service_id']))
            self.cart_table.setItem(row_idx, 0, id_item)
            name_item = QTableWidgetItem(item['name'])
            self.cart_table.setItem(row_idx, 1, name_item)
            price_item = QTableWidgetItem(f"{item['price']:.2f}")
            self.cart_table.setItem(row_idx, 2, price_item)
            qty_item = QTableWidgetItem(str(item['quantity']))
            self.cart_table.setItem(row_idx, 3, qty_item)
            total_item = QTableWidgetItem(f"{item['total']:.2f}")
            self.cart_table.setItem(row_idx, 4, total_item)
            total_sum += item['total']
        self.total_label.setText(f"{total_sum:.2f} руб.")
        has_items = len(self.cart_items) > 0
        self.create_order_button.setEnabled(has_items)
        self.cart_table.resizeColumnsToContents()

    def remove_from_cart(self):
        selected_row = self.cart_table.currentRow()
        if selected_row >= 0 and selected_row < len(self.cart_items):
            del self.cart_items[selected_row]
            self.update_cart_display()

    def clear_cart(self):
        if self.cart_items:
            reply = QMessageBox.question(
                self, 'Подтверждение',
                'Вы уверены, что хотите очистить корзину?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.cart_items = []
                self.update_cart_display()

    def create_order(self):
        try:
            client_id = self.client_combo.currentData()
            payment_method_id = self.payment_combo.currentData()
            contact_method_id = self.contact_combo.currentData()

            if not client_id:
                QMessageBox.warning(self, 'Ошибка', 'Выберите клиента')
                return
            if not payment_method_id:
                QMessageBox.warning(self, 'Ошибка', 'Выберите способ оплаты')
                return
            if not contact_method_id:
                QMessageBox.warning(self, 'Ошибка', 'Выберите способ связи')
                return
            if not self.cart_items:
                QMessageBox.warning(self, 'Ошибка', 'Корзина пуста')
                return
            client_query = "SELECT surname, name, patronymic, phone, email FROM client WHERE client_id = %s"
            client_data, _ = self.db_manager.execute_query(client_query, (client_id,))
            payment_query = "SELECT name FROM payment_method WHERE payment_method_id = %s"
            payment_data, _ = self.db_manager.execute_query(payment_query, (payment_method_id,))
            contact_query = "SELECT name FROM contact_method WHERE contact_method_id = %s"
            contact_data, _ = self.db_manager.execute_query(contact_query, (contact_method_id,))
            if client_data and client_data[0]:
                surname, name, patronymic, phone, email = client_data[0]
                client_info_parts = []
                if surname:
                    client_info_parts.append(surname)
                if name:
                    client_info_parts.append(name)
                if patronymic:
                    client_info_parts.append(patronymic)
                client_info = " ".join(client_info_parts)
                contact_info = []
                if phone:
                    contact_info.append(f"тел: {phone}")
                if email:
                    contact_info.append(f"email: {email}")
                if contact_info:
                    client_info_for_receipt = f"{client_info} ({', '.join(contact_info)})"
                else:
                    client_info_for_receipt = client_info
            else:
                client_info = f"Клиент ID: {client_id}"
                client_info_for_receipt = client_info
            payment_method = payment_data[0][0] if payment_data and payment_data[0] else "Неизвестно"
            contact_method = contact_data[0][0] if contact_data and contact_data[0] else "Неизвестно"
            total_sum = sum(item['total'] for item in self.cart_items)
            query = """
                INSERT INTO orders (client_id, payment_method_id, contact_method_id, total_sum, date)
                VALUES (%s, %s, %s, %s, NOW())
                RETURNING order_id
            """
            order_result = self.db_manager.execute_query_with_return(query, (
            client_id, payment_method_id, contact_method_id, total_sum))
            if not order_result:
                raise Exception("Не удалось создать заказ")
            order_id = order_result[0]
            for item in self.cart_items:
                query = """
                    INSERT INTO order_info (order_id, service_id, quantity)
                    VALUES (%s, %s, %s)
                """
                self.db_manager.execute_query(query, (order_id, item['service_id'], item['quantity']))
            receipt_dialog = ReceiptDialog(
                order_id=order_id,
                client_info=client_info_for_receipt,
                payment_method=payment_method,
                contact_method=contact_method,
                cart_items=self.cart_items,
                total_sum=total_sum,
                parent=self
            )
            self.cart_items = []
            self.update_cart_display()
            self.client_combo.setCurrentIndex(0)
            self.payment_combo.setCurrentIndex(0)
            self.contact_combo.setCurrentIndex(0)
            receipt_dialog.exec()
            QMessageBox.information(self, 'Успех', f'Заказ #{order_id} создан успешно!')
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Не удалось создать заказ:\n{str(e)}')

    def generate_report(self):
        try:
            date_from = self.date_from.date().toString('yyyy-MM-dd')
            date_to = self.date_to.date().toString('yyyy-MM-dd')
            query = """
                SELECT 
                    o.order_id,
                    c.surname || ' ' || c.name as client,
                    s.name as service,
                    oi.quantity,
                    s.service_price,
                    (oi.quantity * s.service_price) as total,
                    pm.name as payment_method,
                    cm.name as contact_method,
                    o.date
                FROM orders o
                JOIN client c ON o.client_id = c.client_id
                JOIN order_info oi ON o.order_id = oi.order_id
                JOIN service s ON oi.service_id = s.service_id
                JOIN payment_method pm ON o.payment_method_id = pm.payment_method_id
                JOIN contact_method cm ON o.contact_method_id = cm.contact_method_id
                WHERE o.date::date BETWEEN %s AND %s
                ORDER BY o.date DESC
            """
            data, columns = self.db_manager.execute_query(query, (date_from, date_to))
            self.report_table.setRowCount(len(data))
            self.report_table.setColumnCount(len(columns))
            formatted_columns = []
            for col in columns:
                formatted = col.replace('_', ' ').title()
                formatted_columns.append(formatted)
            self.report_table.setHorizontalHeaderLabels(formatted_columns)
            total_sum = 0
            for row_idx, row in enumerate(data):
                for col_idx, value in enumerate(row):
                    item_text = ''
                    if value is not None:
                        if col_idx == 5:
                            item_text = f"{float(value):.2f}"
                            total_sum += float(value)
                        elif col_idx == 4:
                            item_text = f"{float(value):.2f}"
                        else:
                            item_text = str(value)
                    item = QTableWidgetItem(item_text)
                    self.report_table.setItem(row_idx, col_idx, item)
            self.report_table.resizeColumnsToContents()
            self.report_table.setRowCount(len(data) + 1)
            total_item = QTableWidgetItem(f'ИТОГО: {total_sum:.2f} руб.')
            total_item.setFont(QFont('Arial', 10, QFont.Weight.Bold))
            self.report_table.setItem(len(data), 5, total_item)
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Не удалось сгенерировать отчет:\n{str(e)}')

    def export_to_excel(self):
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, 'Экспорт в Excel', '', 'Excel Files (*.xlsx)'
            )
            if file_path:
                if not file_path.endswith('.xlsx'):
                    file_path += '.xlsx'
                data = []
                columns = []
                for col in range(self.report_table.columnCount()):
                    columns.append(self.report_table.horizontalHeaderItem(col).text())
                for row in range(self.report_table.rowCount()):
                    row_data = []
                    for col in range(self.report_table.columnCount()):
                        item = self.report_table.item(row, col)
                        row_data.append(item.text() if item else '')
                    data.append(row_data)
                df = pd.DataFrame(data, columns=columns)
                df.to_excel(file_path, index=False, engine='openpyxl')
                QMessageBox.information(self, 'Успех', f'Данные экспортированы в {file_path}')
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Не удалось экспортировать данные:\n{str(e)}')

    def export_to_csv(self):
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, 'Экспорт в CSV', '', 'CSV Files (*.csv)'
            )
            if file_path:
                if not file_path.endswith('.csv'):
                    file_path += '.csv'
                data = []
                columns = []
                for col in range(self.report_table.columnCount()):
                    columns.append(self.report_table.horizontalHeaderItem(col).text())
                for row in range(self.report_table.rowCount()):
                    row_data = []
                    for col in range(self.report_table.columnCount()):
                        item = self.report_table.item(row, col)
                        row_data.append(item.text() if item else '')
                    data.append(row_data)
                with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                    writer = csv.writer(csvfile, delimiter=';')
                    writer.writerow(columns)
                    writer.writerows(data)
                QMessageBox.information(self, 'Успех', f'Данные экспортированы в {file_path}')
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Не удалось экспортировать данные:\n{str(e)}')

    def add_user(self):
        username = self.new_username.text()
        password = self.new_password.text()
        role = self.new_role.currentText()
        name = self.new_name.text()
        if not all([username, password, role, name]):
            QMessageBox.warning(self, 'Ошибка', 'Заполните все поля')
            return
        try:
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            query = """
                INSERT INTO users (username, password_hash, role, name)
                VALUES (%s, %s, %s, %s)
            """
            self.db_manager.execute_query(query, (username, password_hash, role, name))
            QMessageBox.information(self, 'Успех', 'Пользователь добавлен')
            self.new_username.clear()
            self.new_password.clear()
            self.new_name.clear()
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Не удалось добавить пользователя:\n{str(e)}')

    def load_statistics(self):
        try:
            stats = []
            query = "SELECT COUNT(*) FROM orders"
            data, _ = self.db_manager.execute_query(query)
            stats.append(f"Всего заказов: {data[0][0]}")
            query = "SELECT SUM(total_sum) FROM orders"
            data, _ = self.db_manager.execute_query(query)
            total_revenue = data[0][0] or 0
            stats.append(f"Общая выручка: {float(total_revenue):.2f} руб.")
            query = """
                SELECT s.name, COUNT(*), SUM(oi.quantity * s.service_price)
                FROM order_info oi
                JOIN service s ON oi.service_id = s.service_id
                GROUP BY s.service_id, s.name
                ORDER BY SUM(oi.quantity * s.service_price) DESC
                LIMIT 10
            """
            data, _ = self.db_manager.execute_query(query)
            stats.append("\nТоп-10 услуг:")
            for row in data:
                service_name = row[0] if row[0] else "Без названия"
                order_count = row[1] if row[1] else 0
                revenue = float(row[2] or 0)
                stats.append(f"  {service_name}: {order_count} заказов, {revenue:.2f} руб.")
            query = """
                SELECT c.surname || ' ' || c.name, COUNT(*), SUM(o.total_sum)
                FROM orders o
                JOIN client c ON o.client_id = c.client_id
                GROUP BY c.client_id, c.surname, c.name
                ORDER BY SUM(o.total_sum) DESC
                LIMIT 10
            """
            data, _ = self.db_manager.execute_query(query)
            stats.append("\nТоп-10 клиентов:")
            for row in data:
                client_name = row[0] if row[0] else "Неизвестный клиент"
                order_count = row[1] if row[1] else 0
                revenue = float(row[2] or 0)
                stats.append(f"  {client_name}: {order_count} заказов, {revenue:.2f} руб.")
            self.stats_text.setText('\n'.join(stats))
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Не удалось загрузить статистику:\n{str(e)}')

    def create_backup(self):
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, 'Создать резервную копию', '', 'SQL Files (*.sql)'
            )
            if file_path:
                if not file_path.endswith('.sql'):
                    file_path += '.sql'
                with open(file_path, 'w', encoding='utf-8') as f:
                    cursor = self.db_manager.connection.cursor()
                    cursor.execute("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = 'public'
                    """)
                    tables = cursor.fetchall()
                    for table in tables:
                        table_name = table[0]
                        cursor.execute(
                            f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table_name}'")
                        columns = cursor.fetchall()
                        cursor.execute(f"SELECT * FROM {table_name}")
                        data = cursor.fetchall()
                        if data:
                            for row in data:
                                values = []
                                for val in row:
                                    if val is None:
                                        values.append('NULL')
                                    elif isinstance(val, str):
                                        values.append(f"'{val.replace("'", "''")}'")
                                    else:
                                        values.append(str(val))
                                insert_query = f"INSERT INTO {table_name} VALUES ({', '.join(values)});\n"
                                f.write(insert_query)
                    cursor.close()
                QMessageBox.information(self, 'Успех', f'Резервная копия создана: {file_path}')
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Не удалось создать резервную копию:\n{str(e)}')

    def refresh_data(self):
        if self.current_table:
            self.load_table_data(self.current_table)

    def show_about(self):
        QMessageBox.about(self, 'О программе',
                          'Система управления фотостудии\n'
                          'Для управления базой данных фотостудии\n'
                          'Поддерживаемые роли: владелец, администратор, работник, бухгалтер')


def main():
    app = QApplication(sys.argv)
    login_window = LoginWindow()
    if login_window.exec() == QDialog.DialogCode.Accepted:
        main_window = MainWindow(login_window.db_manager)
        main_window.show()
        sys.exit(app.exec())
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
