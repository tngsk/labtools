#!/usr/bin/env python3
"""VL53L0X Data Receiver - Simplified Version with Object Identification"""

import json
import time
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Button
from collections import deque
import threading
import queue
from enum import Enum
from statistics import mean, stdev
import signal
import sys
import atexit
import os

# Try to import serial module with better error handling
try:
    import serial
    HAS_SERIAL = True
    print("Serial module imported successfully")

    # Test if Serial class is available
    if not hasattr(serial, 'Serial'):
        print("Warning: serial.Serial class not found")
        print("This might be due to a conflict with another 'serial' module")
        print("Try: pip uninstall serial && pip install pyserial")
        HAS_SERIAL = False
    else:
        print(f"Serial class available, pyserial version: {getattr(serial, '__version__', 'unknown')}")

except ImportError as e:
    print(f"Failed to import serial module: {e}")
    print("Please install pyserial: pip install pyserial")
    HAS_SERIAL = False

try:
    import serial.tools.list_ports
    HAS_SERIAL_TOOLS = True
except ImportError:
    HAS_SERIAL_TOOLS = False


class OperationMode(Enum):
    NORMAL = "normal"
    OBJECT_IDENTIFICATION = "object_identification"


class CalibrationManager:
    """キャリブレーションデータの管理"""
    def __init__(self, config_file="object_calibration.json"):
        self.config_file = config_file
        self.calibration_data = {}
        self.load_calibration()

    def load_calibration(self):
        """キャリブレーションデータをJSONから読み込み"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    self.calibration_data = json.load(f)
                print(f"Calibration data loaded from {self.config_file}")
            else:
                print(f"No calibration file found. Using default values.")
                self.calibration_data = {}
        except Exception as e:
            print(f"Error loading calibration: {e}")
            self.calibration_data = {}

    def save_calibration(self):
        """キャリブレーションデータをJSONに保存"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.calibration_data, f, indent=2)
            print(f"Calibration data saved to {self.config_file}")
            return True
        except Exception as e:
            print(f"Error saving calibration: {e}")
            return False

    def add_object_measurement(self, object_name, distance, margin=2.0):
        """オブジェクトの測定値を追加（マージン付き）"""
        self.calibration_data[object_name] = {
            'min_distance': distance - margin,
            'max_distance': distance + margin,
            'center_distance': distance,
            'name': object_name
        }

    def get_objects_config(self):
        """オブジェクト設定辞書を取得"""
        return self.calibration_data


class ObjectDatabase:
    """オブジェクト識別のための基準データベース"""
    def __init__(self, debug_mode=False, calibration_manager=None):
        self.debug_mode = debug_mode
        self.calibration_manager = calibration_manager

        # キャリブレーションデータがある場合はそれを使用
        if calibration_manager and calibration_manager.calibration_data:
            self.objects = calibration_manager.get_objects_config()
            print("Using calibrated object ranges:")
            for obj_id, obj_data in self.objects.items():
                print(f"  {obj_data['name']}: {obj_data['min_distance']:.1f}-{obj_data['max_distance']:.1f}mm")
        elif debug_mode:
            # デバッグモード時は広い範囲
            self.objects = {
                'ObjectA': {'min_distance': 0, 'max_distance': 500, 'name': 'Object A (Debug)'},
                'ObjectB': {'min_distance': 500, 'max_distance': 1000, 'name': 'Object B (Debug)'},
                'ObjectC': {'min_distance': 1000, 'max_distance': 2000, 'name': 'Object C (Debug)'},
            }
        else:
            # デフォルト値
            self.objects = {
                'ObjectA': {'min_distance': 10.3, 'max_distance': 10.7, 'name': 'Object A'},
                'ObjectB': {'min_distance': 12.0, 'max_distance': 12.4, 'name': 'Object B'},
                'ObjectC': {'min_distance': 13.6, 'max_distance': 14.0, 'name': 'Object C'},
            }

    def identify_object(self, distance):
        """距離値からオブジェクトを識別"""
        if distance is None:
            return None, 0.0

        best_match = None
        best_confidence = 0.0

        for obj_id, obj_data in self.objects.items():
            min_dist = obj_data['min_distance']
            max_dist = obj_data['max_distance']

            if min_dist <= distance <= max_dist:
                # 範囲内の場合、中心からの距離で信頼度計算
                center = (min_dist + max_dist) / 2
                range_width = max_dist - min_dist
                confidence = 1.0 - abs(distance - center) / (range_width / 2)

                if confidence > best_confidence:
                    best_match = obj_data['name']
                    best_confidence = confidence

        return best_match, best_confidence

    def add_object(self, obj_id, name, min_distance, max_distance):
        """新しいオブジェクトを追加"""
        self.objects[obj_id] = {
            'min_distance': min_distance,
            'max_distance': max_distance,
            'name': name
        }


