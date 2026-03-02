# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import unittest
from unittest.mock import MagicMock, patch
from src.worker import TranscriberThread, SearchThread, ChatThread
import os

class TestTranscriberThread(unittest.TestCase):
    @patch('src.worker.WhisperModel')
    @patch('os.path.getsize')
    def test_transcription(self, mock_getsize, MockWhisper):
        # Setup Mock
        mock_getsize.return_value = 1024
        mock_model = MockWhisper.return_value
        Segment = MagicMock()
        Segment.start = 0.0
        Segment.end = 1.0
        Segment.text = "Hello world"
        
        mock_model.transcribe.return_value = ([Segment], None)
        
        thread = TranscriberThread("test.wav")
        
        # Mock signals
        thread.finished = MagicMock()
        thread.progress = MagicMock()
        thread.status_update = MagicMock()
        thread.error = MagicMock()
        
        thread.run()
        
        # Verify finished signal called with a dict containing the text
        args, _ = thread.finished.emit.call_args
        result = args[0]
        self.assertIsInstance(result, dict)
        self.assertEqual(result['text'], "Hello world")

    @patch('src.worker.torch.cuda.is_available')
    @patch('src.worker.torch.cuda.get_device_properties')
    def test_get_optimal_device_with_cuda(self, mock_props, mock_cuda):
        from src.worker import get_optimal_device
        
        # Mock GPU with 6GB VRAM
        mock_cuda.return_value = True
        mock_props.return_value.total_memory = 6 * (1024**3)  # 6GB
        
        # Test with small model - should use int8 for safety on 6GB GPU
        device, compute_type = get_optimal_device(force_cpu=False, model_size="base")
        self.assertEqual(device, "cuda")
        self.assertEqual(compute_type, "int8")
        
        # Test with large model on 6GB GPU - should use int8
        device, compute_type = get_optimal_device(force_cpu=False, model_size="large-v3")
        self.assertEqual(device, "cuda")
        self.assertEqual(compute_type, "int8")
        
        # Test with force_cpu=True
        device, compute_type = get_optimal_device(force_cpu=True, model_size="base")
        self.assertEqual(device, "cpu")
        self.assertEqual(compute_type, "int8")
    
    @patch('src.worker.torch.cuda.is_available')
    def test_get_optimal_device_without_cuda(self, mock_cuda):
        from src.worker import get_optimal_device
        
        mock_cuda.return_value = False
        device, compute_type = get_optimal_device(force_cpu=False, model_size="base")
        self.assertEqual(device, "cpu")
        self.assertEqual(compute_type, "int8")

    @patch('src.worker.torch.cuda.is_available')
    @patch('src.worker.torch.cuda.get_device_properties')
    def test_get_optimal_device_with_large_gpu_prefers_float16(self, mock_props, mock_cuda):
        from src.worker import get_optimal_device

        mock_cuda.return_value = True
        mock_props.return_value.total_memory = 12 * (1024**3)
        device, compute_type = get_optimal_device(force_cpu=False, model_size="base")
        self.assertEqual(device, "cuda")
        self.assertEqual(compute_type, "float16")

    @patch('src.worker.torch.cuda.is_available')
    @patch('src.worker.torch.cuda.get_device_properties', side_effect=RuntimeError("gpu err"))
    def test_get_optimal_device_cuda_properties_error_defaults_int8(self, _mock_props, mock_cuda):
        from src.worker import get_optimal_device

        mock_cuda.return_value = True
        device, compute_type = get_optimal_device(force_cpu=False, model_size="base")
        self.assertEqual(device, "cuda")
        self.assertEqual(compute_type, "int8")

    @patch('src.worker.platform.system', return_value="Windows")
    @patch('src.worker.torch.cuda.is_available', return_value=True)
    def test_get_optimal_device_windows_cuda_prefers_float16(self, _mock_cuda, _mock_system):
        from src.worker import get_optimal_device

        device, compute_type = get_optimal_device(force_cpu=False, model_size="large-v3")
        self.assertEqual(device, "cuda")
        self.assertEqual(compute_type, "float16")

    @patch('src.worker.platform.system', return_value="Windows")
    @patch('src.worker.torch.cuda.is_available', return_value=False)
    def test_get_optimal_device_windows_cpu_prefers_float32(self, _mock_cuda, _mock_system):
        from src.worker import get_optimal_device

        device, compute_type = get_optimal_device(force_cpu=False, model_size="base")
        self.assertEqual(device, "cpu")
        self.assertEqual(compute_type, "float32")

    @patch('src.worker.platform.system', return_value="Windows")
    def test_windows_remaps_int8_compute_type_in_thread_init(self, _mock_system):
        # On Windows, we remap int8 to float16 on CUDA for stability.
        thread_cuda = TranscriberThread("test.wav", device="cuda", compute_type="int8")
        self.assertEqual(thread_cuda.compute_type, "float16")

        # On Windows CPU, we now prefer int8_float32 over pure float32/int8 to avoid native crashes.
        thread_cpu = TranscriberThread("test.wav", device="cpu", compute_type="int8")
        self.assertEqual(thread_cpu.compute_type, "int8_float32")

        thread_cpu_explicit = TranscriberThread("test.wav", device="cpu", compute_type="float32")
        self.assertEqual(thread_cpu_explicit.compute_type, "int8_float32")


class TestSearchAndChatThreads(unittest.TestCase):
    def test_search_thread_success(self):
        rag = MagicMock()
        rag.search.return_value = [{"id": 1}]
        thread = SearchThread(rag, "hello")
        thread.finished = MagicMock()
        thread.error = MagicMock()

        thread.run()

        thread.finished.emit.assert_called_once_with([{"id": 1}])
        thread.error.emit.assert_not_called()

    def test_search_thread_error(self):
        rag = MagicMock()
        rag.search.side_effect = Exception("boom")
        thread = SearchThread(rag, "hello")
        thread.finished = MagicMock()
        thread.error = MagicMock()

        thread.run()

        thread.error.emit.assert_called_once_with("boom")
        thread.finished.emit.assert_not_called()

    def test_chat_thread_success(self):
        provider = MagicMock()
        provider.chat.return_value = "ok-response"

        with patch("src.ai_provider.get_ai_provider", return_value=provider), \
             patch("PyQt6.QtCore.QSettings"):
            thread = ChatThread("k", "q", "ctx", history=[{"role": "user", "content": "hi"}], model_name="x")
            thread.finished = MagicMock()
            thread.error = MagicMock()
            thread.run()

        thread.finished.emit.assert_called_once_with("ok-response")
        thread.error.emit.assert_not_called()

    def test_chat_thread_error(self):
        with patch("src.ai_provider.get_ai_provider", side_effect=Exception("provider fail")), \
             patch("PyQt6.QtCore.QSettings"):
            thread = ChatThread("k", "q", "ctx")
            thread.finished = MagicMock()
            thread.error = MagicMock()
            thread.run()

        thread.error.emit.assert_called_once_with("provider fail")
        thread.finished.emit.assert_not_called()

if __name__ == '__main__':
    unittest.main()
