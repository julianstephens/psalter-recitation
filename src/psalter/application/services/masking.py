from __future__ import annotations

import hashlib
import re

_WORD_PATTERN = re.compile(r"\w+", re.UNICODE)
_LEVEL_MASK_RATIOS: dict[int, float] = {0: 0.0, 1: 0.25, 2: 0.5, 3: 0.75, 4: 1.0}


def mask_text(canonical_text: str, passage_id: str, level: int) -> str:
    ratio = _LEVEL_MASK_RATIOS.get(level, 1.0)
    global_word_index = 0
    masked_lines: list[str] = []

    for line in canonical_text.splitlines():
        parts = re.split(r"(\w+)", line)
        word_positions: list[int] = []
        for index, part in enumerate(parts):
            if _WORD_PATTERN.fullmatch(part) is not None:
                word_positions.append(index)

        visible_in_line = 0
        for position in word_positions:
            token = parts[position]
            should_mask = _should_mask(
                passage_id=passage_id, token_index=global_word_index, ratio=ratio
            )
            if level == 0:
                should_mask = False
            if not should_mask:
                visible_in_line += 1
            parts[position] = _mask_token(token, level) if should_mask else token
            global_word_index += 1

        if level in (1, 2, 3) and word_positions and visible_in_line == 0:
            keep_index = _select_visible_word(
                passage_id=passage_id,
                line_word_count=len(word_positions),
                global_word_end=global_word_index,
            )
            restore_position = word_positions[keep_index]
            original = re.split(r"(\w+)", line)[restore_position]
            parts[restore_position] = original

        masked_lines.append("".join(parts))

    return "\n".join(masked_lines)


def _should_mask(passage_id: str, token_index: int, ratio: float) -> bool:
    if ratio <= 0.0:
        return False
    seed = f"{passage_id}:{token_index}".encode()
    value = int.from_bytes(hashlib.sha256(seed).digest()[:8], byteorder="big")
    return (value / ((1 << 64) - 1)) < ratio


def _mask_token(token: str, level: int) -> str:
    if level >= 4:
        return token[0] + "_" * (max(len(token), 2) - 1)
    return "_" * max(len(token), 2)


def _select_visible_word(passage_id: str, line_word_count: int, global_word_end: int) -> int:
    # Restores one deterministic visible token on intermediate levels per nonblank line.
    best = 0
    best_score = -1
    for local_index in range(line_word_count):
        global_index = global_word_end - line_word_count + local_index
        seed = f"{passage_id}:visible:{global_index}".encode()
        score = int.from_bytes(hashlib.sha256(seed).digest()[:8], byteorder="big")
        if score > best_score:
            best_score = score
            best = local_index
    return best