class DebugCalibrator:
    """デバッグモードでのキャリブレーション機能"""
    def __init__(self, calibration_manager, processor):
        self.calibration_manager = calibration_manager
        self.processor = processor
        self.measurement_buffer = []
        self.object_counter = 0
        self.object_names = ['ObjectA', 'ObjectB', 'ObjectC']
        self.calibration_active = True
        self.buttons = None

    def capture_current_state(self):
        """現在の測定値をキャプチャして自動保存"""
        latest = self.processor.latest_data
        valid_measurements = [d for d in latest if d is not None]

        if valid_measurements:
            avg_distance = sum(valid_measurements) / len(valid_measurements)

            if self.object_counter < len(self.object_names):
                object_name = self.object_names[self.object_counter]
                self.calibration_manager.add_object_measurement(object_name, avg_distance)
                print(f"\n*** Saved {object_name}: {avg_distance:.2f}mm ***")
                self.object_counter += 1

                if self.object_counter >= len(self.object_names):
                    # 全オブジェクト完了時に自動保存
                    if self.calibration_manager.save_calibration():
                        print("*** All objects calibrated and saved! You can now use normal identification mode. ***")
                        self.calibration_active = False
                    self.object_counter = 0  # リセット
                else:
                    next_obj = self.object_names[self.object_counter]
                    print(f"*** Next: Attach {next_obj} and press ENTER ***")
                return True
            else:
                print("*** All objects already calibrated. Press ENTER to restart calibration. ***")
                self.object_counter = 0
                return False
        else:
            print("*** No valid measurements available ***")
            return False

    def get_current_object_name(self):
        """現在キャリブレーション中のオブジェクト名を取得"""
        if self.object_counter < len(self.object_names):
            return self.object_names[self.object_counter]
        return "Completed"


class InstantIdentifier:
    """装着時の即座識別機能"""
    def __init__(self, database):
        self.database = database
        self.measurement_buffer = [deque(maxlen=10) for _ in range(3)]
        # デバッグモード時は安定化の閾値を緩める
        if database.debug_mode:
            self.stable_threshold = 50.0  # mm (デバッグ用)
        else:
            self.stable_threshold = 1.0  # mm (通常用、精度向上のため緩和)
        self.min_samples = 5  # サンプル数削減で応答性向上
        self.identification_results = [None, None, None]
        self.confidence_scores = [0.0, 0.0, 0.0]

    def add_measurement(self, channel, distance):
        """測定値を追加し、安定性をチェック"""
        if distance is not None:
            self.measurement_buffer[channel].append(distance)
            return self._check_stability(channel)
        return False

    def _check_stability(self, channel):
        """測定値の安定性をチェック"""
        buffer = self.measurement_buffer[channel]
        if len(buffer) < self.min_samples:
            return False

        recent_values = list(buffer)[-self.min_samples:]
        if len(recent_values) < self.min_samples:
            return False

        try:
            std_dev = stdev(recent_values)
            return std_dev < self.stable_threshold
        except:
            return False

    def get_stable_distance(self, channel):
        """安定した距離値を取得"""
        buffer = self.measurement_buffer[channel]
        if len(buffer) >= self.min_samples:
            recent_values = list(buffer)[-self.min_samples:]
            return mean(recent_values)
        return None

    def identify_channel(self, channel):
        """指定チャンネルのオブジェクト識別"""
        if self._check_stability(channel):
            stable_distance = self.get_stable_distance(channel)
            obj_name, confidence = self.database.identify_object(stable_distance)
            self.identification_results[channel] = obj_name
            self.confidence_scores[channel] = confidence
            return obj_name, confidence
        return None, 0.0

    def reset_channel(self, channel):
        """指定チャンネルのデータをリセット"""
        self.measurement_buffer[channel].clear()
        self.identification_results[channel] = None
        self.confidence_scores[channel] = 0.0


