from __future__ import annotations

from typing import BinaryIO, Protocol

from psalter.application.dto import PreparedAudioUpload


class UploadedAudioPreparer(Protocol):
    def prepare(
        self,
        *,
        passage_id: str,
        source: BinaryIO,
        content_type: str,
    ) -> PreparedAudioUpload: ...
