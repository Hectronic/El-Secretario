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

import pytest

from src.worker_components.error_messages import transcription_error_message


@pytest.mark.parametrize(
    "error",
    [
        '("Connection broken: BrokenPipeError(32, \'Broken pipe\')", BrokenPipeError(32, \'Broken pipe\'))',
        "Connection reset by peer",
        "Read timed out",
    ],
)
def test_network_download_errors_are_explained_without_backend_details(error):
    message = transcription_error_message(error)

    assert "conexión" in message
    assert "vuelve a intentarlo" in message
    assert "BrokenPipeError" not in message


def test_unknown_errors_are_not_exposed_verbatim():
    message = transcription_error_message("native backend failure 0xdeadbeef")

    assert message == (
        "No se pudo completar la transcripción. Vuelve a intentarlo. "
        "Si el problema continúa, consulta el registro de la aplicación."
    )