class SensorDataProcessor:
    def __init__(self, mode=OperationMode.NORMAL, debug_mode=False):
        self.channels = ['ch1', 'ch2', 'ch3']
        self.raw_data = [deque(maxlen=1000) for _ in range(3)]
        self.latest_data = [None, None, None]
        self.mode = mode
        self.debug_mode = debug_mode

        # キャリブレーション管理
        self.calibration_manager = CalibrationManager()

        # オブジェクト識別モード用
        if self.mode == OperationMode.OBJECT_IDENTIFICATION:
            self.object_db = ObjectDatabase(debug_mode, self.calibration_manager)
            if not debug_mode:
                self.identifier = InstantIdentifier(self.object_db)
            else:
                self.identifier = None  # デバッグモードでは使用しない
                self.debug_calibrator = DebugCalibrator(self.calibration_manager, self)

    def process_measurement(self, timestamp, measurements):
        for i in range(3):
            if i < len(measurements):
                distance, valid = measurements[i]
                if valid and distance is not None:
                    self.raw_data[i].append(distance)
                    self.latest_data[i] = distance

                    # オブジェクト識別モードの場合（デバッグモード以外）
                    if self.mode == OperationMode.OBJECT_IDENTIFICATION and hasattr(self, 'identifier') and self.identifier:
                        self.identifier.add_measurement(i, distance)
                else:
                    self.raw_data[i].append(None)

    def get_plot_data(self):
        return [list(data) for data in self.raw_data]

    def get_identification_results(self):
        """オブジェクト識別結果を取得"""
        if self.mode == OperationMode.OBJECT_IDENTIFICATION and hasattr(self, 'identifier') and self.identifier:
            results = []
            for i in range(3):
                obj_name, confidence = self.identifier.identify_channel(i)
                stable_distance = self.identifier.get_stable_distance(i)
                results.append({
                    'channel': self.channels[i],
                    'object': obj_name or self.identifier.identification_results[i],
                    'confidence': confidence or self.identifier.confidence_scores[i],
                    'distance': stable_distance,
                    'stable': self.identifier._check_stability(i)
                })
            return results
        return None

    def set_mode(self, mode):
        """動作モードを変更"""
        self.mode = mode
        if self.mode == OperationMode.OBJECT_IDENTIFICATION:
            self.object_db = ObjectDatabase(self.debug_mode, self.calibration_manager)
            if not self.debug_mode:
                self.identifier = InstantIdentifier(self.object_db)
            else:
                self.identifier = None
                self.debug_calibrator = DebugCalibrator(self.calibration_manager, self)


class VL53L0XReceiver:
    def __init__(self, port, baudrate=115200, mode=OperationMode.NORMAL, debug_mode=False):
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self.running = False
        self.data_queue = queue.Queue()
        self.processor = SensorDataProcessor(mode, debug_mode)
        self.read_thread = None
        self.mode = mode
        self.debug_mode = debug_mode

    def connect(self):
        if not HAS_SERIAL:
            print("Error: pyserial module not available")
            print("Please install it with: pip install pyserial")
            return False

        try:
            print(f"Attempting to connect to {self.port} at {self.baudrate} baud...")

            # Check if serial.Serial class is available
            if not hasattr(serial, 'Serial'):
                print("Error: serial.Serial class not found")
                print("This might be due to a module conflict. Try:")
                print("  pip uninstall serial")
                print("  pip install pyserial")
                return False

            self.serial = serial.Serial(self.port, self.baudrate, timeout=1)
            print(f"Successfully connected to {self.port}")
            time.sleep(2)
            return True

        except serial.SerialException as e:
            print(f"Serial connection error: {e}")
            print(f"Make sure {self.port} is available and not in use by another application")
            return False
        except FileNotFoundError:
            print(f"Error: Port {self.port} not found")
            print("Available ports:")
            available = get_available_ports()
            for port in available:
                print(f"  {port}")
            return False
        except PermissionError:
            print(f"Permission denied accessing {self.port}")
            print("Try running with sudo or check port permissions")
            return False
        except Exception as e:
            print(f"Unexpected connection error: {e}")
            print(f"Error type: {type(e).__name__}")
            return False

    def disconnect(self):
        self.running = False
        if self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=2)
        if self.serial and self.serial.is_open:
            try:
                self.serial.close()
                print(f"Serial port {self.port} closed successfully")
            except Exception as e:
                print(f"Error closing serial port: {e}")
        self.serial = None

    def parse_data(self, line):
        try:
            if line.startswith('{'):  # JSON
                brace_count = 0
                json_end = -1
                for i, char in enumerate(line):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i + 1
                            break

                if json_end > 0:
                    json_part = line[:json_end]
                    data = json.loads(json_part)
                else:
                    data = json.loads(line)

                if data.get('type') == 'measurement':
                    timestamp = data['timestamp']
                    channels = data.get('channels', [])
                    measurements = []

                    for i in range(3):
                        if i < len(channels) and channels[i] is not None:
                            dist = channels[i].get('distance')
                            valid = dist is not None
                            measurements.append((dist, valid))
                        else:
                            measurements.append((None, False))
                    return timestamp, measurements

            else:  # CSV
                if line.startswith('#'):
                    return None, None
                parts = line.strip().split(',')
                if len(parts) >= 5:
                    timestamp = int(parts[0])
                    measurements = []
                    for i in range(2, 5):  # ch1, ch2, ch3
                        if i < len(parts):
                            val_str = parts[i]
                            if val_str in ['N/A'] or val_str.startswith('E'):
                                measurements.append((None, False))
                            else:
                                try:
                                    val = int(val_str)
                                    measurements.append((val, True))
                                except ValueError:
                                    measurements.append((None, False))
                        else:
                            measurements.append((None, False))
                    return timestamp, measurements

        except Exception as e:
            print(f"Parse error: {e}")
        return None, None

    def read_data_thread(self):
        consecutive_errors = 0
        max_consecutive_errors = 10

        while self.running and self.serial and self.serial.is_open:
            try:
                if self.serial.in_waiting > 0:
                    line = self.serial.readline().decode('utf-8').strip()
                    if line:
                        timestamp, measurements = self.parse_data(line)
                        if timestamp is not None and measurements is not None:
                            self.data_queue.put((timestamp, measurements))
                        consecutive_errors = 0  # Reset error counter on successful read
                else:
                    time.sleep(0.001)
            except serial.SerialException as e:
                consecutive_errors += 1
                print(f"Serial error: {e} (attempt {consecutive_errors}/{max_consecutive_errors})")
                if consecutive_errors >= max_consecutive_errors:
                    print("Too many consecutive serial errors. Stopping read thread.")
                    self.running = False
                    break
                time.sleep(0.1)
            except UnicodeDecodeError as e:
                print(f"Unicode decode error: {e}")
                time.sleep(0.01)
            except Exception as e:
                consecutive_errors += 1
                print(f"Read error: {e} (attempt {consecutive_errors}/{max_consecutive_errors})")
                if consecutive_errors >= max_consecutive_errors:
                    print("Too many consecutive read errors. Stopping read thread.")
                    self.running = False
                    break
                time.sleep(0.01)

    def start_reading(self):
        if not self.serial or not self.serial.is_open:
            return False
        self.running = True
        self.read_thread = threading.Thread(target=self.read_data_thread)
        self.read_thread.daemon = True
        self.read_thread.start()
        return True

    def get_data(self):
        try:
            return self.data_queue.get_nowait()
        except queue.Empty:
            return None, None


