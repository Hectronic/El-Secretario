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

"""User-facing messages for transcription failures.

The original exception must remain in the application log, but it is rarely
actionable for someone using the desktop UI.
"""


def transcription_error_message(error) -> str:
    """Return a concise, actionable message without backend exception details."""
    detail = str(error or "").lower()

    if any(
        marker in detail
        for marker in (
            "connection broken",
            "broken pipe",
            "connection reset",
            "connection aborted",
            "connection timed out",
            "read timed out",
            "temporary failure in name resolution",
            "network is unreachable",
        )
    ):
        return (
            "No se pudo descargar o cargar el modelo de transcripción porque se interrumpió "
            "la conexión. Comprueba tu conexión a Internet y vuelve a intentarlo. "
            "La grabación se ha guardado."
        )

    if "no space left on device" in detail or "disk full" in detail:
        return (
            "No hay espacio suficiente en disco para preparar el modelo de transcripción. "
            "Libera espacio y vuelve a intentarlo. La grabación se ha guardado."
        )

    if "ffmpeg" in detail and ("not found" in detail or "not installed" in detail):
        return (
            "No se pudo abrir el archivo de audio porque falta FFmpeg. "
            "Instálalo y vuelve a intentarlo."
        )

    if "cancelled" in detail or "canceled" in detail:
        return "La transcripción se ha cancelado."

    return (
        "No se pudo completar la transcripción. Vuelve a intentarlo. "
        "Si el problema continúa, consulta el registro de la aplicación."
    )
