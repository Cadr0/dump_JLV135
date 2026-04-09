#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JLV135 Дамп анализатор - Мини-программа для анализа дампа контроллера
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import struct
import os
import sys
from typing import List, Tuple, Dict

class DumpAnalyzerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("JLV135 Анализ дампа от Марутина А.В.")
        self.root.geometry("1000x700")
        
        # Данные дампа
        self.dump_data = None
        self.dump_file_path = None
        
        # Эталонный дамп для сравнения
        self.reference_data = None
        self.reference_file_path = None
        
        # Известные области с идентификаторами (будут отличаться)
        self.identifier_regions = [
            (0xE000, 0xF000, "GUID область"),  # Уникальные идентификаторы
            (0x10000, 0x20000, "Область серийных номеров"),
            (0x20000, 0x30000, "Область даты производства"),
            (0x30000, 0x40000, "Область конфигурации"),
        ]
        
        self.setup_ui()
        
    def setup_ui(self):
        """Настройка пользовательского интерфейса"""
        # Главный фрейм
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Настройка растягивания
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Заголовок
        title_label = ttk.Label(main_frame, text="JLV135 Анализатор Дампа", 
                              font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Выбор файлов
        file_frame = ttk.Frame(main_frame)
        file_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(1, weight=1)
        file_frame.columnconfigure(3, weight=1)
        
        # Основной дамп
        ttk.Label(file_frame, text="Файл дампа:").grid(row=0, column=0, padx=(0, 10))
        
        self.file_path_var = tk.StringVar()
        self.file_entry = ttk.Entry(file_frame, textvariable=self.file_path_var, state="readonly")
        self.file_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        
        ttk.Button(file_frame, text="Выбрать файл", 
                  command=self.select_file).grid(row=0, column=2)
        
        # Эталонный дамп
        ttk.Label(file_frame, text="Эталонный дамп:").grid(row=1, column=0, padx=(0, 10), pady=(5, 0))
        
        self.reference_path_var = tk.StringVar()
        self.reference_entry = ttk.Entry(file_frame, textvariable=self.reference_path_var, state="readonly")
        self.reference_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(0, 10), pady=(5, 0))
        
        ttk.Button(file_frame, text="Выбрать эталон", 
                  command=self.select_reference).grid(row=1, column=2, pady=(5, 0))
        
        # Кнопки анализа
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Button(button_frame, text="Полный анализ", 
                  command=self.full_analysis).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Быстрый анализ", 
                  command=self.quick_analysis).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Анализ векторов", 
                  command=self.analyze_vectors).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Поиск сигнатур", 
                  command=self.find_signatures).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Флеш-память", 
                  command=self.analyze_flash_memory).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Поиск ошибок", 
                  command=self.detect_specific_errors).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Диагностика памяти", 
                  command=self.diagnose_memory).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Вывод дампа", 
                  command=self.dump_full_hex).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Очистить", 
                  command=self.clear_output).pack(side=tk.LEFT)
        
        # Область вывода
        output_frame = ttk.LabelFrame(main_frame, text="Результаты анализа", padding="5")
        output_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)
        
        self.output_text = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD, 
                                                    font=("Consolas", 9))
        self.output_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Статус бар
        self.status_var = tk.StringVar(value="Готов к работе")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, 
                              relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        
    def select_file(self):
        """Выбор файла дампа"""
        file_path = filedialog.askopenfilename(
            title="Выберите файл дампа",
            filetypes=[("Binary files", "*.bin"), ("All files", "*.*")]
        )
        
        if file_path:
            self.file_path_var.set(file_path)
            self.dump_file_path = file_path
            self.status_var.set(f"Выбран файл: {os.path.basename(file_path)}")
            
    def load_dump(self):
        """Загрузка дампа в память"""
        if not self.dump_file_path or not os.path.exists(self.dump_file_path):
            messagebox.showerror("Ошибка", "Файл дампа не выбран или не существует!")
            return False
            
        try:
            with open(self.dump_file_path, 'rb') as f:
                self.dump_data = f.read()
            
            file_size = len(self.dump_data)
            self.log(f"Загружен дамп размером: {file_size:,} байт ({file_size/1024/1024:.2f} MB)")
            return True
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить файл: {e}")
            return False
    
    def select_reference(self):
        """Выбор эталонного дампа"""
        file_path = filedialog.askopenfilename(
            title="Выберите эталонный дамп",
            filetypes=[("Binary files", "*.bin"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'rb') as f:
                    self.reference_data = f.read()
                self.reference_file_path = file_path
                self.reference_path_var.set(os.path.basename(file_path))
                self.log(f"Эталонный дамп загружен: {os.path.basename(file_path)}")
                self.log(f"Размер эталонного дампа: {len(self.reference_data):,} байт")
                self.status_var.set("Эталонный дамп загружен")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось загрузить эталонный дамп: {e}")
    
    def is_identifier_region(self, address):
        """Проверяет, находится ли адрес в области с идентификаторами"""
        for start, end, name in self.identifier_regions:
            if start <= address < end:
                return True, name
        return False, None
    
    def compare_with_reference(self, region_name="", start_addr=0, end_addr=None):
        """Сравнение текущего дампа с эталонным"""
        if self.reference_data is None:
            return False, "Эталонный дамп не загружен"
        
        if self.dump_data is None:
            return False, "Основной дамп не загружен"
        
        if len(self.dump_data) != len(self.reference_data):
            return False, f"Разные размеры дампов: {len(self.dump_data)} vs {len(self.reference_data)}"
        
        if end_addr is None:
            end_addr = len(self.dump_data)
        
        # Сравниваем указанную область
        region1 = self.dump_data[start_addr:end_addr]
        region2 = self.reference_data[start_addr:end_addr]
        
        if region1 == region2:
            return True, f"{region_name} идентичен эталонному"
        
        # Подсчитываем различия
        differences = sum(1 for a, b in zip(region1, region2) if a != b)
        total_bytes = len(region1)
        diff_percent = (differences / total_bytes) * 100
        
        # Проверяем, не является ли это областью с идентификаторами
        is_id_region, id_name = self.is_identifier_region(start_addr)
        
        if is_id_region:
            return True, f"{region_name} отличается от эталона ({diff_percent:.1f}% различий) - это нормально для {id_name}"
        else:
            return False, f"{region_name} отличается от эталона ({diff_percent:.1f}% различий) - возможна проблема"

    def show_reference_diff(self, start_addr: int, end_addr: int, max_items: int = 16):
        """Показать подробные различия между текущим дампом и эталоном в указанном диапазоне.

        Выводит:
        - Общее число отличающихся байт и процент
        - Первые max_items отличий с абсолютным адресом, байтами текущего и эталона
        """
        if self.reference_data is None or self.dump_data is None:
            return
        end_addr = min(end_addr, len(self.dump_data), len(self.reference_data))
        region1 = self.dump_data[start_addr:end_addr]
        region2 = self.reference_data[start_addr:end_addr]
        if not region1 or not region2:
            return

        total = len(region1)
        diff_indexes = [i for i in range(total) if region1[i] != region2[i]]
        if not diff_indexes:
            self.log("  [REF DETAIL] Байтовых различий не найдено в указанном диапазоне")
            return
        diff_percent = len(diff_indexes) / total * 100.0
        self.log(f"  [REF DETAIL] Отличается байт: {len(diff_indexes)} из {total} ({diff_percent:.2f}%)")
        self.log(f"  [REF DETAIL] Первые {min(max_items, len(diff_indexes))} отличий:")
        for i in diff_indexes[:max_items]:
            abs_addr = start_addr + i
            cur_b = region1[i]
            ref_b = region2[i]
            self.log(f"    @0x{abs_addr:08X}: cur=0x{cur_b:02X} ref=0x{ref_b:02X}")

    def compare_full_with_reference(self, block_size: int = 0x10000, max_items_per_block: int = 8):
        """Полное сравнение с эталоном по всему дампу, блоками по block_size.

        - Выводит суммарное число различий и долю блоков с отличиями
        - Для каждого отличающегося блока показывает [REF ERROR] и первые байтовые отличия
        """
        if self.reference_data is None or self.dump_data is None:
            return
        total_len = min(len(self.dump_data), len(self.reference_data))
        if total_len == 0:
            return
        self.log("\n--- Полное сравнение с эталоном (64KB блоки) ---")
        total_blocks = (total_len + block_size - 1) // block_size
        blocks_with_diff = 0
        total_byte_diffs = 0
        for start in range(0, total_len, block_size):
            end = min(start + block_size, total_len)
            cur = self.dump_data[start:end]
            ref = self.reference_data[start:end]
            if cur == ref:
                continue
            blocks_with_diff += 1
            # Подсчет отличий
            diff_idx = [i for i in range(len(cur)) if cur[i] != ref[i]]
            total_byte_diffs += len(diff_idx)
            self.log(f"[REF ERROR] Блок 0x{start:08X}-0x{end:08X}: отличается байт {len(diff_idx)}")
            # Показать первые отличия
            for i in diff_idx[:max_items_per_block]:
                abs_addr = start + i
                self.log(f"  @0x{abs_addr:08X}: cur=0x{cur[i]:02X} ref=0x{ref[i]:02X}")
        if blocks_with_diff == 0:
            self.log("[REF] Полное сравнение: отличий не найдено")
        else:
            percent_blocks = blocks_with_diff / total_blocks * 100.0
            self.log(f"Итог: блоков с отличиями: {blocks_with_diff}/{total_blocks} ({percent_blocks:.2f}%), байтовых отличий: {total_byte_diffs}")
    
    def log(self, message):
        """Добавление сообщения в область вывода"""
        self.output_text.insert(tk.END, message + "\n")
        self.output_text.see(tk.END)
        self.root.update_idletasks()
        
    def clear_output(self):
        """Очистка области вывода"""
        self.output_text.delete(1.0, tk.END)
        self.status_var.set("Готов к работе")
        
    def quick_analysis(self):
        """Быстрый анализ дампа"""
        if not self.load_dump():
            return
            
        self.log("="*60)
        self.log("БЫСТРЫЙ АНАЛИЗ ДАМПА")
        self.log("="*60)
        
        # Размер файла
        file_size = len(self.dump_data)
        expected_size = 0x4000000  # 64MB
        
        self.log(f"Размер дампа: {file_size:,} байт ({file_size/1024/1024:.2f} MB)")
        
        if file_size == expected_size:
            self.log("[OK] Размер дампа корректен")
        else:
            self.log(f"[Ошибка] Неожиданный размер (ожидалось {expected_size:,} байт)")
        
        # Анализ векторов прерываний
        self.log("\n--- Векторы прерываний ---")
        vectors = struct.unpack('<16I', self.dump_data[:64])
        
        vector_names = [
            "Stack Pointer", "Reset Handler", "NMI Handler", "Hard Fault",
            "Mem Mgmt Fault", "Bus Fault", "Usage Fault", "Reserved",
            "Reserved", "Reserved", "Reserved", "SVCall Handler",
            "Debug Monitor", "Reserved", "PendSV Handler", "SysTick Handler"
        ]
        
        for i, (vector, name) in enumerate(zip(vectors, vector_names)):
            if vector != 0xFFFFFFFF and vector != 0x00000000:
                self.log(f"  {i:2d}. {name:15s}: 0x{vector:08X}")
        
        # Проверка Stack Pointer
        sp_value = vectors[0]
        if sp_value == 0xFFFFFFFF:
            self.log("\n[Критическая ошибка] Stack Pointer = 0xFFFFFFFF - критическая ошибка!")
        elif sp_value == 0x00000000:
            self.log("\n[Критическая ошибка] Stack Pointer = 0x00000000 - критическая ошибка!")
        else:
            self.log(f"\n[OK] Stack Pointer выглядит нормально: 0x{sp_value:08X}")
        
        # Анализ критических областей
        self.log("\n--- Критические области ---")
        regions = [
            (0x0000, 0x1000, "Загрузочный сектор"),
            (0x1000, 0x2000, "Начало прошивки"),
            (0xE000, 0xF000, "GUID область"),
        ]
        
        for start, end, name in regions:
            if start < file_size and end <= file_size:
                region = self.dump_data[start:end]
                ff_count = region.count(b'\xFF')
                zero_count = region.count(b'\x00')
                total = len(region)
                
                ff_percent = ff_count / total * 100
                zero_percent = zero_count / total * 100
                
                self.log(f"\n{name}:")
                self.log(f"  0xFF: {ff_percent:.1f}% | 0x00: {zero_percent:.1f}%")
                
                # Сравнение с эталонным
                if self.reference_data:
                    is_ok, ref_msg = self.compare_with_reference(name, start, end)
                    if is_ok:
                        self.log(f"  [REF] {ref_msg}")
                    else:
                        self.log(f"  [REF ERROR] {ref_msg}")
                        # Детальная разница по байтам
                        self.show_reference_diff(start, end)
                
                if ff_percent > 95:
                    self.log(f"  [Ошибка] Область не записана")
                elif zero_percent > 95:
                    self.log(f"  [Ошибка] Область повреждена")
                else:
                    self.log(f"  [OK] Область выглядит нормально")
        
        self.status_var.set("Быстрый анализ завершен")
        
    def analyze_vectors(self):
        """Детальный анализ векторов прерываний"""
        if not self.load_dump():
            return
            
        self.log("="*60)
        self.log("АНАЛИЗ ВЕКТОРОВ ПРЕРЫВАНИЙ")
        self.log("="*60)
        
        vectors = struct.unpack('<16I', self.dump_data[:64])
        
        self.log("Детальная информация о векторах:")
        self.log("-" * 40)
        
        for i, vector in enumerate(vectors):
            if vector != 0xFFFFFFFF and vector != 0x00000000:
                # Проверяем, указывает ли вектор на валидный код
                if 0x60000000 <= vector <= 0x60040000:
                    offset = vector - 0x60000000
                    if offset < len(self.dump_data):
                        handler_bytes = self.dump_data[offset:offset+4]
                        self.log(f"Вектор {i:2d}: 0x{vector:08X} -> Код: {handler_bytes.hex()}")
                    else:
                        self.log(f"Вектор {i:2d}: 0x{vector:08X} -> Вне диапазона дампа")
                else:
                    self.log(f"Вектор {i:2d}: 0x{vector:08X} -> Вне флеш-памяти")
        
        self.status_var.set("Анализ векторов завершен")
        
    def find_signatures(self):
        """Поиск сигнатур в дампе"""
        if not self.load_dump():
            return
            
        self.log("="*60)
        self.log("ПОИСК СИГНАТУР")
        self.log("="*60)
        
        signatures = [
            (b'ARM', "ARM архитектура"),
            (b'Cortex', "ARM Cortex"),
            (b'Freescale', "Freescale/NXP"),
            (b'NXP', "NXP Semiconductors"),
            (b'Kinetis', "Kinetis микроконтроллер"),
            (b'LPC', "LPC микроконтроллер"),
            (b'STM32', "STM32 микроконтроллер"),
            (b'JLV', "JLV специфичная сигнатура"),
            # Расширенные сигнатуры для диагностики
            (b'MK', "Kinetis MK серия"),
            (b'MKL', "Kinetis MKL серия"),
            (b'LPC43', "LPC43xx серия"),
            (b'LPC17', "LPC17xx серия"),
            (b'LPC11', "LPC11xx серия"),
            (b'Cortex-M0', "Cortex-M0 ядро"),
            (b'Cortex-M3', "Cortex-M3 ядро"),
            (b'Cortex-M4', "Cortex-M4 ядро"),
            (b'Cortex-M7', "Cortex-M7 ядро"),
            (b'bootloader', "Загрузчик"),
            (b'firmware', "Прошивка"),
            (b'config', "Конфигурация"),
            (b'settings', "Настройки"),
        ]
        
        for sig, desc in signatures:
            positions = []
            start = 0
            while True:
                pos = self.dump_data.find(sig, start)
                if pos == -1:
                    break
                positions.append(pos)
                start = pos + 1
            
            if positions:
                self.log(f"\nНайдена сигнатура '{sig.decode('ascii', errors='ignore')}' ({desc}):")
                for pos in positions[:5]:  # Показываем только первые 5
                    self.log(f"  Позиция: 0x{pos:08X}")
                if len(positions) > 5:
                    self.log(f"  ... и еще {len(positions) - 5} вхождений")
        
        self.status_var.set("Поиск сигнатур завершен")
    
    def analyze_flash_memory(self):
        """Анализ флеш-памяти и процессора"""
        if not self.load_dump():
            return
            
        self.log("="*60)
        self.log("АНАЛИЗ ФЛЕШ-ПАМЯТИ И ПРОЦЕССОРА")
        self.log("="*60)
        
        # Анализ структуры флеш-памяти
        self.log("\n--- Структура флеш-памяти ---")
        
        # Определяем размеры секторов (типичные для ARM Cortex-M)
        sector_sizes = [
            (0x0000, 0x1000, "Сектор 0 (4KB) - Векторы прерываний"),
            (0x1000, 0x2000, "Сектор 1 (4KB) - Начало прошивки"),
            (0x2000, 0x3000, "Сектор 2 (4KB) - Продолжение прошивки"),
            (0x3000, 0x4000, "Сектор 3 (4KB) - Продолжение прошивки"),
            (0x4000, 0x8000, "Сектор 4 (16KB) - Основная прошивка"),
            (0x8000, 0xC000, "Сектор 5 (16KB) - Основная прошивка"),
            (0xC000, 0xE000, "Сектор 6 (8KB) - Данные"),
            (0xE000, 0xF000, "Сектор 7 (4KB) - GUID/Конфигурация"),
        ]
        
        for start, end, desc in sector_sizes:
            if start < len(self.dump_data) and end <= len(self.dump_data):
                sector = self.dump_data[start:end]
                
                # Анализ содержимого сектора
                ff_count = sector.count(b'\xFF')
                zero_count = sector.count(b'\x00')
                total = len(sector)
                
                ff_percent = ff_count / total * 100
                zero_percent = zero_count / total * 100
                data_percent = 100 - ff_percent - zero_percent
                
                self.log(f"\n{desc}:")
                self.log(f"  0xFF: {ff_percent:.1f}% | 0x00: {zero_percent:.1f}% | Данные: {data_percent:.1f}%")
                
                # Сравнение с эталонным
                if self.reference_data:
                    is_ok, ref_msg = self.compare_with_reference(desc, start, end)
                    if is_ok:
                        self.log(f"  [REF] {ref_msg}")
                    else:
                        self.log(f"  [REF ERROR] {ref_msg}")
                        # Детальная разница по байтам в секторе
                        self.show_reference_diff(start, end)
                
                # Определяем состояние сектора
                if ff_percent > 95:
                    self.log(f"  [EMPTY] Сектор не записан")
                elif zero_percent > 95:
                    self.log(f"  [CORRUPTED] Сектор поврежден")
                elif data_percent > 50:
                    self.log(f"  [DATA] Сектор содержит данные")
                else:
                    self.log(f"  [PARTIAL] Сектор частично записан")
        
        # Анализ процессора по сигнатурам
        self.log("\n--- Определение процессора ---")
        
        processor_signatures = {
            b'MK': "Kinetis K серия",
            b'MKL': "Kinetis L серия", 
            b'LPC43': "LPC43xx серия",
            b'LPC17': "LPC17xx серия",
            b'LPC11': "LPC11xx серия",
            b'Cortex-M0': "Cortex-M0 ядро",
            b'Cortex-M3': "Cortex-M3 ядро", 
            b'Cortex-M4': "Cortex-M4 ядро",
            b'Cortex-M7': "Cortex-M7 ядро",
        }
        
        found_processors = []
        for sig, desc in processor_signatures.items():
            if sig in self.dump_data:
                found_processors.append(desc)
                pos = self.dump_data.find(sig)
                self.log(f"Найден {desc} по адресу 0x{pos:08X}")
        
        if found_processors:
            self.log(f"\n[Информация] Определен процессор: {', '.join(found_processors)}")
        else:
            self.log(f"\n[Ошибка] Не удалось точно определить процессор")
        
        self.status_var.set("Анализ флеш-памяти завершен")
    
    def diagnose_memory(self):
        """Диагностика подсистем памяти: QSPI NOR (MX25L51245G) и SDRAM (AS4C16M16SA)."""
        if not self.load_dump():
            return
        
        self.log("="*60)
        self.log("ДИАГНОСТИКА ПАМЯТИ")
        self.log("="*60)
        
        file_size = len(self.dump_data)
        self.log(f"Размер дампа: {file_size:,} байт")
        
        # 1) QSPI NOR Flash (Macronix MX25L51245G): проверка стирания/заполнения, равномерности
        self.log("\n— QSPI NOR Flash (MX25L51245G) —")
        sample_regions = [
            (0x0000, 0x10000, "Начало флеш (64KB)"),
            (0x100000, 0x110000, "Середина флеш (64KB)"),
            (0x3FF0000, 0x4000000, "Конец флеш (64KB)")
        ]
        for start, end, name in sample_regions:
            if end <= file_size:
                region = self.dump_data[start:end]
                ff = region.count(b'\xFF') / len(region) * 100
                zero = region.count(b'\x00') / len(region) * 100
                self.log(f"{name}: 0x{start:08X}-0x{end:08X} | 0xFF={ff:.1f}% 0x00={zero:.1f}%")
                if ff > 98.0:
                    self.log("  [INFO] Похоже на стертый участок — ок для пустых областей")
                if zero > 90.0:
                    self.log("  [WARN] Много 0x00 — возможна проблема записи/залипания линий")
        
        # Поиск повторяющихся шаблонов (типичный симптом сбоев питания/линий)
        self.log("\nПроверка повторяющихся шаблонов (1KB окна):")
        repeated = 0
        for i in range(0, min(file_size, 2*1024*1024), 1024):  # проверим первые 2MB для скорости
            blk = self.dump_data[i:i+1024]
            if len(set(blk)) <= 2:
                repeated += 1
        if repeated > 200:
            self.log(f"[WARN] Много однообразных блоков: {repeated} на первых 2MB")
        else:
            self.log(f"[OK] Однообразных блоков немного: {repeated}")
        
        # 2) SDRAM (AS4C16M16SA): прямого дампа нет, но можно косвенно судить по признакам
        self.log("\n— SDRAM (AS4C16M16SA) —")
        self.log("SDRAM не попадает в этот дамп (это QSPI флеш). Косвенные признаки:")
        self.log("- Много 0x00 в коде/данных при том, что должны быть данные — возможен сбой чтения из SDRAM")
        self.log("- Случайные рассыпанные байтовые ошибки — возможна нестабильность частоты/питания SDRAM")
        
        # Грубая эвристика: поиск участков, где ожидались бы данные (после 0x1000), но 0xFF/0x00 доминируют
        firmware_region = self.dump_data[0x1000:0x1000+0x20000] if file_size > 0x1000+0x20000 else self.dump_data[0x1000:]
        if firmware_region:
            ff = firmware_region.count(b'\xFF')/len(firmware_region)*100
            zero = firmware_region.count(b'\x00')/len(firmware_region)*100
            self.log(f"Прошивка (0x1000..): 0xFF={ff:.1f}% 0x00={zero:.1f}%")
            if ff > 95.0:
                self.log("[WARN] Большая часть прошивки стёрта — проверьте процесс прошивки/соединение QSPI")
            if zero > 80.0:
                self.log("[WARN] Много 0x00 в прошивке — подозрение на сбой чтения/инициализации периферии")
        
        self.status_var.set("Диагностика памяти завершена")
    
    def dump_full_hex(self):
        """Вывести в окно весь дамп в виде адрес: hex ... ascii (странично, для больших файлов ограничим)."""
        if not self.load_dump():
            return
        data = self.dump_data
        self.log("="*60)
        self.log("ПОЛНЫЙ ВЫВОД ДАМПА (HEX)")
        self.log("="*60)
        
        # Безопасный лимит вывода (например, первые 70MB), чтобы не заморозить GUI (70 очень много может лагать)
        max_bytes = min(len(data), 70*1024*1024)
        line_width = 16
        for offset in range(0, max_bytes, line_width):
            chunk = data[offset:offset+line_width]
            hex_part = ' '.join(f"{b:02X}" for b in chunk)
            ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
            self.log(f"0x{offset:08X}: {hex_part:<48}  {ascii_part}")
        if len(data) > max_bytes:
            self.log(f"... (Выведено первые {max_bytes//1024} KB из {len(data)//1024} KB)")
        self.status_var.set("Вывод дампа завершен")
    
    def detect_specific_errors(self):
        """Поиск конкретных ошибок"""
        if not self.load_dump():
            return
            
        self.log("="*60)
        self.log("ПОИСК КОНКРЕТНЫХ ОШИБОК")
        self.log("="*60)
        
        errors_found = []
        
        # Проверка векторов прерываний
        vectors = struct.unpack('<16I', self.dump_data[:64])
        
        self.log("\n--- Проверка векторов прерываний ---")
        
        # Stack Pointer проверки
        sp_value = vectors[0]
        if sp_value == 0xFFFFFFFF:
            errors_found.append("Критическая ошибка: Stack Pointer = 0xFFFFFFFF")
            self.log("[Критическая ошибка] Stack Pointer содержит 0xFFFFFFFF - контроллер не запустится!")
        elif sp_value == 0x00000000:
            errors_found.append("CRITICAL: Stack Pointer = 0x00000000")
            self.log("[Критическая ошибка] Stack Pointer равен нулю - критическая ошибка!")
        elif sp_value < 0x20000000 or sp_value > 0x20020000:
            # Проверяем, не является ли это специфичным для данного контроллера
            if sp_value == 0x42464346:  # Известный рабочий Stack Pointer
                self.log(f"[OK] Stack Pointer 0x{sp_value:08X} - известный рабочий адрес")
            else:
                errors_found.append("Ошибка: Stack Pointer вне диапазона RAM")
                self.log(f"[Ошибка] Stack Pointer 0x{sp_value:08X} может быть вне диапазона RAM")
        else:
            self.log(f"[OK] Stack Pointer 0x{sp_value:08X} выглядит нормально")
        
        # Reset Handler проверки
        reset_handler = vectors[1]
        if reset_handler == 0xFFFFFFFF:
            errors_found.append("Критическая ошибка: Reset Handler = 0xFFFFFFFF")
            self.log("[Критическая ошибка] Reset Handler содержит 0xFFFFFFFF - нет точки входа!")
        elif reset_handler == 0x00000000:
            errors_found.append("Критическая ошибка: Reset Handler = 0x00000000")
            self.log("[Критическая ошибка] Reset Handler равен нулю - критическая ошибка!")
        elif not (0x60000000 <= reset_handler <= 0x60040000):
            # Проверяем, не является ли это специфичным для данного контроллера
            if reset_handler == 0x56010400:  # Известный рабочий Reset Handler
                self.log(f"[OK] Reset Handler 0x{reset_handler:08X} - известный рабочий адрес")
            else:
                errors_found.append("Ошибка: Reset Handler вне флеш-памяти")
                self.log(f"[Ошибка] Reset Handler 0x{reset_handler:08X} вне диапазона флеш-памяти")
        else:
            self.log(f"[OK] Reset Handler 0x{reset_handler:08X} указывает на флеш-память")
        
        # Сравнение с эталоном по таблице векторов
        if self.reference_data is not None:
            is_ok_v, ref_v = self.compare_with_reference("Vector Table", 0x0000, 0x0040)
            if not is_ok_v:
                self.log(f"[REF ERROR] {ref_v}")
                self.show_reference_diff(0x0000, 0x0040)

        # Проверка на повреждение загрузочного сектора
        self.log("\n--- Проверка загрузочного сектора ---")
        
        boot_sector = self.dump_data[:0x1000]
        corruption_patterns = [
            (b'\xFF' * 16, "Блок из 0xFF"),
            (b'\x00' * 16, "Блок из 0x00"),
            (b'\xAA' * 16, "Блок из 0xAA"),
            (b'\x55' * 16, "Блок из 0x55"),
        ]
        
        for pattern, desc in corruption_patterns:
            count = boot_sector.count(pattern)
            # Если заголовок совпадает с эталоном, не считаем это ошибкой
            if self.reference_data is not None and boot_sector == self.reference_data[:0x1000]:
                continue
            # Порог делаем адекватным для больших областей: более 256 повторов 16-байтовых блоков
            if count > 256:
                errors_found.append(f"Ошибка: Много {desc} в загрузочном секторе")
                self.log(f"[Ошибка] Найдено {count} блоков {desc} в загрузочном секторе")
        
        # Проверка целостности прошивки
        self.log("\n--- Проверка целостности прошивки ---")
        
        firmware_start = 0x1000
        firmware_size = 0x30000  # Предполагаемый размер прошивки
        
        if firmware_start + firmware_size < len(self.dump_data):
            firmware_data = self.dump_data[firmware_start:firmware_start + firmware_size]
            
            # Проверка на пустые области в прошивке
            empty_blocks = 0
            for i in range(0, len(firmware_data) - 1024, 1024):
                block = firmware_data[i:i+1024]
                if block.count(b'\xFF') > 900:  # Более 90% 0xFF
                    empty_blocks += 1
            
            if empty_blocks > 10:
                # Если эталон совпадает по этой области, не трактуем как ошибку
                if not (self.reference_data is not None and 
                        self.dump_data[firmware_start:firmware_start + firmware_size] == 
                        self.reference_data[firmware_start:firmware_start + firmware_size]):
                    errors_found.append("Ошибка: Много пустых блоков в прошивке")
                    self.log(f"[Ошибка] Найдено {empty_blocks} пустых блоков в прошивке")

            # Сравнение с эталоном начала прошивки
            if self.reference_data is not None:
                is_ok_fw, ref_fw = self.compare_with_reference("Прошивка (0x1000..)", firmware_start, firmware_start + firmware_size)
                if not is_ok_fw:
                    self.log(f"[REF ERROR] {ref_fw}")
                    self.show_reference_diff(firmware_start, firmware_start + min(firmware_size, 0x1000))
        
        # Итоговый отчет
        self.log("\n" + "="*40)
        self.log("ИТОГОВЫЙ ОТЧЕТ ОБ ОШИБКАХ")
        self.log("="*40)
        
        if errors_found:
            self.log(f"Найдено ошибок: {len(errors_found)}")
            for i, error in enumerate(errors_found, 1):
                self.log(f"{i}. {error}")
        else:
            self.log("[OK] Критических ошибок не найдено")
        
        self.status_var.set("Поиск ошибок завершен")
    
    # compare_dumps удален по требованию пользователя
        
    def full_analysis(self):
        """Полный анализ дампа"""
        if not self.load_dump():
            return
            
        self.log("="*60)
        self.log("ПОЛНЫЙ АНАЛИЗ ДАМПА JLV135")
        self.log("="*60)
        
        # Выполняем все виды анализа
        self.quick_analysis()
        self.log("\n" + "="*60)
        self.find_signatures()
        self.log("\n" + "="*60)
        self.analyze_flash_memory()
        self.log("\n" + "="*60)
        self.detect_specific_errors()
        self.log("\n" + "="*60)
        # Если есть эталон — запустим полное блочное сравнение
        if self.reference_data is not None:
            self.compare_full_with_reference(block_size=0x10000, max_items_per_block=8)
        
        # Дополнительный анализ
        self.log("ДОПОЛНИТЕЛЬНЫЙ АНАЛИЗ")
        self.log("-" * 30)
        
        # Поиск повреждений (эвристика). Если загружен эталон и области совпадают — не считаем.
        self.log("\nПоиск поврежденных областей:")
        corruption_count = 0
        
        for i in range(0, len(self.dump_data) - 1024, 1024):
            chunk = self.dump_data[i:i+1024]
            if len(set(chunk)) <= 2:
                # Если есть эталон и этот блок идентичен эталонному — пропускаем как валидный
                if self.reference_data is not None and self.reference_data[i:i+1024] == chunk:
                    continue
                corruption_count += 1
        
        self.log(f"Найдено {corruption_count} подозрительных областей")
        
        if corruption_count > 10000:
            self.log("[Ошибка] Много подозрительных областей - возможны повреждения")
        elif corruption_count > 1000:
            self.log("[Информация] Умеренное количество подозрительных областей")
        else:
            self.log("[OK] Мало подозрительных областей")
        
        # Рекомендации
        self.log("\n" + "="*60)
        self.log("РЕКОМЕНДАЦИИ:")
        self.log("="*60)
        
        vectors = struct.unpack('<16I', self.dump_data[:64])
        sp_value = vectors[0]
        
        if sp_value == 0xFFFFFFFF:
            self.log("[Критическая ошибка] Основная проблема: невалидный Stack Pointer")
            self.log("Рекомендации:")
            self.log("1. Попробовать полную перепрошивку: flash, format, format_all")
            self.log("2. Проверить стабильность питания при прошивке")
            self.log("3. Убедиться в качестве USB кабеля")
        else:
            self.log("[Информация] Stack Pointer валиден")
            self.log("Рекомендации:")
            self.log("1. Попробовать перепрошивку: flash, format, format_default")
            self.log("2. Проверить целостность файла jlv135.img")
            self.log("3. Убедиться в правильности подключения")
        
        self.status_var.set("Полный анализ завершен")

def main():
    # Настройка кодировки для Windows (только если есть консоль)
    if sys.platform == "win32" and sys.stdout is not None:
        try:
            import codecs
            sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
        except (AttributeError, OSError):
            # Игнорируем ошибки если нет консоли (например, в exe файле)
            pass
    
    root = tk.Tk()
    app = DumpAnalyzerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()