class RealTimePlotter:
    def __init__(self, receiver):
        self.receiver = receiver

        # デバッグモードの場合はボタン用のスペースを確保
        if self.receiver.debug_mode:
            self.fig, (self.ax, self.button_ax) = plt.subplots(2, 1, figsize=(12, 10),
                                                               gridspec_kw={'height_ratios': [4, 1]})
            self.setup_calibration_buttons()
        else:
            self.fig, self.ax = plt.subplots(figsize=(12, 8))

        self.lines = []
        self.colors = ['red', 'green', 'blue']
        self.channels = ['ch1', 'ch2', 'ch3']

        for i, (channel, color) in enumerate(zip(self.channels, self.colors)):
            line, = self.ax.plot([], [], color=color, label=channel, linewidth=2)
            self.lines.append(line)

        self.ax.set_xlabel('Time (samples)')
        self.ax.set_ylabel('Distance (mm)')

        # モードに応じて表示を調整
        if self.receiver.mode == OperationMode.OBJECT_IDENTIFICATION:
            if self.receiver.debug_mode:
                self.ax.set_title('VL53L0X ToF Sensor Data - CALIBRATION MODE')
                self.ax.set_ylim(0, 2000)  # デバッグ時は広い範囲
                # キャリブレーション済みの境界線を表示
                if hasattr(self.receiver.processor, 'calibration_manager'):
                    cal_data = self.receiver.processor.calibration_manager.calibration_data
                    for obj_name, obj_data in cal_data.items():
                        center = obj_data.get('center_distance')
                        if center:
                            self.ax.axhline(y=center, color='orange', linestyle='-', alpha=0.7,
                                          label=f'{obj_name}: {center:.1f}mm')
            else:
                self.ax.set_title('VL53L0X ToF Sensor Data - Object Identification Mode')
                # キャリブレーションデータに基づいて表示範囲を調整
                if hasattr(self.receiver.processor, 'calibration_manager'):
                    cal_data = self.receiver.processor.calibration_manager.calibration_data
                    if cal_data:
                        distances = [obj['center_distance'] for obj in cal_data.values() if 'center_distance' in obj]
                        if distances:
                            min_dist = min(distances) - 10
                            max_dist = max(distances) + 10
                            self.ax.set_ylim(min_dist, max_dist)
                        # キャリブレーション済み境界線を表示
                        for obj_name, obj_data in cal_data.items():
                            min_d = obj_data.get('min_distance')
                            max_d = obj_data.get('max_distance')
                            if min_d and max_d:
                                self.ax.axhspan(min_d, max_d, alpha=0.2, label=f'{obj_name} range')
                    else:
                        self.ax.set_ylim(9, 16)  # デフォルト範囲
        else:
            self.ax.set_title('VL53L0X ToF Sensor Data - Real Time')
            self.ax.set_ylim(0, 1000)

        self.ax.legend()
        self.ax.grid(True, alpha=0.3)

    def setup_calibration_buttons(self):
        """キャリブレーション用ボタンの設定"""
        self.button_ax.axis('off')

        # ボタンの配置
        button_width = 0.15
        button_height = 0.3
        button_y = 0.35

        # ObjectA ボタン
        ax_btn_a = plt.axes([0.2, button_y, button_width, button_height])
        self.btn_object_a = Button(ax_btn_a, 'Save ObjectA')
        self.btn_object_a.on_clicked(self.on_object_a_clicked)

        # ObjectB ボタン
        ax_btn_b = plt.axes([0.425, button_y, button_width, button_height])
        self.btn_object_b = Button(ax_btn_b, 'Save ObjectB')
        self.btn_object_b.on_clicked(self.on_object_b_clicked)

        # ObjectC ボタン
        ax_btn_c = plt.axes([0.65, button_y, button_width, button_height])
        self.btn_object_c = Button(ax_btn_c, 'Save ObjectC')
        self.btn_object_c.on_clicked(self.on_object_c_clicked)

        # レシーバーのキャリブレーターにボタン参照を設定
        if hasattr(self.receiver.processor, 'debug_calibrator'):
            self.receiver.processor.debug_calibrator.buttons = {
                'A': self.btn_object_a,
                'B': self.btn_object_b,
                'C': self.btn_object_c
            }

    def on_object_a_clicked(self, event):
        """ObjectA ボタンクリック時の処理"""
        if hasattr(self.receiver.processor, 'debug_calibrator'):
            self.save_object_measurement('ObjectA', 0)

    def on_object_b_clicked(self, event):
        """ObjectB ボタンクリック時の処理"""
        if hasattr(self.receiver.processor, 'debug_calibrator'):
            self.save_object_measurement('ObjectB', 1)

    def on_object_c_clicked(self, event):
        """ObjectC ボタンクリック時の処理"""
        if hasattr(self.receiver.processor, 'debug_calibrator'):
            self.save_object_measurement('ObjectC', 2)

    def save_object_measurement(self, object_name, index):
        """オブジェクト測定値の保存"""
        calibrator = self.receiver.processor.debug_calibrator
        latest = self.receiver.processor.latest_data
        valid_measurements = [d for d in latest if d is not None]

        if valid_measurements:
            avg_distance = sum(valid_measurements) / len(valid_measurements)
            calibrator.calibration_manager.add_object_measurement(object_name, avg_distance)
            print(f"*** Saved {object_name}: {avg_distance:.2f}mm ***")

            # ボタンの色を変更して保存済みを示す
            if calibrator.buttons:
                button_keys = ['A', 'B', 'C']
                calibrator.buttons[button_keys[index]].color = 'lightgreen'

            # 全て保存されたかチェック
            saved_objects = len(calibrator.calibration_manager.calibration_data)
            if saved_objects >= 3:
                if calibrator.calibration_manager.save_calibration():
                    print("*** All objects calibrated and saved! You can now use normal identification mode. ***")
                    self.update_button_status("All objects saved!")
        else:
            print(f"*** No valid measurements for {object_name} ***")

    def update_button_status(self, message):
        """ボタンステータスの更新"""
        if hasattr(self, 'button_ax'):
            self.button_ax.clear()
            self.button_ax.axis('off')
            self.button_ax.text(0.5, 0.5, message, ha='center', va='center',
                               fontsize=14, weight='bold', color='green')

    def update_plot(self, frame):
        try:
            # Safety check for disconnected receiver
            if not self.receiver or not self.receiver.running or not self.receiver.serial or not self.receiver.serial.is_open:
                # Clear all lines if receiver is disconnected
                for line in self.lines:
                    line.set_data([], [])
                self.ax.set_title("VL53L0X ToF Sensor Data - DISCONNECTED", color='red')
                return self.lines

            plot_data = self.receiver.processor.get_plot_data()

            for i, (line, data) in enumerate(zip(self.lines, plot_data)):
                if data and len(data) > 0:
                    valid_data = [(j, val) for j, val in enumerate(data) if val is not None]
                    if valid_data:
                        x_vals, y_vals = zip(*valid_data)
                        line.set_data(x_vals, y_vals)
                    else:
                        line.set_data([], [])
                else:
                    line.set_data([], [])

            # x軸の範囲を調整
            valid_lengths = [len(data) for data in plot_data if data]
            if valid_lengths:
                max_len = max(valid_lengths)
                if max_len > 0:
                    self.ax.set_xlim(max(0, max_len - 200), max_len)

            # タイトルの更新（モードに応じて）
            if self.receiver.mode == OperationMode.OBJECT_IDENTIFICATION:
                self._update_identification_title()
            else:
                self._update_normal_title()

        except Exception as e:
            print(f"Plot update error: {e}")

        return self.lines

    def _update_normal_title(self):
        """通常モードのタイトル更新"""
        latest = self.receiver.processor.latest_data
        title = 'VL53L0X ToF Sensor Data - Real Time\n'
        for i, (channel, value) in enumerate(zip(self.channels, latest)):
            if value is not None:
                title += f'{channel}: {value:.1f}mm  '
            else:
                title += f'{channel}: N/A  '
        self.ax.set_title(title)

    def _update_identification_title(self):
        """オブジェクト識別モードのタイトル更新"""
        if self.receiver.debug_mode:
            # デバッグ（キャリブレーション）モードのタイトル
            title = 'CALIBRATION MODE - Attach objects and click buttons below to save measurements\n'

            # 現在の測定値表示
            latest = self.receiver.processor.latest_data
            for i, (channel, value) in enumerate(zip(self.channels, latest)):
                if value is not None:
                    title += f'{channel}: {value:.2f}mm  '
                else:
                    title += f'{channel}: N/A  '
        else:
            # 通常のオブジェクト識別モード
            results = self.receiver.processor.get_identification_results()
            latest = self.receiver.processor.latest_data
            title = 'VL53L0X ToF Sensor Data - Object Identification Mode\n'

            # 生データと安定化データの両方を表示
            for i, channel in enumerate(self.channels):
                raw_value = latest[i] if i < len(latest) else None

                if results and i < len(results):
                    result = results[i]
                    obj = result['object'] or 'Unknown'
                    confidence = result['confidence']
                    stable_distance = result['distance']
                    stable = result['stable']

                    status = "✓" if stable else "..."
                    if raw_value is not None:
                        title += f'{channel}: {raw_value:.2f}mm '
                        if stable_distance is not None:
                            title += f'[{obj}({confidence:.1f}){status}]  '
                        else:
                            title += '[Analyzing...]  '
                    else:
                        title += f'{channel}: N/A  '
                else:
                    if raw_value is not None:
                        title += f'{channel}: {raw_value:.2f}mm [Initializing...]  '
                    else:
                        title += f'{channel}: N/A  '

        self.ax.set_title(title)

    def start(self):
        ani = FuncAnimation(self.fig, self.update_plot, interval=50, blit=False, cache_frame_data=False)
        try:
            plt.show()
        except KeyboardInterrupt:
            print("Plot interrupted by user")
        finally:
            plt.close(self.fig)
        return ani


