from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from psalter.domain.psalm import PsalmVerse


@dataclass(frozen=True, slots=True)
class PassageDefinition:
    start_verse: int
    end_verse: int
    canonical_text: str
    sequence_number: int


class PsalmSegmentationPolicy(Protocol):
    @property
    def version(self) -> str: ...

    def segment(self, verses: tuple[PsalmVerse, ...]) -> tuple[PassageDefinition, ...]: ...


@dataclass(frozen=True, slots=True)
class WordCountSegmentationPolicy:
    target_words_per_passage: int = 45
    maximum_words_per_passage: int = 70
    minimum_words_per_passage: int = 20
    version: str = "word-target-v1"

    def segment(self, verses: tuple[PsalmVerse, ...]) -> tuple[PassageDefinition, ...]:
        if not verses:
            return ()

        groups: list[list[PsalmVerse]] = []
        current: list[PsalmVerse] = []
        current_words = 0
        for verse in verses:
            verse_words = _word_count(verse.canonical_text)
            proposed_words = current_words + verse_words
            if (
                current
                and current_words >= self.minimum_words_per_passage
                and (
                    current_words >= self.target_words_per_passage
                    or proposed_words > self.maximum_words_per_passage
                )
            ):
                groups.append(current)
                current = [verse]
                current_words = verse_words
                continue
            current.append(verse)
            current_words = proposed_words

        if current:
            groups.append(current)

        if len(groups) > 1 and _group_word_count(groups[-1]) < self.minimum_words_per_passage:
            trailing = groups[-1]
            combined = _group_word_count(groups[-2]) + _group_word_count(trailing)
            if combined <= self.maximum_words_per_passage:
                groups[-2].extend(trailing)
                groups.pop()

        return tuple(
            PassageDefinition(
                start_verse=group[0].verse_number,
                end_verse=group[-1].verse_number,
                canonical_text="\n".join(verse.canonical_text for verse in group).strip(),
                sequence_number=index,
            )
            for index, group in enumerate(groups, start=1)
        )


def _word_count(text: str) -> int:
    return len(text.split())


def _group_word_count(group: list[PsalmVerse]) -> int:
    return sum(_word_count(verse.canonical_text) for verse in group)