def get_available_ports():
    import subprocess
    import glob

    ports = []
    try:
        # Use glob to get /dev/cu.* ports (macOS)
        ports = glob.glob('/dev/cu.*')
        # Filter to keep only Arduino-compatible ports
        arduino_ports = []
        for port in ports:
            # Keep USB serial devices (common Arduino ports)
            if any(x in port.lower() for x in ['usbserial', 'usbmodem', 'wchusbserial']):
                arduino_ports.append(port)
            # Skip known non-Arduino ports
            elif any(x in port.lower() for x in ['bluetooth', 'debug-console', 'ysaudio', 'redmi']):
                continue
            # Keep other potentially Arduino ports but warn
            else:
                arduino_ports.append(port)
        ports = arduino_ports
    except Exception as e:
        print(f"Port detection error: {e}")
        # Fallback: try shell command
        try:
            result = subprocess.run('ls /dev/cu.* 2>/dev/null',
                                  shell=True,
                                  capture_output=True,
                                  text=True)
            if result.returncode == 0:
                all_ports = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
                ports = []
                for port in all_ports:
                    if any(x in port.lower() for x in ['usbserial', 'usbmodem', 'wchusbserial']):
                        ports.append(port)
                    elif not any(x in port.lower() for x in ['bluetooth', 'debug-console', 'ysaudio', 'redmi']):
                        ports.append(port)
        except:
            pass

    return sorted(ports)


def select_serial_port():
    print("=== Serial Port Selection ===")
    ports = get_available_ports()

    if not ports:
        print("No available serial ports detected.")
        print("Common Arduino ports: /dev/cu.usbserial-*, /dev/cu.usbmodem*")
        manual_port = input("Enter port manually: ").strip()
        if manual_port:
            return manual_port
        return None

    print("Available serial ports:")
    for i, port in enumerate(ports):
        port_name = port.split('/')[-1]  # Get just the device name
        print(f"  {i+1}. {port} ({port_name})")

    if len(ports) == 1:
        confirm = input(f"\nAuto-select {ports[0]}? (y/n, default=y): ").strip().lower()
        if confirm in ['', 'y', 'yes']:
            return ports[0]

    while True:
        try:
            choice = input(f"\nSelect port (1-{len(ports)}) or enter path manually: ").strip()
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(ports):
                    selected_port = ports[idx]
                    print(f"Selected: {selected_port}")
                    return selected_port
                else:
                    print(f"Invalid number. Please enter 1-{len(ports)}")
            elif choice:
                # Manual entry
                if choice.startswith('/dev/'):
                    return choice
                else:
                    # Add /dev/ prefix if missing
                    return f"/dev/{choice}"
            else:
                print("Please make a selection.")
        except KeyboardInterrupt:
            print("\nCancelled.")
            return None
        except Exception as e:
            print(f"Error: {e}. Try again.")


def select_operation_mode():
    """動作モードを選択"""
    print("\n=== Operation Mode Selection ===")
    print("1. Normal Mode (Standard plotting)")
    print("2. Object Identification Mode (10-15mm range identification)")
    print("3. Object Identification DEBUG Mode (Check actual sensor values)")

    while True:
        try:
            choice = input("Select mode (1-3): ").strip()
            if choice == "1":
                return OperationMode.NORMAL, False
            elif choice == "2":
                return OperationMode.OBJECT_IDENTIFICATION, False
            elif choice == "3":
                return OperationMode.OBJECT_IDENTIFICATION, True
            else:
                print("Invalid selection. Please choose 1, 2, or 3.")
        except KeyboardInterrupt:
            return None, None
        except:
            print("Invalid input. Please try again.")


def signal_handler(sig, frame):
    """シグナルハンドラ - Ctrl+C などでの終了処理"""
    print("\nReceived interrupt signal. Cleaning up...")
    cleanup_resources()

def cleanup_resources():
    """リソースをクリーンアップ"""
    global receiver
    try:
        if 'receiver' in globals() and receiver:
            receiver.disconnect()
        plt.close('all')
    except:
        pass

def main():
    global receiver
    receiver = None

    # シグナルハンドラの設定
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("VL53L0X Data Receiver - Enhanced Version")
    print("3 Channels (ch1, ch2, ch3) - Multiple Modes Available")

    # Check serial module availability
    if not HAS_SERIAL:
        print("\nERROR: pyserial module not available!")
        print("Please install it with one of the following commands:")
        print("  pip install pyserial")
        print("  pip3 install pyserial")
        print("  python -m pip install pyserial")
        return

    # 動作モード選択
    mode_result = select_operation_mode()
    if mode_result[0] is None:
        print("No mode selected. Exiting.")
        return

    mode, debug_mode = mode_result

    if mode == OperationMode.OBJECT_IDENTIFICATION:
        if debug_mode:
            print("\nObject Identification CALIBRATION Mode:")
            print("- Attach ObjectA and click 'Save ObjectA' button")
            print("- Attach ObjectB and click 'Save ObjectB' button")
            print("- Attach ObjectC and click 'Save ObjectC' button")
            print("- Configuration will be saved automatically")
            print("- Use the buttons in the plot window")
        else:
            print("\nObject Identification Mode:")
            print("- Default ranges will be used or loaded from calibration file")
            print("- Measurement will stabilize automatically")

    # シリアルポート選択
    port = select_serial_port()
    if not port:
        print("No port selected. Exiting.")
        return

    # レシーバー初期化
    try:
        receiver = VL53L0XReceiver(port, mode=mode, debug_mode=debug_mode)
        if not receiver.connect():
            print("\nConnection failed!")
            print("Troubleshooting tips:")
            print("1. Make sure the Arduino is connected and powered on")
            print("2. Check if another program is using the serial port")
            print("3. Try unplugging and reconnecting the USB cable")
            print("4. Verify the correct port is selected")
            print("Failed to connect. Exiting.")
            return
    except Exception as e:
        print(f"\nUnexpected error during initialization: {e}")
        print(f"Error type: {type(e).__name__}")
        return

    print(f"Connected to {port}")
    print(f"Mode: {mode.value}")
    if debug_mode:
        print("DEBUG MODE: Wide range detection enabled")

    # キャリブレーションデータの表示（レシーバー初期化後）
    if mode == OperationMode.OBJECT_IDENTIFICATION and not debug_mode:
        if hasattr(receiver.processor, 'calibration_manager') and receiver.processor.calibration_manager.calibration_data:
            print("Using calibrated ranges:")
            for obj_name, obj_data in receiver.processor.calibration_manager.calibration_data.items():
                print(f"- {obj_data['name']}: {obj_data['min_distance']:.1f}-{obj_data['max_distance']:.1f}mm")
        else:
            print("Using default ranges:")
            print("- ObjectA: 10.3-10.7mm (default)")
            print("- ObjectB: 12.0-12.4mm (default)")
            print("- ObjectC: 13.6-14.0mm (default)")

    # データ読み取り開始
    if not receiver.start_reading():
        print("Failed to start reading. Exiting.")
        receiver.disconnect()
        return

    if mode == OperationMode.OBJECT_IDENTIFICATION:
        if debug_mode:
            print("CALIBRATION MODE: Use buttons in the plot window...")
        else:
            print("Attach objects and wait for identification...")
    else:
        print("Reading data... Press Ctrl+C to stop")

    # データ処理スレッド
    def data_update():
        while receiver and receiver.running:
            try:
                timestamp, measurements = receiver.get_data()
                if timestamp is not None and measurements is not None:
                    receiver.processor.process_measurement(timestamp, measurements)
            except KeyboardInterrupt:
                break
            except Exception as e:
                if receiver and receiver.running:
                    print(f"Data update error: {e}")
                break
            time.sleep(0.001)

    # データ処理スレッド開始
    data_thread = threading.Thread(target=data_update)
    data_thread.daemon = True
    data_thread.start()

    # プロット開始
    try:
        plotter = RealTimePlotter(receiver)
        ani = plotter.start()
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received...")
    except Exception as e:
        print(f"\nError occurred: {e}")
    finally:
        print("\nStopping...")
        try:
            if receiver:
                receiver.disconnect()
                receiver = None
            plt.close('all')
            # スレッドの終了を少し待つ
            if 'data_thread' in locals() and data_thread.is_alive():
                data_thread.join(timeout=1)
        except:
            pass
        print("Disconnected and cleaned up.")


def auto_main(timeout_seconds=30):
    """Automated main function for non-interactive execution"""
    global receiver
    receiver = None

    # シグナルハンドラの設定
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print(f"VL53L0X Data Receiver - Auto Mode (timeout: {timeout_seconds}s)")

    # Check serial module availability
    if not HAS_SERIAL:
        print("\nERROR: pyserial module not available!")
        return

    # Auto-select first available port
    ports = get_available_ports()
    if not ports:
        print("No Arduino-compatible ports found")
        return

    port = ports[0]
    print(f"Auto-selected port: {port}")

    # Use normal mode by default
    mode = OperationMode.NORMAL
    debug_mode = False

    # レシーバー初期化
    try:
        receiver = VL53L0XReceiver(port, mode=mode, debug_mode=debug_mode)
        if not receiver.connect():
            print("Failed to connect. Exiting.")
            return
    except Exception as e:
        print(f"Error during initialization: {e}")
        return

    print(f"Connected to {port}")
    print(f"Mode: {mode.value}")

    try:
        receiver.start_reading()

        # Wait a bit for data to start flowing
        time.sleep(2)

        # Check if we're receiving data
        start_time = time.time()
        data_received = False

        print("Checking for data reception...")
        while time.time() - start_time < 5:  # Check for 5 seconds
            if not receiver.data_queue.empty():
                data_received = True
                print("✓ Data reception confirmed")
                break
            time.sleep(0.1)

        if not data_received:
            print("⚠ Warning: No data received from Arduino")
            print("Make sure Arduino is running and sending data")

        print(f"Running for {timeout_seconds} seconds...")

        # Run for specified timeout
        end_time = time.time() + timeout_seconds
        data_count = 0

        while time.time() < end_time and receiver.running:
            if not receiver.data_queue.empty():
                data = receiver.data_queue.get()
                data_count += 1
                if data_count % 10 == 0:  # Print every 10th measurement
                    print(f"Data points received: {data_count}")
            time.sleep(0.1)

        print(f"✓ Test completed. Total data points: {data_count}")

    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error during execution: {e}")
    finally:
        cleanup_resources()
        print("Disconnected and cleaned up.")


def test_serial_connection():
    """Test serial connection without GUI for debugging"""
    print("=== Serial Connection Test ===")

    if not HAS_SERIAL:
        print("ERROR: pyserial not available")
        return False

    # Get available ports
    ports = get_available_ports()
    if not ports:
        print("No Arduino-compatible ports found")
        return False

    port = ports[0]  # Use first available port
    print(f"Testing connection to: {port}")

    try:
        # Test basic serial connection
        ser = serial.Serial(port, 115200, timeout=1)
        print("✓ Serial port opened successfully")

        # Read a few lines to test communication
        print("Reading data for 5 seconds...")
        start_time = time.time()
        line_count = 0

        while time.time() - start_time < 5 and line_count < 10:
            try:
                line = ser.readline().decode('utf-8').strip()
                if line:
                    print(f"  Received: {line}")
                    line_count += 1
            except UnicodeDecodeError:
                print("  Received non-UTF8 data")
            except Exception as e:
                print(f"  Read error: {e}")

        ser.close()
        print("✓ Serial port closed successfully")

        if line_count > 0:
            print(f"✓ Successfully received {line_count} lines")
            return True
        else:
            print("⚠ No data received - check Arduino is running and sending data")
            return False

    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            test_serial_connection()
        elif sys.argv[1] == "auto":
            # Auto mode: use first available port, normal mode
            timeout = 30  # default timeout
            if len(sys.argv) > 2:
                try:
                    timeout = int(sys.argv[2])
                except ValueError:
                    print("Invalid timeout value. Using default 30 seconds.")
            auto_main(timeout)
        else:
            print("Usage:")
            print("  python receiver_python.py          # Interactive mode")
            print("  python receiver_python.py test     # Test serial connection")
            print("  python receiver_python.py auto [timeout]  # Auto mode with optional timeout")
    else:
        main()
